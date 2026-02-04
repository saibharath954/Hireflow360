# backend/app/api/candidates.py
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_
import uuid
from datetime import datetime, timedelta
import json

from app.core.database import get_db
from app.core.dependencies import get_current_recruiter_user, get_current_admin_user
from app.schemas.schemas import (
    Candidate, CandidateCreate, CandidateUpdate, CandidateFilters,
    PaginatedResponse, ApiResponse, CandidateFieldKey,
    ConversationState, ExportOptions
)
from app.models.models import (
    User, Candidate as CandidateModel, CandidateSkill,
    ParsedField, Resume, Message, Organization, Job, JobType
)
from app.services.candidate_service import CandidateService
from app.services.resume_service import ResumeService
from app.services.messaging_service import MessagingService
from app.services.export_service import ExportService
from app.workers.background import process_bulk_update

router = APIRouter()

@router.get("", response_model=ApiResponse)
async def get_candidates(
    filters: CandidateFilters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("updated_at", regex="^(created_at|updated_at|name|years_experience|overall_confidence)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Get candidates with advanced filtering, sorting, and pagination
    """
    try:
        result = CandidateService.get_candidates_with_filters(
            db=db,
            organization_id=current_user.organization_id,
            filters=filters,
            page=page,
            page_size=page_size,
            owner_id=current_user.id if current_user.role == "RECRUITER" else None,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return ApiResponse(
            success=True,
            data=result,
            message=f"Found {result.total} candidates"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=ApiResponse)
async def search_candidates(
    query: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Advanced search across candidates
    """
    try:
        candidates = CandidateService.search_candidates_advanced(
            db=db,
            organization_id=current_user.organization_id,
            query=query,
            limit=limit
        )
        
        # Format response
        items = [CandidateService._format_candidate_response(c) for c in candidates]
        
        return ApiResponse(
            success=True,
            data=items,
            message=f"Found {len(items)} candidates matching '{query}'"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-upload", response_model=ApiResponse)
async def bulk_upload_resumes(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user),
    background_tasks: BackgroundTasks = None
):
    """
    Upload multiple resumes at once
    """
    try:
        results = []
        errors = []
        
        for file in files:
            try:
                # Read file content
                content = await file.read()
                
                # Validate file
                is_valid, error = ResumeService.validate_resume_file(content, file.filename)
                if not is_valid:
                    errors.append({
                        "file": file.filename,
                        "error": error
                    })
                    continue
                
                # Process upload
                result, error = ResumeService.process_resume_upload(
                    file_content=content,
                    organization_id=current_user.organization_id,
                    user_id=current_user.id,
                    db=db
                )
                
                if result:
                    results.append(result)
                else:
                    errors.append({
                        "file": file.filename,
                        "error": error
                    })
                    
            except Exception as e:
                errors.append({
                    "file": file.filename,
                    "error": str(e)
                })
        
        return ApiResponse(
            success=True,
            data={
                "processed": len(results),
                "failed": len(errors),
                "results": results,
                "errors": errors
            },
            message=f"Processed {len(results)} files, {len(errors)} failed"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{candidate_id}", response_model=ApiResponse)
async def get_candidate_detail(
    candidate_id: str,
    include_timeline: bool = Query(False),
    include_analytics: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Get candidate by ID with optional timeline and analytics
    """
    try:
        candidate = CandidateService.get_candidate_by_id(
            db=db,
            candidate_id=uuid.UUID(candidate_id),
            organization_id=current_user.organization_id
        )
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Format basic response
        response_data = CandidateService._format_candidate_response(candidate)
        
        # Add timeline if requested
        if include_timeline:
            timeline = CandidateService.export_candidate_timeline(
                db=db,
                candidate_id=uuid.UUID(candidate_id),
                organization_id=current_user.organization_id
            )
            response_data["timeline"] = timeline
        
        # Add conversation analytics if requested
        if include_analytics:
            analytics = MessagingService.get_conversation_analytics(
                db=db,
                candidate_id=uuid.UUID(candidate_id),
                organization_id=current_user.organization_id
            )
            response_data["conversation_analytics"] = analytics
        
        return ApiResponse(
            success=True,
            data=response_data,
            message="Candidate retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{candidate_id}", response_model=ApiResponse)
async def update_candidate(
    candidate_id: str,
    updates: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Update candidate information
    """
    try:
        candidate = CandidateService.update_candidate(
            db=db,
            candidate_id=uuid.UUID(candidate_id),
            organization_id=current_user.organization_id,
            update_data=updates
        )
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        return ApiResponse(
            success=True,
            data=CandidateService._format_candidate_response(candidate),
            message="Candidate updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{candidate_id}", response_model=ApiResponse)
async def delete_candidate(
    candidate_id: str,
    permanent: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Delete candidate (soft delete by default)
    """
    try:
        if permanent and current_user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Only admins can perform permanent deletion")
        
        if permanent:
            # Permanent deletion
            candidate = db.query(CandidateModel).filter(
                CandidateModel.id == candidate_id,
                CandidateModel.organization_id == current_user.organization_id
            ).first()
            
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            
            # Delete related records
            db.query(CandidateSkill).filter(
                CandidateSkill.candidate_id == candidate_id
            ).delete()
            
            db.query(ParsedField).filter(
                ParsedField.candidate_id == candidate_id
            ).delete()
            
            # Delete candidate
            db.delete(candidate)
            db.commit()
            
            message = "Candidate permanently deleted"
        else:
            # Soft delete
            success = CandidateService.delete_candidate(
                db=db,
                candidate_id=uuid.UUID(candidate_id),
                organization_id=current_user.organization_id
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="Candidate not found")
            
            message = "Candidate soft deleted"
        
        return ApiResponse(
            success=True,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{candidate_id}/conversation/state", response_model=ApiResponse)
async def update_conversation_state(
    candidate_id: str,
    field_key: str,
    field_state: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Update conversation state for a candidate field
    """
    try:
        candidate = CandidateService.update_conversation_state(
            db=db,
            candidate_id=uuid.UUID(candidate_id),
            organization_id=current_user.organization_id,
            field_key=field_key,
            field_state=field_state
        )
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        return ApiResponse(
            success=True,
            data=CandidateService._format_candidate_response(candidate),
            message="Conversation state updated"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{candidate_id}/conversation/pending", response_model=ApiResponse)
async def get_pending_fields(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Get pending fields for a candidate
    """
    try:
        pending_fields = CandidateService.get_pending_fields(
            db=db,
            candidate_id=uuid.UUID(candidate_id),
            organization_id=current_user.organization_id
        )
        
        return ApiResponse(
            success=True,
            data={"pending_fields": pending_fields},
            message=f"Found {len(pending_fields)} pending fields"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{candidate_id}/schedule-followup", response_model=ApiResponse)
async def schedule_follow_up(
    candidate_id: str,
    delay_hours: int = Query(24, ge=1, le=168),
    follow_up_type: str = Query("reminder", regex="^(reminder|checkin|nudge)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Schedule a follow-up message for a candidate
    """
    try:
        job, error = MessagingService.schedule_follow_up(
            db=db,
            candidate_id=uuid.UUID(candidate_id),
            organization_id=current_user.organization_id,
            delay_hours=delay_hours,
            follow_up_type=follow_up_type
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return ApiResponse(
            success=True,
            data={"job_id": str(job.id), "scheduled_for": job.scheduled_for.isoformat()},
            message=f"Follow-up scheduled for {delay_hours} hours from now"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-update", response_model=ApiResponse)
async def bulk_update_candidates(
    updates: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Bulk update multiple candidates (admin only)
    """
    try:
        # Validate updates
        valid_updates = []
        for update in updates:
            if 'candidate_id' in update and 'updates' in update:
                try:
                    uuid.UUID(update['candidate_id'])
                    valid_updates.append(update)
                except:
                    continue
        
        if not valid_updates:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        # Process in background
        background_tasks.add_task(
            process_bulk_update,
            valid_updates,
            current_user.organization_id
        )
        
        return ApiResponse(
            success=True,
            message=f"Bulk update queued for {len(valid_updates)} candidates"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deduplicate", response_model=ApiResponse)
async def deduplicate_candidates(
    threshold: float = Query(0.85, ge=0.5, le=1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Find and merge duplicate candidates (admin only)
    """
    try:
        result = CandidateService.deduplicate_candidates(
            db=db,
            organization_id=current_user.organization_id,
            threshold=threshold
        )
        
        return ApiResponse(
            success=result["success"],
            data=result,
            message=f"Found {result.get('duplicate_groups', 0)} duplicate groups"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/overview", response_model=ApiResponse)
async def get_candidates_analytics(
    time_range_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Get comprehensive candidates analytics
    """
    try:
        analytics = CandidateService.get_candidate_analytics(
            db=db,
            organization_id=current_user.organization_id,
            time_range_days=time_range_days
        )
        
        return ApiResponse(
            success=True,
            data=analytics,
            message=f"Analytics for last {time_range_days} days"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export", response_model=ApiResponse)
async def export_candidates(
    options: ExportOptions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Export candidates in various formats
    """
    try:
        if options.format == "excel":
            file_content = ExportService.export_candidates_to_excel(
                db=db,
                organization_id=current_user.organization_id,
                options=options
            )
            
            filename = ExportService.generate_export_filename("xlsx")
            
            return ApiResponse(
                success=True,
                data={
                    "filename": filename,
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "file_size": len(file_content.getvalue())
                },
                message="Excel export generated"
            )
            
        elif options.format == "csv":
            file_content = ExportService.export_candidates_to_csv(
                db=db,
                organization_id=current_user.organization_id,
                options=options
            )
            
            filename = ExportService.generate_export_filename("csv")
            
            return ApiResponse(
                success=True,
                data={
                    "filename": filename,
                    "content_type": "text/csv",
                    "file_size": len(file_content.getvalue())
                },
                message="CSV export generated"
            )
            
        elif options.format == "json":
            data = ExportService.export_candidates_to_json(
                db=db,
                organization_id=current_user.organization_id,
                options=options
            )
            
            return ApiResponse(
                success=True,
                data=data,
                message="JSON export generated"
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {options.format}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommendations", response_model=ApiResponse)
async def get_candidate_recommendations(
    job_description: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Get candidate recommendations based on job description
    """
    try:
        recommendations = CandidateService.get_candidate_recommendations(
            db=db,
            organization_id=current_user.organization_id,
            job_description=job_description,
            limit=limit
        )
        
        # Format response
        formatted_recommendations = []
        for rec in recommendations:
            candidate_data = CandidateService._format_candidate_response(rec["candidate"])
            candidate_data.update({
                "match_score": rec["match_score"],
                "matching_skills": rec["matching_skills"],
                "missing_skills": rec["missing_skills"]
            })
            formatted_recommendations.append(candidate_data)
        
        return ApiResponse(
            success=True,
            data=formatted_recommendations,
            message=f"Found {len(formatted_recommendations)} matching candidates"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{candidate_id}/validate", response_model=ApiResponse)
async def validate_candidate_data(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Validate candidate data completeness and quality
    """
    try:
        candidate = CandidateService.get_candidate_by_id(
            db=db,
            candidate_id=uuid.UUID(candidate_id),
            organization_id=current_user.organization_id
        )
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        validation = CandidateService.validate_candidate_data(candidate)
        
        return ApiResponse(
            success=True,
            data=validation,
            message=f"Validation score: {validation['score']:.1f}/100"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))