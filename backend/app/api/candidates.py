# backend/app/api/candidates.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
import uuid
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.dependencies import get_current_recruiter_user
from app.schemas.schemas import (
    Candidate, CandidateCreate, CandidateUpdate, CandidateFilters,
    PaginatedResponse, ApiResponse
)
from app.models.models import (
    User, Candidate as CandidateModel, CandidateSkill,
    ParsedField, Resume, Message, Organization
)
from app.services.candidate_service import CandidateService

router = APIRouter()

@router.get("", response_model=ApiResponse)
async def get_candidates(
    filters: CandidateFilters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Get candidates with filtering and pagination"""
    query = db.query(CandidateModel).filter(
        CandidateModel.organization_id == current_user.organization_id
    )
    
    # Apply filters
    if filters.search:
        search = f"%{filters.search.lower()}%"
        query = query.filter(
            or_(
                CandidateModel.name.ilike(search),
                CandidateModel.email.ilike(search),
                CandidateModel.current_company.ilike(search),
                CandidateModel.location.ilike(search),
                CandidateModel.education.ilike(search),
                CandidateModel.id.in_(
                    db.query(CandidateSkill.candidate_id).filter(
                        CandidateSkill.skill.ilike(search)
                    )
                )
            )
        )
    
    if filters.status and len(filters.status) > 0:
        query = query.filter(CandidateModel.status.in_(filters.status))
    
    if filters.skills and len(filters.skills) > 0:
        for skill in filters.skills:
            query = query.filter(
                CandidateModel.id.in_(
                    db.query(CandidateSkill.candidate_id).filter(
                        CandidateSkill.skill.ilike(f"%{skill}%")
                    )
                )
            )
    
    if filters.min_experience is not None:
        query = query.filter(
            or_(
                CandidateModel.years_experience >= filters.min_experience,
                CandidateModel.years_experience == None
            )
        )
    
    if filters.max_experience is not None:
        query = query.filter(
            CandidateModel.years_experience <= filters.max_experience
        )
    
    if filters.location:
        query = query.filter(CandidateModel.location.ilike(f"%{filters.location}%"))
    
    if filters.date_range:
        query = query.filter(
            CandidateModel.created_at.between(
                filters.date_range["from"],
                filters.date_range["to"]
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    candidates = query.offset(offset).limit(page_size).all()
    
    # Convert to response format
    items = []
    for candidate in candidates:
        # Get skills
        skills = [skill.skill for skill in candidate.skills]
        
        # Get parsed fields
        parsed_fields = []
        for pf in candidate.parsed_fields:
            parsed_fields.append({
                "name": pf.name,
                "value": pf.value,
                "confidence": pf.confidence,
                "raw_extraction": pf.raw_extraction,
                "source": pf.source
            })
        
        # Get resumes
        resumes = []
        for resume in candidate.resumes:
            resumes.append({
                "id": str(resume.id),
                "candidateId": str(resume.candidate_id),
                "fileName": resume.file_name,
                "fileUrl": resume.file_url,
                "fileType": resume.file_type,
                "uploadedAt": resume.uploaded_at.isoformat(),
                "parsedAt": resume.parsed_at.isoformat() if resume.parsed_at else None,
                "parseJobId": resume.parse_job_id,
                "rawText": resume.raw_text
            })
        
        # Get messages
        messages = []
        for msg in candidate.messages:
            messages.append({
                "id": str(msg.id),
                "candidateId": str(msg.candidate_id),
                "direction": msg.direction,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "status": msg.status,
                "intent": msg.intent,
                "generatedBy": msg.generated_by,
                "classification": msg.classification,
                "suggestedReply": msg.suggested_reply,
                "extractedFields": msg.extracted_fields,
                "requiresHRReview": msg.requires_hr_review,
                "aiSuggestedReply": msg.ai_suggested_reply,
                "hrApproved": msg.hr_approved,
                "hrApprovedAt": msg.hr_approved_at.isoformat() if msg.hr_approved_at else None,
                "askedFields": msg.asked_fields
            })
        
        items.append({
            "id": str(candidate.id),
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "yearsExperience": candidate.years_experience,
            "skills": skills,
            "currentCompany": candidate.current_company,
            "education": candidate.education,
            "location": candidate.location,
            "portfolioUrl": candidate.portfolio_url,
            "noticePeriod": candidate.notice_period,
            "expectedSalary": candidate.expected_salary,
            "status": candidate.status,
            "parsedFields": parsed_fields,
            "resumes": resumes,
            "messages": messages,
            "lastMessageAt": candidate.last_message_at.isoformat() if candidate.last_message_at else None,
            "overallConfidence": candidate.overall_confidence,
            "conversationState": candidate.conversation_state,
            "createdAt": candidate.created_at.isoformat(),
            "updatedAt": candidate.updated_at.isoformat() if candidate.updated_at else None
        })
    
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=offset + len(items) < total
        )
    )

@router.get("/{candidate_id}", response_model=ApiResponse)
async def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Get candidate by ID"""
    candidate = db.query(CandidateModel).filter(
        CandidateModel.id == candidate_id,
        CandidateModel.organization_id == current_user.organization_id
    ).first()
    
    if not candidate:
        return ApiResponse(success=False, error="Candidate not found")
    
    # Get skills
    skills = [skill.skill for skill in candidate.skills]
    
    # Get parsed fields
    parsed_fields = []
    for pf in candidate.parsed_fields:
        parsed_fields.append({
            "name": pf.name,
            "value": pf.value,
            "confidence": pf.confidence,
            "raw_extraction": pf.raw_extraction,
            "source": pf.source
        })
    
    # Get resumes
    resumes = []
    for resume in candidate.resumes:
        resumes.append({
            "id": str(resume.id),
            "candidateId": str(resume.candidate_id),
            "fileName": resume.file_name,
            "fileUrl": resume.file_url,
            "fileType": resume.file_type,
            "uploadedAt": resume.uploaded_at.isoformat(),
            "parsedAt": resume.parsed_at.isoformat() if resume.parsed_at else None,
            "parseJobId": resume.parse_job_id,
            "rawText": resume.raw_text
        })
    
    # Get messages
    messages = []
    for msg in candidate.messages:
        messages.append({
            "id": str(msg.id),
            "candidateId": str(msg.candidate_id),
            "direction": msg.direction,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "status": msg.status,
            "intent": msg.intent,
            "generatedBy": msg.generated_by,
            "classification": msg.classification,
            "suggestedReply": msg.suggested_reply,
            "extractedFields": msg.extracted_fields,
            "requiresHRReview": msg.requires_hr_review,
            "aiSuggestedReply": msg.ai_suggested_reply,
            "hrApproved": msg.hr_approved,
            "hrApprovedAt": msg.hr_approved_at.isoformat() if msg.hr_approved_at else None,
            "askedFields": msg.asked_fields
        })
    
    data = {
        "id": str(candidate.id),
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "yearsExperience": candidate.years_experience,
        "skills": skills,
        "currentCompany": candidate.current_company,
        "education": candidate.education,
        "location": candidate.location,
        "portfolioUrl": candidate.portfolio_url,
        "noticePeriod": candidate.notice_period,
        "expectedSalary": candidate.expected_salary,
        "status": candidate.status,
        "parsedFields": parsed_fields,
        "resumes": resumes,
        "messages": messages,
        "lastMessageAt": candidate.last_message_at.isoformat() if candidate.last_message_at else None,
        "overallConfidence": candidate.overall_confidence,
        "conversationState": candidate.conversation_state,
        "createdAt": candidate.created_at.isoformat(),
        "updatedAt": candidate.updated_at.isoformat() if candidate.updated_at else None
    }
    
    return ApiResponse(success=True, data=data)

@router.put("/{candidate_id}", response_model=ApiResponse)
async def update_candidate(
    candidate_id: str,
    updates: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Update candidate"""
    candidate = db.query(CandidateModel).filter(
        CandidateModel.id == candidate_id,
        CandidateModel.organization_id == current_user.organization_id
    ).first()
    
    if not candidate:
        return ApiResponse(success=False, error="Candidate not found")
    
    # Update fields
    update_dict = updates.dict(exclude_unset=True)
    
    # Handle skills separately
    if "skills" in update_dict:
        skills = update_dict.pop("skills", [])
        # Delete existing skills
        db.query(CandidateSkill).filter(
            CandidateSkill.candidate_id == candidate.id
        ).delete()
        # Add new skills
        for skill in skills:
            candidate_skill = CandidateSkill(
                candidate_id=candidate.id,
                skill=skill,
                confidence=1.0
            )
            db.add(candidate_skill)
    
    for key, value in update_dict.items():
        setattr(candidate, key, value)
    
    candidate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(candidate)
    
    return ApiResponse(
        success=True,
        data=Candidate.from_orm(candidate),
        message="Candidate updated successfully"
    )