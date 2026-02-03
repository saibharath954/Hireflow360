# backend/app/workers/background.py
import uuid
from datetime import datetime
from typing import Optional
import time
import random

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import (
    Candidate, Resume, ParsedField, CandidateSkill,
    Job, JobType, JobStatus, Message
)

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
        time.sleep(2)
        
        # Update job progress
        job.progress = 50
        db.commit()
        
        # Mock parsing results
        # In production, this would call actual OCR and LLM services
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
        
        # Get candidate
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            # Update candidate with parsed data
            candidate.name = parsed_data["name"]
            candidate.email = parsed_data["email"]
            candidate.phone = parsed_data["phone"]
            candidate.years_experience = parsed_data["experience"]
            candidate.current_company = parsed_data["current_company"]
            candidate.education = parsed_data["education"]
            candidate.location = parsed_data["location"]
            candidate.overall_confidence = 75.0
            
            # Clear existing skills
            db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).delete()
            
            # Add new skills
            for skill in parsed_data["skills"]:
                candidate_skill = CandidateSkill(
                    candidate_id=candidate_id,
                    skill=skill,
                    confidence=0.9
                )
                db.add(candidate_skill)
            
            # Clear existing parsed fields
            db.query(ParsedField).filter(ParsedField.candidate_id == candidate_id).delete()
            
            # Add parsed fields
            for field_name, value in parsed_data.items():
                if field_name == "skills":
                    continue
                    
                parsed_field = ParsedField(
                    candidate_id=candidate_id,
                    name=field_name,
                    value=str(value),
                    confidence=85.0,
                    raw_extraction=str(value),
                    source="resume"
                )
                db.add(parsed_field)
            
            # Initialize conversation state if not exists
            if not candidate.conversation_state:
                candidate.conversation_state = {
                    "fields": {
                        "name": {"value": parsed_data["name"], "confidence": 0.9, "asked": False, "answered": True, "source": "resume"},
                        "email": {"value": parsed_data["email"], "confidence": 0.9, "asked": False, "answered": True, "source": "resume"},
                        "phone": {"value": parsed_data["phone"], "confidence": 0.7, "asked": False, "answered": False, "source": "resume"},
                        "experience": {"value": parsed_data["experience"], "confidence": 0.8, "asked": False, "answered": True, "source": "resume"},
                        "skills": {"value": parsed_data["skills"], "confidence": 0.9, "asked": False, "answered": True, "source": "resume"},
                        "currentCompany": {"value": parsed_data["current_company"], "confidence": 0.8, "asked": False, "answered": False, "source": "resume"},
                        "education": {"value": parsed_data["education"], "confidence": 0.9, "asked": False, "answered": True, "source": "resume"},
                        "location": {"value": parsed_data["location"], "confidence": 0.7, "asked": False, "answered": False, "source": "resume"},
                    }
                }
            
            candidate.updated_at = datetime.utcnow()
        
        # Update resume
        resume.parsed_at = datetime.utcnow()
        resume.raw_text = f"Mock raw text from {resume.file_name}"
        
        # Complete job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        # Update job with error
        if 'job' in locals():
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        raise e
    finally:
        db.close()

def send_message_job(message_id: str, job_id: str):
    """Background job to send message"""
    db = SessionLocal()
    try:
        # Get job and message
        job = db.query(Job).filter(Job.id == job_id).first()
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not job or not message:
            return
        
        # Update job status
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.progress = 10
        db.commit()
        
        # Simulate sending delay (human-like)
        delay_seconds = random.randint(3, 10)
        time.sleep(delay_seconds)
        
        # Update job progress
        job.progress = 50
        db.commit()
        
        # Simulate more processing
        time.sleep(2)
        
        # Update message status
        message.status = "sent"
        
        # Complete job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        # Update job with error
        if 'job' in locals():
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        raise e
    finally:
        db.close()