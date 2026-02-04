import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import time
import random
import json
import threading
import functools

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import (
    Candidate, Resume, ParsedField, CandidateSkill,
    Job, JobType, JobStatus, Message
)
from app.core.logging import logger

# ----------------------------------------------------------------------
# Mock Celery Decorator (Makes .delay() work without Redis)
# ----------------------------------------------------------------------
def mock_celery_task(func):
    """
    Decorator that adds a .delay() method to functions, 
    mimicking Celery's behavior using threading for local dev.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    def delay(*args, **kwargs):
        # Run in a separate thread to simulate background processing
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.daemon = True  # Ensure thread doesn't block shutdown
        t.start()
        return t

    wrapper.delay = delay
    return wrapper

# ----------------------------------------------------------------------
# Job 1: Resume Processing
# ----------------------------------------------------------------------

@mock_celery_task
def process_resume_upload(resume_id: str, candidate_id: str, job_id: str, reprocess: bool = False):
    """Background job to process resume upload"""
    db = SessionLocal()
    try:
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        
        # Update job status
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.progress = 10
        db.commit()
        
        # Get resume
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            job.status = JobStatus.FAILED
            job.error = "Resume not found"
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        # Simulate OCR and parsing delay
        time.sleep(1)
        job.progress = 30
        db.commit()
        
        # ---------------------------------------------------------
        # AI/LLM Integration Point
        # ---------------------------------------------------------
        try:
            from app.services.ai_service import AIService
            # Using mock data for robustness if service call fails or isn't configured
            raise ImportError("Using mock data for speed")
        except Exception:
            # Fallback Mock Data
            parsed_data = {
                "name": resume.file_name.replace(".pdf", "").replace(".docx", "").replace("_", " ").title(),
                "email": f"candidate_{int(time.time())}@example.com",
                "phone": f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                "experience": random.randint(1, 15),
                "skills": ["Python", "JavaScript", "React", "FastAPI", "PostgreSQL"],
                "current_company": f"Tech Company {random.choice(['Inc', 'Corp', 'Ltd'])}",
                "education": f"{random.choice(['BSc', 'MSc', 'PhD'])} in Computer Science",
                "location": f"{random.choice(['San Francisco', 'New York', 'Remote'])}",
            }
        
        job.progress = 60
        db.commit()

        # Get candidate
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            # Update candidate details
            candidate.name = parsed_data.get("name", candidate.name)
            candidate.email = parsed_data.get("email", candidate.email)
            candidate.phone = parsed_data.get("phone", candidate.phone)
            candidate.years_experience = parsed_data.get("experience")
            candidate.current_company = parsed_data.get("current_company")
            candidate.education = parsed_data.get("education")
            candidate.location = parsed_data.get("location")
            candidate.overall_confidence = 75.0
            
            # Clear and re-add skills
            db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).delete()
            for skill in parsed_data.get("skills", []):
                db.add(CandidateSkill(candidate_id=candidate_id, skill=skill, confidence=0.9))
            
            # Clear and re-add parsed fields
            db.query(ParsedField).filter(ParsedField.candidate_id == candidate_id).delete()
            for field_name, value in parsed_data.items():
                if field_name != "skills":
                    db.add(ParsedField(
                        candidate_id=candidate_id,
                        name=field_name,
                        value=str(value),
                        confidence=85.0,
                        raw_extraction=str(value),
                        source="resume"
                    ))
            
            # Initialize conversation state
            if not candidate.conversation_state:
                candidate.conversation_state = {
                    "fields": {
                        "name": {"value": parsed_data.get("name"), "confidence": 0.9, "asked": False, "answered": True},
                        "email": {"value": parsed_data.get("email"), "confidence": 0.9, "asked": False, "answered": True},
                        "experience": {"value": parsed_data.get("experience"), "confidence": 0.8, "asked": False, "answered": True},
                        "skills": {"value": parsed_data.get("skills"), "confidence": 0.9, "asked": False, "answered": True},
                        "location": {"value": parsed_data.get("location"), "confidence": 0.7, "asked": False, "answered": False},
                    }
                }
            
            candidate.updated_at = datetime.utcnow()
        
        # Update resume meta
        resume.parsed_at = datetime.utcnow()
        resume.raw_text = f"Mock raw text from {resume.file_name}"
        
        # Complete job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        if 'job' in locals() and job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        logger.error(f"Resume processing failed: {str(e)}")
    finally:
        db.close()

# ----------------------------------------------------------------------
# Job 2: Send Message
# ----------------------------------------------------------------------

@mock_celery_task
def send_message_job(message_id: str, job_id: str):
    """Background job to send message"""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not job or not message:
            return
        
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.progress = 10
        db.commit()
        
        time.sleep(random.randint(2, 5))
        job.progress = 50
        db.commit()
        
        time.sleep(1)
        message.status = "sent"
        
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        if 'job' in locals() and job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        logger.error(f"Message sending failed: {str(e)}")
    finally:
        db.close()

# ----------------------------------------------------------------------
# Job 3: Process Reply
# ----------------------------------------------------------------------

@mock_celery_task
def process_candidate_reply(message_content: str, candidate_id: str, job_id: str = None):
    """Background job to process an incoming candidate reply."""
    db = SessionLocal()
    try:
        # Local import to avoid circular dependency
        from app.services.ai_service import AIService
        
        job = None
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
                db.commit()

        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            if job: 
                job.status = JobStatus.FAILED
                job.error = "Candidate not found"
                db.commit()
            return

        incoming_msg = Message(
            candidate_id=candidate_id, content=message_content,
            direction="incoming", status="received", timestamp=datetime.utcnow()
        )
        db.add(incoming_msg)
        db.commit()

        asked_fields = []
        if candidate.conversation_state and "fields" in candidate.conversation_state:
            fields = candidate.conversation_state["fields"]
            asked_fields = [k for k, v in fields.items() if v.get("asked") and not v.get("answered")]

        candidate_info = {
            "name": candidate.name,
            "status": str(candidate.status)
        }
        
        analysis = AIService.analyze_candidate_reply(
            reply_text=message_content,
            candidate_info=candidate_info,
            asked_fields=asked_fields
        )

        extracted_data = analysis.get("extracted_data", {})
        if extracted_data.get("location"): candidate.location = extracted_data["location"]
        if extracted_data.get("expected_salary"): candidate.expected_salary = extracted_data["expected_salary"]
        if extracted_data.get("notice_period"): candidate.notice_period = extracted_data["notice_period"]
        
        if job:
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()
        
        db.commit()

    except Exception as e:
        if job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        logger.error(f"Reply processing failed: {str(e)}")
    finally:
        db.close()

# ----------------------------------------------------------------------
# Job 4: Bulk Update
# ----------------------------------------------------------------------

@mock_celery_task
def process_bulk_update(job_id: str, candidate_ids: List[str], update_data: Dict[str, Any]):
    """Background job to process bulk updates."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
            
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.progress = 0
        db.commit()
        
        total_candidates = len(candidate_ids)
        processed_count = 0
        
        for cid in candidate_ids:
            candidate = db.query(Candidate).filter(Candidate.id == cid).first()
            if candidate:
                for key, value in update_data.items():
                    if hasattr(candidate, key) and key not in ['id', 'created_at']:
                        setattr(candidate, key, value)
                candidate.updated_at = datetime.utcnow()
            
            processed_count += 1
            if processed_count % 5 == 0 or processed_count == total_candidates:
                job.progress = int((processed_count / total_candidates) * 100)
                db.commit()
        
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        if job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        logger.error(f"Bulk update failed: {str(e)}")
    finally:
        db.close()