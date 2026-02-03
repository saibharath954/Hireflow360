# backend/app/services/job_service.py
"""
Job Service
Handles all business logic related to background jobs.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_
from sqlalchemy.exc import SQLAlchemyError

from app.models.models import Job, JobType, JobStatus, Candidate, User
from app.schemas.schemas import Job as JobSchema
from app.core.logging import logger


class JobService:
    """Service for job-related operations"""
    
    @staticmethod
    def create_job(
        db: Session,
        job_type: JobType,
        status: JobStatus = JobStatus.QUEUED,
        candidate_id: Optional[uuid.UUID] = None,
        resume_id: Optional[uuid.UUID] = None,
        message_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Job:
        """
        Create a new background job.
        
        Args:
            db: Database session
            job_type: Type of job
            status: Initial status
            candidate_id: Optional candidate ID
            resume_id: Optional resume ID
            message_id: Optional message ID
            metadata: Optional job metadata
            
        Returns:
            Created job
        """
        try:
            job = Job(
                id=uuid.uuid4(),
                type=job_type,
                status=status,
                candidate_id=candidate_id,
                resume_id=resume_id,
                message_id=message_id,
                metadata=metadata or {},
                created_at=datetime.utcnow()
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            logger.info(f"Created job: {job.id} ({job_type})")
            return job
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to create job: {str(e)}")
            raise
    
    @staticmethod
    def get_job_by_id(
        db: Session,
        job_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Optional[Job]:
        """
        Get job by ID with security check.
        
        Args:
            db: Database session
            job_id: Job ID
            organization_id: Organization ID
            
        Returns:
            Job object or None
        """
        try:
            job = db.query(Job).options(
                joinedload(Job.candidate)
            ).filter(
                Job.id == job_id,
                Job.candidate.has(organization_id=organization_id)
            ).first()
            
            return job
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_jobs(
        db: Session,
        organization_id: uuid.UUID,
        job_type: Optional[JobType] = None,
        status: Optional[JobStatus] = None,
        candidate_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """
        Get jobs with filtering.
        
        Args:
            db: Database session
            organization_id: Organization ID
            job_type: Filter by job type
            status: Filter by status
            candidate_id: Filter by candidate ID
            user_id: Filter by user (candidate owner)
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of jobs
        """
        try:
            query = db.query(Job).options(
                joinedload(Job.candidate)
            ).filter(
                Job.candidate.has(organization_id=organization_id)
            )
            
            # Apply filters
            if job_type:
                query = query.filter(Job.type == job_type)
            
            if status:
                query = query.filter(Job.status == status)
            
            if candidate_id:
                query = query.filter(Job.candidate_id == candidate_id)
            
            if user_id:
                query = query.filter(Job.candidate.has(owner_id=user_id))
            
            # Order by creation date (newest first)
            jobs = query.order_by(
                desc(Job.created_at)
            ).offset(offset).limit(limit).all()
            
            return jobs
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get jobs: {str(e)}")
            raise
    
    @staticmethod
    def update_job_status(
        db: Session,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
        status: JobStatus,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> Optional[Job]:
        """
        Update job status and progress.
        
        Args:
            db: Database session
            job_id: Job ID
            organization_id: Organization ID
            status: New status
            progress: Optional progress (0-100)
            error: Optional error message
            metadata_update: Optional metadata updates
            
        Returns:
            Updated job or None if not found
        """
        try:
            job = db.query(Job).filter(
                Job.id == job_id,
                Job.candidate.has(organization_id=organization_id)
            ).first()
            
            if not job:
                return None
            
            # Update fields
            job.status = status
            
            if progress is not None:
                job.progress = max(0, min(100, progress))
            
            if error:
                job.error = error
            
            # Update timestamps based on status
            if status == JobStatus.PROCESSING and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED] and not job.completed_at:
                job.completed_at = datetime.utcnow()
            
            # Update metadata
            if metadata_update and job.metadata:
                job.metadata.update(metadata_update)
            elif metadata_update:
                job.metadata = metadata_update
            
            job.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(job)
            
            logger.info(f"Updated job {job_id} to {status} (progress: {progress})")
            return job
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to update job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def retry_failed_job(
        db: Session,
        job_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Optional[Job]:
        """
        Retry a failed job.
        
        Args:
            db: Database session
            job_id: Job ID
            organization_id: Organization ID
            
        Returns:
            New job or None if original not found
        """
        try:
            original_job = db.query(Job).filter(
                Job.id == job_id,
                Job.candidate.has(organization_id=organization_id)
            ).first()
            
            if not original_job:
                return None
            
            # Create new job based on original
            new_job = Job(
                id=uuid.uuid4(),
                type=original_job.type,
                status=JobStatus.QUEUED,
                candidate_id=original_job.candidate_id,
                resume_id=original_job.resume_id,
                message_id=original_job.message_id,
                metadata={
                    **original_job.metadata,
                    "retry_of": str(original_job.id),
                    "retry_count": original_job.metadata.get("retry_count", 0) + 1
                },
                created_at=datetime.utcnow()
            )
            
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            
            # Update original job metadata
            original_job.metadata["retried_as"] = str(new_job.id)
            db.commit()
            
            logger.info(f"Retried job {original_job.id} as {new_job.id}")
            return new_job
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to retry job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def cancel_job(
        db: Session,
        job_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        """
        Cancel a queued or processing job.
        
        Args:
            db: Database session
            job_id: Job ID
            organization_id: Organization ID
            
        Returns:
            True if cancelled, False if not found or cannot cancel
        """
        try:
            job = db.query(Job).filter(
                Job.id == job_id,
                Job.candidate.has(organization_id=organization_id),
                Job.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING])
            ).first()
            
            if not job:
                return False
            
            job.status = JobStatus.FAILED
            job.error = "Cancelled by user"
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Cancelled job: {job_id}")
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_job_stats(
        db: Session,
        organization_id: uuid.UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get job statistics.
        
        Args:
            db: Database session
            organization_id: Organization ID
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            from sqlalchemy import func
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Base query
            query = db.query(Job).join(Candidate).filter(
                Candidate.organization_id == organization_id,
                Job.created_at >= cutoff_date
            )
            
            # Total jobs
            total_jobs = query.count()
            
            # Count by status
            status_counts = {}
            status_query = query.with_entities(
                Job.status,
                func.count(Job.id)
            ).group_by(Job.status).all()
            
            for status, count in status_query:
                status_counts[status] = count
            
            # Count by type
            type_counts = {}
            type_query = query.with_entities(
                Job.type,
                func.count(Job.id)
            ).group_by(Job.type).all()
            
            for job_type, count in type_query:
                type_counts[job_type] = count
            
            # Average duration for completed jobs
            avg_duration = None
            duration_query = db.query(
                func.avg(func.extract('epoch', Job.completed_at - Job.started_at))
            ).join(Candidate).filter(
                Candidate.organization_id == organization_id,
                Job.status == JobStatus.COMPLETED,
                Job.started_at.isnot(None),
                Job.completed_at.isnot(None),
                Job.created_at >= cutoff_date
            ).scalar()
            
            if duration_query:
                avg_duration = round(float(duration_query), 2)
            
            # Failed jobs with errors
            failed_jobs = query.filter(
                Job.status == JobStatus.FAILED,
                Job.error.isnot(None)
            ).with_entities(
                Job.type,
                Job.error,
                Job.created_at
            ).order_by(desc(Job.created_at)).limit(10).all()
            
            return {
                "total": total_jobs,
                "by_status": status_counts,
                "by_type": type_counts,
                "avg_duration_seconds": avg_duration,
                "recent_failures": [
                    {
                        "type": job.type,
                        "error": job.error[:100] if job.error else "Unknown error",
                        "created_at": job.created_at.isoformat()
                    }
                    for job in failed_jobs
                ]
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get job stats: {str(e)}")
            raise
    
    @staticmethod
    def cleanup_old_jobs(
        db: Session,
        organization_id: uuid.UUID,
        days: int = 30
    ) -> int:
        """
        Clean up old completed/failed jobs.
        
        Args:
            db: Database session
            organization_id: Organization ID
            days: Jobs older than this many days will be deleted
            
        Returns:
            Number of jobs deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Find old jobs to delete
            old_jobs = db.query(Job).join(Candidate).filter(
                Candidate.organization_id == organization_id,
                Job.created_at < cutoff_date,
                Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
            ).all()
            
            deleted_count = len(old_jobs)
            
            # Delete jobs
            for job in old_jobs:
                db.delete(job)
            
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old jobs (older than {days} days)")
            
            return deleted_count
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to cleanup old jobs: {str(e)}")
            raise
    
    @staticmethod
    def format_job_response(job: Job) -> Dict[str, Any]:
        """Format job for API response."""
        response = {
            "id": str(job.id),
            "type": job.type,
            "status": job.status,
            "progress": job.progress,
            "createdAt": job.created_at.isoformat(),
            "startedAt": job.started_at.isoformat() if job.started_at else None,
            "completedAt": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
            "metadata": job.metadata,
            "candidateId": str(job.candidate_id) if job.candidate_id else None,
            "resumeId": str(job.resume_id) if job.resume_id else None,
            "messageId": str(job.message_id) if job.message_id else None
        }
        
        # Include candidate name if available
        if job.candidate:
            response["candidateName"] = job.candidate.name
            response["candidateEmail"] = job.candidate.email
        
        return response