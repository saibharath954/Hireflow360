# backend/app/services/resume_service.py
"""
Updated Resume Service using the real parser
"""

import os
import uuid
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import requests

from app.models.models import (
    Resume, Candidate, CandidateSkill, ParsedField,
    Job, JobStatus, WorkExperience, CandidateStatus
)
from app.core.config import settings
from app.core.logging import logger
from app.workers.background import process_resume_upload
from app.services.resume_parser import ResumeParser, ParsedResume

def _extract_drive_file_id(url: str) -> Optional[str]:
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

class ResumeService:
    """Updated with real parsing"""
    
    @staticmethod
    def parse_resume_content(
        resume_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
        reprocess: bool = False
    ) -> bool:
        """Parse resume content with real extraction"""
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
            
            # Get file content
            file_content = ResumeService._get_file_content(resume)
            if not file_content:
                job.status = JobStatus.FAILED
                job.error = "Could not read resume file"
                job.completed_at = datetime.utcnow()
                db.commit()
                return False
            
            # Update job progress
            job.progress = 30
            db.commit()
            
            # Parse with real parser
            parser = ResumeParser(use_ocr=True, use_nlp=True)
            parsed_data = parser.parse_resume(file_content, resume.file_name)
            
            # Update job progress
            job.progress = 70
            db.commit()
            
            # Update candidate with real data
            ResumeService._update_candidate_with_real_data(
                db, candidate, parsed_data, resume, reprocess
            )
            
            # Update resume
            resume.raw_text = parsed_data.raw_text or ""
            resume.text_length = len(resume.raw_text)
            resume.language = "en"  # Could detect language
            resume.is_parsed = True
            resume.parsed_at = datetime.utcnow()
            resume.parsing_engine = "resume_parser"
            resume.parsing_version = "1.0"
            
            # Calculate quality metrics
            if resume.raw_text:
                resume.quality_score = ResumeService._calculate_quality_score(parsed_data)
                resume.readability_score = ResumeService._calculate_readability(resume.raw_text)
                resume.parsing_confidence = sum(parsed_data.confidence_scores.values()) / len(parsed_data.confidence_scores) if parsed_data.confidence_scores else 0
            
            # Complete job
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()

            job.job_metadata = {   # ✅ FIX 1
                **(job.job_metadata or {}),
                "text_length": resume.text_length,
                "parsed_fields": len([v for v in parsed_data.__dict__.values() if v]),
                "confidence_avg": resume.parsing_confidence or 0,
                "parsing_engine": resume.parsing_engine
            }

            db.commit()
        
            logger.info(f"Resume parsed successfully: {resume.file_name}, "
                       f"Text length: {resume.text_length}, "
                       f"Parsing confidence: {resume.parsing_confidence}")
            return True
            
        except Exception as e:
            db.rollback()  

            logger.exception("Failed to parse resume")

            # Start a NEW clean transaction
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to update job failure status")

            return False

        finally:
            db.close()
    
    @staticmethod
    def _get_file_content(resume: Resume) -> Optional[bytes]:
        try:
            url = resume.file_url

            if url.startswith("http"):
                # ✅ Handle Google Drive links
                if "drive.google.com" in url:
                    file_id = _extract_drive_file_id(url)
                    if not file_id:
                        logger.error("Invalid Google Drive link")
                        return None

                    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    response = requests.get(download_url, timeout=30)

                else:
                    # Normal HTTP file
                    response = requests.get(url, timeout=30)

                if response.status_code == 200:
                    return response.content

            else:
                # Local file
                file_path = os.path.join(
                    settings.UPLOAD_DIR,
                    resume.file_url.replace("/uploads/", "", 1)
                )
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        return f.read()

        except Exception as e:
            logger.error(f"Failed to get file content: {str(e)}")

        return None
        
    @staticmethod
    def _update_candidate_with_real_data(
        db: Session,
        candidate: Candidate,
        parsed_data: ParsedResume,
        resume: Resume,
        reprocess: bool = False
    ):
        """Update candidate with real parsed data"""
        # Clear existing data if reprocessing
        if reprocess:
            db.query(CandidateSkill).filter(
                CandidateSkill.candidate_id == candidate.id
            ).delete()
            
            db.query(ParsedField).filter(
                ParsedField.candidate_id == candidate.id
            ).delete()
            
            db.query(WorkExperience).filter(
                WorkExperience.candidate_id == candidate.id
            ).delete()
        
        # Update candidate fields
        candidate.name = parsed_data.name or candidate.name
        # Handle email carefully (unique per org)
        if parsed_data.email and parsed_data.email != candidate.email:
            existing_candidate = (
                db.query(Candidate)
                .filter(
                    Candidate.email == parsed_data.email,
                    Candidate.organization_id == candidate.organization_id,
                    Candidate.id != candidate.id
                )
                .first()
            )

            if existing_candidate:
                # Email already belongs to another candidate
                logger.warning(
                    f"Duplicate email detected: {parsed_data.email}. "
                    f"Keeping existing candidate {existing_candidate.id}, "
                    f"skipping email update for {candidate.id}"
                )
                # Optional: mark status or flag duplicate
                candidate.status = CandidateStatus.NEEDS_CLARIFICATION
            else:
                candidate.email = parsed_data.email
        candidate.phone = parsed_data.phone or candidate.phone
        candidate.current_title = parsed_data.current_title or candidate.current_title
        candidate.current_company = parsed_data.current_company or candidate.current_company
        candidate.years_experience = parsed_data.years_experience or candidate.years_experience
        candidate.education = json.dumps(parsed_data.education) if parsed_data.education else candidate.education
        candidate.degree = parsed_data.degree or candidate.degree
        candidate.university = parsed_data.university or candidate.university
        candidate.graduation_year = parsed_data.graduation_year or candidate.graduation_year
        candidate.location = parsed_data.location or candidate.location
        candidate.city = parsed_data.city or candidate.city
        candidate.country = parsed_data.country or candidate.country
        candidate.linkedin_url = parsed_data.linkedin_url or candidate.linkedin_url
        candidate.github_url = parsed_data.github_url or candidate.github_url
        candidate.portfolio_url = parsed_data.portfolio_url or candidate.portfolio_url
        candidate.updated_at = datetime.utcnow()
        
        # Update work experience
        for exp in parsed_data.work_experience:
            work_exp = WorkExperience(
                id=uuid.uuid4(),
                candidate_id=candidate.id,
                company=exp.get('company', ''),
                title=exp.get('title', ''),
                location=exp.get('location'),
                start_date=exp.get('start_date'),
                end_date=exp.get('end_date'),
                is_current=exp.get('is_current', False),
                description=exp.get('description')
            )
            db.add(work_exp)
        
        # Update skills with categorization
        for skill in parsed_data.skills:
            category = None
            skill_lower = skill.lower()
            
            if skill_lower in parsed_data.skill_categories.get('technical', []):
                category = 'programming'
            elif skill_lower in parsed_data.skill_categories.get('soft', []):
                category = 'soft'
            elif skill_lower in parsed_data.skill_categories.get('tools', []):
                category = 'tool'
            elif skill_lower in parsed_data.skill_categories.get('languages', []):
                category = 'language'
            
            candidate_skill = CandidateSkill(
                candidate_id=candidate.id,
                skill=skill,
                category=category,
                confidence=parsed_data.confidence_scores.get('skills', 0.7),
                source="resume"
            )
            db.add(candidate_skill)
        
        # Create parsed fields
        for field_name, value in [
            ('name', parsed_data.name),
            ('email', parsed_data.email),
            ('phone', parsed_data.phone),
            ('current_title', parsed_data.current_title),
            ('current_company', parsed_data.current_company),
            ('years_experience', parsed_data.years_experience),
            ('degree', parsed_data.degree),
            ('university', parsed_data.university),
            ('location', parsed_data.location),
            ('summary', parsed_data.summary)
        ]:
            if value:
                parsed_field = ParsedField(
                    candidate_id=candidate.id,
                    name=field_name,
                    value=str(value),
                    confidence=parsed_data.confidence_scores.get(field_name, 0.8) * 100,
                    raw_extraction=str(value),
                    source="resume_parser",
                    parser_version="1.0"
                )
                db.add(parsed_field)
        
        # Add skills as parsed field
        if parsed_data.skills:
            parsed_field = ParsedField(
                candidate_id=candidate.id,
                name='skills',
                value=','.join(parsed_data.skills[:10]),
                confidence=parsed_data.confidence_scores.get('skills', 0.7) * 100,
                raw_extraction=','.join(parsed_data.skills[:10]),
                source="resume_parser",
                parser_version="1.0"
            )
            db.add(parsed_field)
        
        # Update conversation state
        candidate.conversation_state = ResumeService._create_conversation_state_from_parsed(parsed_data)
        
        # Calculate overall confidence
        if parsed_data.confidence_scores:
            avg_confidence = sum(parsed_data.confidence_scores.values()) / len(parsed_data.confidence_scores)
            candidate.overall_confidence = avg_confidence * 100
    
    @staticmethod
    def _create_conversation_state_from_parsed(parsed_data: ParsedResume) -> Dict[str, Any]:
        """Create conversation state from parsed resume"""
        fields = {}
        
        field_mapping = {
            "name": "name",
            "email": "email", 
            "phone": "phone",
            "years_experience": "experience",
            "current_company": "currentCompany",
            "current_title": "currentTitle",
            "education": "education",
            "location": "location",
            "skills": "skills"
        }
        
        confidence_scores = parsed_data.confidence_scores or {}
        
        for parse_key, field_key in field_mapping.items():
            value = getattr(parsed_data, parse_key, None)
            confidence = confidence_scores.get(parse_key, 0.0)
            
            if value:
                fields[field_key] = {
                    "value": value,
                    "confidence": confidence,
                    "asked": False,
                    "answered": confidence > 0.5,
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
        
        # Handle skills
        if parsed_data.skills:
            skills_confidence = confidence_scores.get('skills', 0.0)
            fields["skills"] = {
                "value": parsed_data.skills,
                "confidence": skills_confidence,
                "asked": False,
                "answered": bool(parsed_data.skills) and skills_confidence > 0.5,
                "source": "resume"
            }
        
        return {"fields": fields}
    
    @staticmethod
    def _calculate_quality_score(parsed_data: ParsedResume) -> float:
        """Calculate quality score for parsed resume"""
        scores = []
        
        # Name score
        if parsed_data.name:
            scores.append(1.0)
        
        # Email score
        if parsed_data.email:
            scores.append(1.0)
        
        # Skills score
        if parsed_data.skills:
            scores.append(min(1.0, len(parsed_data.skills) / 10))
        
        # Experience score
        if parsed_data.work_experience:
            scores.append(min(1.0, len(parsed_data.work_experience) / 5))
        
        # Education score
        if parsed_data.education:
            scores.append(1.0)
        
        return (sum(scores) / len(scores) * 100) if scores else 0.0
    
    @staticmethod
    def _calculate_readability(text: str) -> float:
        """Calculate readability score (simplified)"""
        if not text:
            return 0.0
        
        # Simple metrics
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        # Score based on ideal ranges
        sentence_score = 1.0 if 15 <= avg_sentence_length <= 25 else 0.5
        word_score = 1.0 if 4 <= avg_word_length <= 6 else 0.5
        
        return (sentence_score + word_score) / 2 * 100