# backend/app/api/dashboard.py
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.dependencies import get_current_recruiter_user
from app.schemas.schemas import ApiResponse, DashboardStats, ActivityItem
from app.models.models import User, Candidate, Resume, Message, Job, JobStatus

router = APIRouter()

@router.get("/stats", response_model=ApiResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Get dashboard statistics"""
    # Total candidates
    total_candidates = db.query(Candidate).filter(
        Candidate.organization_id == current_user.organization_id
    ).count()
    
    # Resumes processed
    resumes_processed = db.query(Resume).filter(
        Resume.candidate.has(organization_id=current_user.organization_id)
    ).count()
    
    # Messages sent
    messages_sent = db.query(Message).filter(
        Message.candidate.has(organization_id=current_user.organization_id),
        Message.direction == "outgoing"
    ).count()
    
    # Replies received
    replies_received = db.query(Message).filter(
        Message.candidate.has(organization_id=current_user.organization_id),
        Message.direction == "incoming"
    ).count()
    
    # Pending jobs
    pending_jobs = db.query(Job).filter(
        Job.candidate.has(organization_id=current_user.organization_id),
        Job.status.in_(["queued", "processing"])
    ).count()
    
    # Interested candidates
    interested_candidates = db.query(Candidate).filter(
        Candidate.organization_id == current_user.organization_id,
        Candidate.status == "interested"
    ).count()
    
    stats = DashboardStats(
        total_candidates=total_candidates,
        resumes_processed=resumes_processed,
        messages_sent=messages_sent,
        replies_received=replies_received,
        pending_jobs=pending_jobs,
        interested_candidates=interested_candidates
    )
    
    return ApiResponse(success=True, data=stats)

@router.get("/activity", response_model=ApiResponse)
async def get_recent_activity(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Get recent activity"""
    activities = []
    
    # Get recent candidates
    recent_candidates = db.query(Candidate).filter(
        Candidate.organization_id == current_user.organization_id
    ).order_by(Candidate.created_at.desc()).limit(limit).all()
    
    for candidate in recent_candidates:
        activities.append({
            "id": f"act_{candidate.id}_created",
            "type": "resume_uploaded",
            "description": f"Resume uploaded for {candidate.name}",
            "timestamp": candidate.created_at.isoformat(),
            "candidateId": str(candidate.id),
            "candidateName": candidate.name
        })
    
    # Get recent messages
    recent_messages = db.query(Message).filter(
        Message.candidate.has(organization_id=current_user.organization_id)
    ).order_by(Message.timestamp.desc()).limit(limit).all()
    
    for message in recent_messages:
        candidate = message.candidate
        activities.append({
            "id": f"act_{message.id}",
            "type": "message_sent" if message.direction == "outgoing" else "reply_received",
            "description": f"{'Message sent to' if message.direction == 'outgoing' else 'Reply received from'} {candidate.name}",
            "timestamp": message.timestamp.isoformat(),
            "candidateId": str(candidate.id),
            "candidateName": candidate.name
        })
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    activities = activities[:limit]
    
    return ApiResponse(success=True, data=activities)