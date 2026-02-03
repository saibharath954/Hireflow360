# backend/app/api/jobs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin_user, get_current_recruiter_user
from app.schemas.schemas import ApiResponse, Job as JobSchema
from app.models.models import User, Job as JobModel
from typing import List

router = APIRouter()

@router.get("", response_model=ApiResponse)
async def get_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Get all jobs for organization"""
    # For admins, show all jobs in org
    # For recruiters, show only jobs for their candidates
    if current_user.role == "ADMIN":
        jobs = db.query(JobModel).filter(
            JobModel.candidate.has(organization_id=current_user.organization_id)
        ).order_by(JobModel.created_at.desc()).all()
    else:
        jobs = db.query(JobModel).filter(
            JobModel.candidate.has(
                organization_id=current_user.organization_id,
                owner_id=current_user.id
            )
        ).order_by(JobModel.created_at.desc()).all()
    
    job_list = []
    for job in jobs:
        job_list.append({
            "id": str(job.id),
            "type": job.type,
            "status": job.status,
            "progress": job.progress,
            "createdAt": job.created_at.isoformat(),
            "startedAt": job.started_at.isoformat() if job.started_at else None,
            "completedAt": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
            "metadata": job.job_metadata,
            "candidateId": str(job.candidate_id) if job.candidate_id else None,
            "resumeId": str(job.resume_id) if job.resume_id else None,
            "messageId": str(job.message_id) if job.message_id else None
        })
    
    return ApiResponse(success=True, data=job_list)

@router.get("/{job_id}", response_model=ApiResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Get job by ID"""
    job = db.query(JobModel).filter(
        JobModel.id == job_id,
        JobModel.candidate.has(organization_id=current_user.organization_id)
    ).first()
    
    if not job:
        return ApiResponse(success=False, error="Job not found")
    
    data = {
        "id": str(job.id),
        "type": job.type,
        "status": job.status,
        "progress": job.progress,
        "createdAt": job.created_at.isoformat(),
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error,
        "metadata": job.job_metadata,
        "candidateId": str(job.candidate_id) if job.candidate_id else None,
        "resumeId": str(job.resume_id) if job.resume_id else None,
        "messageId": str(job.message_id) if job.message_id else None
    }
    
    return ApiResponse(success=True, data=data)