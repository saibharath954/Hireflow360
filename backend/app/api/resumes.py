# backend/app/api/resumes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_recruiter_user
from app.schemas.schemas import ApiResponse
from app.models.models import User, Candidate, Resume, Job, JobType, JobStatus
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
    """Upload resume via file or URL"""
    if not file and not url:
        return ApiResponse(
            success=False,
            error="Either file or URL must be provided"
        )
    
    # Generate IDs
    resume_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    # Create resume record
    if file:
        # Save file locally
        file_ext = os.path.splitext(file.filename)[1]
        file_path = f"{settings.UPLOAD_DIR}/{resume_id}{file_ext}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        file_name = file.filename
        file_url = f"/uploads/{resume_id}{file_ext}"
        file_type = "pdf" if file_ext.lower() == ".pdf" else "docx"
    else:
        # URL upload
        file_name = url.split("/")[-1]
        file_url = url
        file_type = "pdf" if url.lower().endswith(".pdf") else "docx"
    
    resume = Resume(
        id=resume_id,
        candidate_id=candidate_id,
        file_name=file_name,
        file_url=file_url,
        file_type=file_type,
        uploaded_at=datetime.utcnow()
    )
    
    # Create candidate placeholder
    candidate = Candidate(
        id=candidate_id,
        organization_id=current_user.organization_id,
        owner_id=current_user.id,
        name=file_name.replace("_", " ").replace("-", " ").replace(".pdf", "").replace(".docx", ""),
        email=f"candidate_{datetime.utcnow().timestamp()}@example.com",
        status="new",
        overall_confidence=0,
        created_at=datetime.utcnow()
    )
    
    # Create parsing job
    job = Job(
        id=job_id,
        type=JobType.PARSE_RESUME,
        status=JobStatus.QUEUED,
        candidate_id=candidate_id,
        resume_id=resume_id,
        job_metadata={
            "file_name": file_name,
            "file_type": file_type,
            "uploaded_by": current_user.email
        },
        created_at=datetime.utcnow()
    )
    
    # Save to database
    db.add(candidate)
    db.add(resume)
    db.add(job)
    db.commit()
    
    # Trigger background processing (async)
    process_resume_upload.delay(
        resume_id=resume_id,
        candidate_id=candidate_id,
        job_id=job_id
    )
    
    return ApiResponse(
        success=True,
        data={
            "resumeId": resume_id,
            "candidateId": candidate_id,
            "jobId": job_id
        }
    )

@router.post("/{resume_id}/reprocess", response_model=ApiResponse)
async def reprocess_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Reprocess a resume"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.candidate.has(organization_id=current_user.organization_id)
    ).first()
    
    if not resume:
        return ApiResponse(success=False, error="Resume not found")
    
    # Create new job
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type=JobType.REPROCESS_RESUME,
        status=JobStatus.QUEUED,
        candidate_id=resume.candidate_id,
        resume_id=resume_id,
        created_at=datetime.utcnow()
    )
    
    db.add(job)
    db.commit()
    
    # Trigger reprocessing
    process_resume_upload.delay(
        resume_id=resume_id,
        candidate_id=str(resume.candidate_id),
        job_id=job_id,
        reprocess=True
    )
    
    return ApiResponse(
        success=True,
        data={"jobId": job_id}
    )