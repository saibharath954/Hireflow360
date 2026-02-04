# backend/app/api/resumes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_recruiter_user
from app.schemas.schemas import ApiResponse
from app.models.models import User, Candidate, Resume, Job, JobType, JobStatus, CandidateStatus
from app.workers.background import process_resume_upload
from app.core.config import settings

router = APIRouter()

@router.post("/upload", response_model=ApiResponse)
async def upload_resume(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """
    Upload resume via file or URL.
    Creates Candidate -> Resume -> Job in a strict transactional order
    to prevent Foreign Key race conditions.
    """
    if not file and not url:
        return ApiResponse(
            success=False,
            error="Either file or URL must be provided"
        )
    
    # 1. Generate UUID objects (not strings) for the DB
    # We generate them here so we can use them for file naming / referencing
    generated_candidate_id = uuid.uuid4()
    generated_resume_id = uuid.uuid4()
    generated_job_id = uuid.uuid4()
    
    # 2. Handle File IO (Save locally first)
    try:
        if file:
            file_ext = os.path.splitext(file.filename)[1]
            if not file_ext:
                file_ext = ".pdf" # Default to pdf if no extension
                
            # Use the UUID for the filename to prevent collisions
            file_path = f"{settings.UPLOAD_DIR}/{generated_resume_id}{file_ext}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            file_name = file.filename
            file_url = f"/uploads/{generated_resume_id}{file_ext}"
            file_type = "pdf" if file_ext.lower() == ".pdf" else "docx"
        else:
            # URL upload
            file_name = url.split("/")[-1] or "resume_download.pdf"
            file_url = url
            file_type = "pdf" if url.lower().endswith(".pdf") else "docx"

    except Exception as e:
        return ApiResponse(success=False, error=f"Failed to save file: {str(e)}")

    try:
        # 3. Create Candidate (First!)
        # We use a placeholder email that ensures uniqueness until parsing extracts the real one
        candidate = Candidate(
            id=generated_candidate_id,
            organization_id=current_user.organization_id,
            owner_id=current_user.id,
            name=file_name.replace("_", " ").replace("-", " ").replace(".pdf", "").replace(".docx", ""),
            email=f"candidate_{generated_candidate_id}@placeholder.com", # Unique placeholder
            status=CandidateStatus.NEW,
            overall_confidence=0.0,
            # Timestamps handled by model defaults, or explicit:
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(candidate)
        db.flush() # 🚨 FLUSH 1: Candidate now exists in DB for Foreign Key checks

        # 4. Create Resume (Second!)
        resume = Resume(
            id=generated_resume_id,
            candidate_id=candidate.id, # Link to the flushed Candidate
            file_name=file_name,
            file_url=file_url,
            file_type=file_type,
            uploaded_at=datetime.now(timezone.utc)
        )
        db.add(resume)
        db.flush() # 🚨 FLUSH 2: Resume now exists in DB for Job checks

        # 5. Create Job (Third!)
        job = Job(
            id=generated_job_id,
            organization_id=current_user.organization_id, # Link to Organization
            type=JobType.PARSE_RESUME,
            status=JobStatus.QUEUED,
            candidate_id=candidate.id,
            resume_id=resume.id, # Link to the flushed Resume
            job_metadata={
                "file_name": file_name,
                "file_type": file_type,
                "uploaded_by": current_user.email
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(job)
        
        # 6. Commit everything
        db.commit()

        # 7. Trigger Background Worker
        process_resume_upload.delay(
            resume_id=str(resume.id),
            candidate_id=str(candidate.id),
            job_id=str(job.id)
        )
        
        return ApiResponse(
            success=True,
            data={
                "resumeId": str(resume.id),
                "candidateId": str(candidate.id),
                "jobId": str(job.id)
            }
        )

    except Exception as e:
        db.rollback()
        # Clean up file if DB insert failed
        if file and 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        print(f"Error uploading resume: {str(e)}")
        return ApiResponse(success=False, error=f"Database error: {str(e)}")

@router.post("/{resume_id}/reprocess", response_model=ApiResponse)
async def reprocess_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Reprocess a resume"""
    try:
        # Validate UUID format
        resume_uuid = uuid.UUID(resume_id)
    except ValueError:
        return ApiResponse(success=False, error="Invalid Resume ID format")

    resume = db.query(Resume).join(Candidate).filter(
        Resume.id == resume_uuid,
        Candidate.organization_id == current_user.organization_id
    ).first()
    
    if not resume:
        return ApiResponse(success=False, error="Resume not found")
    
    # Create new job
    generated_job_id = uuid.uuid4()
    
    job = Job(
        id=generated_job_id,
        organization_id=current_user.organization_id,
        type=JobType.REPROCESS_RESUME,
        status=JobStatus.QUEUED,
        candidate_id=resume.candidate_id,
        resume_id=resume.id,
        job_metadata={
            "reason": "manual_reprocess",
            "triggered_by": current_user.email
        },
        created_at=datetime.now(timezone.utc)
    )
    
    try:
        db.add(job)
        db.commit()
        
        # Trigger reprocessing
        process_resume_upload.delay(
            resume_id=str(resume.id),
            candidate_id=str(resume.candidate_id),
            job_id=str(job.id),
            reprocess=True
        )
        
        return ApiResponse(
            success=True,
            data={"jobId": str(job.id)}
        )
    except Exception as e:
        db.rollback()
        return ApiResponse(success=False, error=f"Failed to queue reprocessing: {str(e)}")