# backend/app/services/resume_service.py
"""
Resume Service
Handles all business logic related to resume processing.
"""

import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import pdf2image
from PIL import Image
import pytesseract
from docx import Document

from app.models.models import (
    Resume, Candidate, CandidateSkill, ParsedField,
    Job, JobType, JobStatus
)
from app.core.config import settings
from app.core.logging import logger
from app.workers.background import process_resume_upload


class ResumeService:
    """Service for resume-related operations"""
    
    @staticmethod
    def upload_resume(
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        db: Session,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        file_name: str = "resume.pdf",
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Process resume upload from file or URL.
        
        Args:
            db: Database session
            file_path: Path to uploaded file (optional)
            file_url: URL to resume (optional)
            file_name: Original filename
            organization_id: Organization ID
            user_id: User ID who uploaded
            
        Returns:
            Tuple of (response_data, error_message)
        """
        try:
            # Validate input
            if not file_path and not file_url:
                return None, "Either file_path or file_url must be provided"
            
            # Generate IDs
            resume_id = uuid.uuid4()
            candidate_id = uuid.uuid4()
            job_id = uuid.uuid4()
            
            # Determine file type
            if file_path:
                file_ext = os.path.splitext(file_path)[1].lower()
                storage_path = file_path
            else:
                file_ext = os.path.splitext(file_name)[1].lower()
                storage_path = file_url
            
            # Validate file type
            if file_ext not in ['.pdf', '.docx', '.doc']:
                return None, f"Unsupported file type: {file_ext}"
            
            file_type = "pdf" if file_ext == '.pdf' else 'docx'
            
            # Create resume record
            resume = Resume(
                id=resume_id,
                candidate_id=candidate_id,
                file_name=file_name,
                file_url=storage_path,
                file_type=file_type,
                uploaded_at=datetime.utcnow()
            )
            
            # Create candidate placeholder
            candidate_name = ResumeService._extract_name_from_filename(file_name)
            candidate = Candidate(
                id=candidate_id,
                organization_id=organization_id,
                owner_id=user_id,
                name=candidate_name,
                email=f"candidate_{int(datetime.utcnow().timestamp())}@example.com",
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
                metadata={
                    "file_name": file_name,
                    "file_type": file_type,
                    "uploaded_by": str(user_id)
                },
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db.add(candidate)
            db.add(resume)
            db.add(job)
            db.commit()
            
            # Copy file to uploads directory if it's a local file
            if file_path and os.path.exists(file_path):
                uploads_dir = os.path.join(settings.UPLOAD_DIR, str(resume_id))
                os.makedirs(uploads_dir, exist_ok=True)
                dest_path = os.path.join(uploads_dir, file_name)
                shutil.copy2(file_path, dest_path)
                
                # Update resume with local URL
                resume.file_url = f"/uploads/{resume_id}/{file_name}"
                db.commit()
            
            # Trigger background processing
            process_resume_upload.delay(
                resume_id=str(resume_id),
                candidate_id=str(candidate_id),
                job_id=str(job_id)
            )
            
            response_data = {
                "resumeId": str(resume_id),
                "candidateId": str(candidate_id),
                "jobId": str(job_id)
            }
            
            logger.info(f"Resume uploaded: {file_name}, Job: {job_id}")
            return response_data, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to upload resume: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def reprocess_resume(
        db: Session,
        resume_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Reprocess an existing resume.
        
        Args:
            db: Database session
            resume_id: Resume ID
            organization_id: Organization ID
            
        Returns:
            Tuple of (response_data, error_message)
        """
        try:
            # Get resume with candidate check
            resume = db.query(Resume).join(Candidate).filter(
                Resume.id == resume_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not resume:
                return None, "Resume not found"
            
            # Create new job
            job_id = uuid.uuid4()
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
                resume_id=str(resume_id),
                candidate_id=str(resume.candidate_id),
                job_id=str(job_id),
                reprocess=True
            )
            
            response_data = {"jobId": str(job_id)}
            logger.info(f"Resume reprocessing triggered: {resume_id}, Job: {job_id}")
            return response_data, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to reprocess resume: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def parse_resume_file(
        resume_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
        reprocess: bool = False
    ) -> bool:
        """
        Parse resume file (OCR, text extraction, parsing).
        
        Args:
            resume_id: Resume ID
            candidate_id: Candidate ID
            job_id: Job ID
            reprocess: Whether this is a reprocessing
            
        Returns:
            Success status
        """
        from app.core.database import SessionLocal
        db = SessionLocal()
        
        try:
            # Get job and resume
            job = db.query(Job).filter(Job.id == job_id).first()
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            
            if not job or not resume or not candidate:
                logger.error(f"Invalid IDs: job={job_id}, resume={resume_id}, candidate={candidate_id}")
                return False
            
            # Update job status
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            job.progress = 10
            db.commit()
            
            # Extract text from resume
            raw_text = ResumeService._extract_text_from_resume(resume)
            
            # Parse text using AI/ML (mock implementation)
            parsed_data = ResumeService._parse_resume_text(raw_text, resume.file_name)
            
            # Update job progress
            job.progress = 50
            db.commit()
            
            # Update candidate with parsed data
            ResumeService._update_candidate_from_parsed_data(
                db, candidate, parsed_data, resume, reprocess
            )
            
            # Update resume
            resume.raw_text = raw_text[:5000]  # Store first 5000 chars
            resume.parsed_at = datetime.utcnow()
            
            # Complete job
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Resume parsed successfully: {resume.file_name}")
            return True
            
        except Exception as e:
            # Update job with error
            if 'job' in locals():
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.utcnow()
                db.commit()
            
            logger.error(f"Failed to parse resume: {str(e)}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_resume_by_id(
        db: Session,
        resume_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Optional[Resume]:
        """
        Get resume by ID with security check.
        
        Args:
            db: Database session
            resume_id: Resume ID
            organization_id: Organization ID
            
        Returns:
            Resume object or None
        """
        try:
            resume = db.query(Resume).join(Candidate).filter(
                Resume.id == resume_id,
                Candidate.organization_id == organization_id
            ).first()
            
            return resume
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get resume {resume_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_resumes_by_candidate(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[Resume]:
        """
        Get all resumes for a candidate.
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            organization_id: Organization ID
            
        Returns:
            List of resumes
        """
        try:
            resumes = db.query(Resume).join(Candidate).filter(
                Resume.candidate_id == candidate_id,
                Candidate.organization_id == organization_id
            ).all()
            
            return resumes
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get resumes for candidate {candidate_id}: {str(e)}")
            raise
    
    @staticmethod
    def delete_resume(
        db: Session,
        resume_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        """
        Delete a resume.
        
        Args:
            db: Database session
            resume_id: Resume ID
            organization_id: Organization ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            resume = db.query(Resume).join(Candidate).filter(
                Resume.id == resume_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not resume:
                return False
            
            # Delete file from storage
            if resume.file_url and resume.file_url.startswith("/uploads/"):
                file_path = os.path.join(settings.UPLOAD_DIR, resume.file_url.replace("/uploads/", "", 1))
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Delete resume record
            db.delete(resume)
            db.commit()
            
            logger.info(f"Deleted resume: {resume.file_name}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete resume {resume_id}: {str(e)}")
            return False
    
    # Helper Methods
    
    @staticmethod
    def _extract_name_from_filename(filename: str) -> str:
        """Extract candidate name from filename."""
        name = filename.replace('.pdf', '').replace('.docx', '').replace('.doc', '')
        name = name.replace('_', ' ').replace('-', ' ')
        name = ' '.join(word.capitalize() for word in name.split())
        return name
    
    @staticmethod
    def _extract_text_from_resume(resume: Resume) -> str:
        """Extract text from resume file."""
        try:
            if resume.file_type == 'pdf':
                # Check if it's an image PDF
                if resume.file_url.startswith('http'):
                    # URL - can't process locally
                    return f"PDF from URL: {resume.file_url}"
                
                file_path = os.path.join(settings.UPLOAD_DIR, resume.file_url.replace("/uploads/", "", 1))
                
                # Try text extraction first
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text()
                        
                        if text.strip():  # If text extraction worked
                            return text
                except:
                    pass
                
                # Fallback to OCR for image PDFs
                try:
                    images = pdf2image.convert_from_path(file_path)
                    text = ""
                    for image in images:
                        text += pytesseract.image_to_string(image)
                    return text
                except:
                    return "Failed to extract text from PDF"
                
            elif resume.file_type == 'docx':
                if resume.file_url.startswith('http'):
                    return f"DOCX from URL: {resume.file_url}"
                
                file_path = os.path.join(settings.UPLOAD_DIR, resume.file_url.replace("/uploads/", "", 1))
                
                try:
                    doc = Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    return text
                except:
                    return "Failed to extract text from DOCX"
            
            else:
                return f"Unsupported file type: {resume.file_type}"
                
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return f"Error extracting text: {str(e)}"
    
    @staticmethod
    def _parse_resume_text(raw_text: str, filename: str) -> Dict[str, Any]:
        """Parse resume text to extract structured data."""
        # Mock parsing - in production, use LLM/ML models
        
        import random
        from datetime import datetime
        
        # Extract email (simple regex)
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
        email = email_match.group(0) if email_match else f"candidate_{int(datetime.utcnow().timestamp())}@example.com"
        
        # Extract phone (simple regex)
        phone_match = re.search(r'(\+\d{1,3}[-\.\s]?)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}', raw_text)
        phone = phone_match.group(0) if phone_match else f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        
        # Mock data
        parsed_data = {
            "name": ResumeService._extract_name_from_filename(filename),
            "email": email,
            "phone": phone,
            "experience": random.randint(1, 20),
            "skills": random.sample([
                "Python", "JavaScript", "React", "Node.js", "AWS", 
                "Docker", "Kubernetes", "SQL", "MongoDB", "FastAPI",
                "TypeScript", "GraphQL", "Redis", "PostgreSQL", "Git"
            ], k=random.randint(3, 8)),
            "current_company": random.choice([
                "TechCorp Inc", "InnovateSoft", "DataSystems Ltd",
                "CloudSolutions", "AI Research Lab", "StartupXYZ"
            ]),
            "education": random.choice([
                "BSc Computer Science, University of Technology",
                "MSc Software Engineering, State University",
                "PhD Artificial Intelligence, Institute of Technology",
                "BEng Computer Engineering, Engineering College"
            ]),
            "location": random.choice([
                "San Francisco, CA", "New York, NY", "Remote",
                "Austin, TX", "Seattle, WA", "Boston, MA"
            ]),
            "raw_extractions": {
                "name": f"Extracted from filename: {filename}",
                "email": email,
                "phone": phone if phone_match else "Not found in text",
                "experience": f"Estimated {random.randint(1, 20)} years based on content",
                "skills": "Extracted from skills section",
                "current_company": "Found in employment history",
                "education": "Found in education section",
                "location": "Found in contact information"
            }
        }
        
        return parsed_data
    
    @staticmethod
    def _update_candidate_from_parsed_data(
        db: Session,
        candidate: Candidate,
        parsed_data: Dict[str, Any],
        resume: Resume,
        reprocess: bool = False
    ):
        """Update candidate with parsed data."""
        # Update candidate fields
        candidate.name = parsed_data["name"]
        candidate.email = parsed_data["email"]
        candidate.phone = parsed_data["phone"]
        candidate.years_experience = parsed_data["experience"]
        candidate.current_company = parsed_data["current_company"]
        candidate.education = parsed_data["education"]
        candidate.location = parsed_data["location"]
        candidate.updated_at = datetime.utcnow()
        
        # Clear existing skills if reprocessing
        if reprocess:
            db.query(CandidateSkill).filter(
                CandidateSkill.candidate_id == candidate.id
            ).delete()
        
        # Add/update skills
        for skill in parsed_data["skills"]:
            candidate_skill = CandidateSkill(
                candidate_id=candidate.id,
                skill=skill,
                confidence=0.9  # Mock confidence
            )
            db.add(candidate_skill)
        
        # Clear existing parsed fields if reprocessing
        if reprocess:
            db.query(ParsedField).filter(
                ParsedField.candidate_id == candidate.id
            ).delete()
        
        # Add parsed fields
        for field_name, value in parsed_data.items():
            if field_name in ["raw_extractions", "skills"]:
                continue
                
            parsed_field = ParsedField(
                candidate_id=candidate.id,
                name=field_name,
                value=str(value),
                confidence=85.0,  # Mock confidence
                raw_extraction=parsed_data["raw_extractions"].get(field_name, ""),
                source="resume"
            )
            db.add(parsed_field)
        
        # Update conversation state
        if not candidate.conversation_state or reprocess:
            candidate.conversation_state = ResumeService._create_conversation_state(parsed_data)
        
        # Update overall confidence
        candidate.overall_confidence = ResumeService._calculate_parsed_confidence(parsed_data)
    
    @staticmethod
    def _create_conversation_state(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create conversation state from parsed data."""
        fields = {}
        
        field_mapping = {
            "name": "name",
            "email": "email", 
            "phone": "phone",
            "experience": "experience",
            "current_company": "currentCompany",
            "education": "education",
            "location": "location"
        }
        
        for parse_key, field_key in field_mapping.items():
            value = parsed_data.get(parse_key)
            if value:
                fields[field_key] = {
                    "value": value,
                    "confidence": 0.8 if parse_key in ["name", "email"] else 0.7,
                    "asked": False,
                    "answered": True,
                    "source": "resume"
                }
            else:
                fields[field_key] = {
                    "value": None,
                    "confidence": 0.0,
                    "asked": False,
                    "answered": False,
                    "source": None
                }
        
        # Handle skills separately
        skills = parsed_data.get("skills", [])
        fields["skills"] = {
            "value": skills,
            "confidence": 0.9 if skills else 0.0,
            "asked": False,
            "answered": bool(skills),
            "source": "resume" if skills else None
        }
        
        return {"fields": fields}
    
    @staticmethod
    def _calculate_parsed_confidence(parsed_data: Dict[str, Any]) -> float:
        """Calculate confidence score for parsed data."""
        required_fields = ["name", "email", "experience", "skills", "education"]
        filled_fields = sum(1 for field in required_fields if parsed_data.get(field))
        
        optional_fields = ["phone", "current_company", "location"]
        filled_optional = sum(1 for field in optional_fields if parsed_data.get(field))
        
        # Weight required fields more heavily
        total_score = (filled_fields * 1.5) + filled_optional
        max_score = (len(required_fields) * 1.5) + len(optional_fields)
        
        return (total_score / max_score * 100) if max_score > 0 else 0