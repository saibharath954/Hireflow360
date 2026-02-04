# backend/app/services/candidate_service.py
"""
Candidate Service
Handles all business logic related to candidates.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import asc, or_, and_, func, desc
from sqlalchemy.exc import SQLAlchemyError

from app.models.models import (
    Candidate, CandidateSkill, ParsedField, 
    Resume, Message, Organization, User
)
from app.schemas.schemas import (
    CandidateCreate, CandidateUpdate, CandidateFilters,
    PaginatedResponse, ConversationState, FieldState
)
from app.core.database import get_db_context
from app.core.logging import logger


class CandidateService:
    """Service for candidate-related operations"""
    
    @staticmethod
    def create_candidate(
        db: Session,
        candidate_data: CandidateCreate,
        organization_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None
    ) -> Candidate:
        """
        Create a new candidate.
        
        Args:
            db: Database session
            candidate_data: Candidate creation data
            organization_id: Organization ID
            owner_id: Optional user ID who owns this candidate
            
        Returns:
            Created candidate
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Check for existing candidate by email
            existing = db.query(Candidate).filter(
                Candidate.email == candidate_data.email,
                Candidate.organization_id == organization_id
            ).first()
            
            if existing:
                # Update existing candidate
                for key, value in candidate_data.model_dump(exclude={"skills", "organization_id"}).items():
                    if value is not None:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                candidate = existing
            else:
                # Create new candidate
                candidate = Candidate(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                    owner_id=owner_id,
                    **candidate_data.model_dump(exclude={"skills", "organization_id"})
                )
                db.add(candidate)
            
            # Handle skills
            if candidate_data.skills:
                # Delete existing skills if updating
                if existing:
                    db.query(CandidateSkill).filter(
                        CandidateSkill.candidate_id == candidate.id
                    ).delete()
                
                # Add new skills
                for skill in candidate_data.skills:
                    candidate_skill = CandidateSkill(
                        candidate_id=candidate.id,
                        skill=skill,
                        confidence=1.0
                    )
                    db.add(candidate_skill)
            
            # Initialize conversation state if not exists
            if not candidate.conversation_state:
                candidate.conversation_state = CandidateService._initialize_conversation_state(candidate_data)
            
            candidate.overall_confidence = CandidateService._calculate_overall_confidence(candidate_data)
            candidate.created_at = datetime.utcnow()
            candidate.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(candidate)
            
            logger.info(f"Created/Updated candidate: {candidate.email}")
            return candidate
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to create candidate: {str(e)}")
            raise
    
    @staticmethod
    def get_candidate_by_id(
        db: Session, 
        candidate_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> Optional[Candidate]:
        """
        Get candidate by ID with all related data.
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            organization_id: Organization ID for security check
            
        Returns:
            Candidate object or None if not found
        """
        try:
            candidate = db.query(Candidate).options(
                joinedload(Candidate.skills),
                joinedload(Candidate.parsed_fields),
                joinedload(Candidate.resumes),
                joinedload(Candidate.messages),
                joinedload(Candidate.organization),
                joinedload(Candidate.owner)
            ).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            return candidate
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get candidate {candidate_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_candidates_with_filters(
        db: Session,
        organization_id: uuid.UUID,
        filters: Optional[CandidateFilters] = None,
        page: int = 1,
        page_size: int = 50,
        owner_id: Optional[uuid.UUID] = None,
        sort_by: str = "updated_at",   
        sort_order: str = "desc"
    ) -> PaginatedResponse:
        """
        Get paginated list of candidates with filtering.
        
        Args:
            db: Database session
            organization_id: Organization ID
            filters: Optional filters
            page: Page number (1-indexed)
            page_size: Items per page
            owner_id: Optional filter by owner
            
        Returns:
            Paginated response with candidates
        """
        try:
            query = db.query(Candidate).filter(
                Candidate.organization_id == organization_id
            )
            
            # Apply owner filter if specified
            if owner_id:
                query = query.filter(Candidate.owner_id == owner_id)
            
            # Apply filters
            if filters:
                query = CandidateService._apply_filters(query, filters)

            # --- ADD SORTING LOGIC HERE ---
            if sort_by:
                sort_attr = getattr(Candidate, sort_by, Candidate.updated_at)
                if sort_order == "desc":
                    query = query.order_by(desc(sort_attr))
                else:
                    query = query.order_by(asc(sort_attr))
            else:
                # Default sort
                query = query.order_by(desc(Candidate.updated_at))
                
            # Get total count
            total = query.count()
            
            # Calculate pagination
            offset = (page - 1) * page_size
            
            # Get paginated results with eager loading
            candidates = query.options(
                joinedload(Candidate.skills),
                joinedload(Candidate.resumes)
            ).order_by(
                desc(Candidate.updated_at)
            ).offset(offset).limit(page_size).all()
            
            # Format response
            items = [CandidateService._format_candidate_response(c) for c in candidates]
            
            return PaginatedResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                has_more=offset + len(items) < total
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get candidates: {str(e)}")
            raise
    
    @staticmethod
    def update_candidate(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        update_data: CandidateUpdate
    ) -> Optional[Candidate]:
        """
        Update candidate information.
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            organization_id: Organization ID
            update_data: Update data
            
        Returns:
            Updated candidate or None if not found
        """
        try:
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None
            
            update_dict = update_data.dict(exclude_unset=True)
            
            # Handle skills update
            if "skills" in update_dict:
                skills = update_dict.pop("skills", [])
                CandidateService._update_candidate_skills(db, candidate.id, skills)
            
            # Handle conversation state update
            if "conversation_state" in update_dict:
                candidate.conversation_state = update_dict.pop("conversation_state")
            
            # Update other fields
            for key, value in update_dict.items():
                if hasattr(candidate, key):
                    setattr(candidate, key, value)
            
            # Recalculate overall confidence
            candidate.overall_confidence = CandidateService._calculate_candidate_confidence(candidate)
            
            candidate.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(candidate)
            
            logger.info(f"Updated candidate: {candidate.email}")
            return candidate
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to update candidate {candidate_id}: {str(e)}")
            raise
    
    @staticmethod
    def delete_candidate(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        """
        Delete a candidate (soft delete).
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            organization_id: Organization ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return False
            
            # Soft delete - mark as inactive
            candidate.is_active = False
            candidate.deleted_at = datetime.utcnow()
            candidate.updated_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Soft deleted candidate: {candidate.email}")
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to delete candidate {candidate_id}: {str(e)}")
            raise
    
    @staticmethod
    def update_conversation_state(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        field_key: str,
        field_state: FieldState
    ) -> Optional[Candidate]:
        """
        Update conversation state for a specific field.
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            organization_id: Organization ID
            field_key: Field key to update
            field_state: New field state
            
        Returns:
            Updated candidate or None if not found
        """
        try:
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None
            
            # Initialize conversation state if not exists
            if not candidate.conversation_state:
                candidate.conversation_state = {"fields": {}}
            
            # Update the specific field
            candidate.conversation_state["fields"][field_key] = field_state.dict()
            
            # Recalculate overall confidence
            candidate.overall_confidence = CandidateService._calculate_candidate_confidence(candidate)
            
            candidate.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(candidate)
            
            logger.info(f"Updated conversation state for candidate {candidate_id}, field: {field_key}")
            return candidate
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to update conversation state: {str(e)}")
            raise
    
    @staticmethod
    def get_pending_fields(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[str]:
        """
        Get list of fields that are pending (not asked or not answered).
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            organization_id: Organization ID
            
        Returns:
            List of pending field keys
        """
        try:
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate or not candidate.conversation_state:
                return []
            
            pending_fields = []
            conversation_state = candidate.conversation_state
            
            for field_key, field_state in conversation_state.get("fields", {}).items():
                field_state_obj = FieldState(**field_state)
                if not field_state_obj.asked or not field_state_obj.answered:
                    pending_fields.append(field_key)
            
            return pending_fields
            
        except Exception as e:
            logger.error(f"Failed to get pending fields: {str(e)}")
            return []
    
    @staticmethod
    def get_candidate_stats(
        db: Session,
        organization_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for candidates.
        
        Args:
            db: Database session
            organization_id: Organization ID
            owner_id: Optional filter by owner
            
        Returns:
            Dictionary with statistics
        """
        try:
            query = db.query(Candidate).filter(
                Candidate.organization_id == organization_id,
                Candidate.is_active == True
            )
            
            if owner_id:
                query = query.filter(Candidate.owner_id == owner_id)
            
            # Total count
            total = query.count()
            
            # Count by status
            status_counts = {}
            status_query = query.with_entities(
                Candidate.status,
                func.count(Candidate.id)
            ).group_by(Candidate.status).all()
            
            for status, count in status_query:
                status_counts[status] = count
            
            # Average confidence
            avg_confidence = query.with_entities(
                func.avg(Candidate.overall_confidence)
            ).scalar() or 0
            
            # Recent activity (last 7 days)
            seven_days_ago = datetime.utcnow().replace(tzinfo=None) - timedelta(days=7)
            recent_count = query.filter(
                Candidate.created_at >= seven_days_ago
            ).count()
            
            return {
                "total": total,
                "by_status": status_counts,
                "avg_confidence": round(float(avg_confidence), 2),
                "recent_7_days": recent_count
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get candidate stats: {str(e)}")
            raise
    
    # Helper Methods
    
    @staticmethod
    def _apply_filters(query, filters: CandidateFilters):
        """Apply filters to query."""
        if filters.search:
            search = f"%{filters.search.lower()}%"
            query = query.filter(
                or_(
                    Candidate.name.ilike(search),
                    Candidate.email.ilike(search),
                    Candidate.current_company.ilike(search),
                    Candidate.location.ilike(search),
                    Candidate.education.ilike(search),
                    Candidate.id.in_(
                        db.query(CandidateSkill.candidate_id).filter(
                            CandidateSkill.skill.ilike(search)
                        )
                    )
                )
            )
        
        if filters.status and len(filters.status) > 0:
            query = query.filter(Candidate.status.in_(filters.status))
        
        if filters.skills and len(filters.skills) > 0:
            for skill in filters.skills:
                query = query.filter(
                    Candidate.id.in_(
                        db.query(CandidateSkill.candidate_id).filter(
                            CandidateSkill.skill.ilike(f"%{skill}%")
                        )
                    )
                )
        
        if filters.min_experience is not None:
            query = query.filter(
                or_(
                    Candidate.years_experience >= filters.min_experience,
                    Candidate.years_experience == None
                )
            )
        
        if filters.max_experience is not None:
            query = query.filter(
                Candidate.years_experience <= filters.max_experience
            )
        
        if filters.location:
            query = query.filter(Candidate.location.ilike(f"%{filters.location}%"))
        
        if filters.date_range:
            query = query.filter(
                Candidate.created_at.between(
                    filters.date_range["from"],
                    filters.date_range["to"]
                )
            )
        
        return query
    
    @staticmethod
    def _update_candidate_skills(db: Session, candidate_id: uuid.UUID, skills: List[str]):
        """Update candidate skills."""
        # Delete existing skills
        db.query(CandidateSkill).filter(
            CandidateSkill.candidate_id == candidate_id
        ).delete()
        
        # Add new skills
        for skill in skills:
            candidate_skill = CandidateSkill(
                candidate_id=candidate_id,
                skill=skill,
                confidence=1.0
            )
            db.add(candidate_skill)
    
    @staticmethod
    def _initialize_conversation_state(candidate_data: CandidateCreate) -> Dict[str, Any]:
        """Initialize conversation state from candidate data."""
        fields = {}
        
        # Define all candidate fields
        candidate_fields = [
            ("name", candidate_data.name),
            ("email", candidate_data.email),
            ("phone", candidate_data.phone),
            ("experience", candidate_data.years_experience),
            ("skills", candidate_data.skills),
            ("currentCompany", candidate_data.current_company),
            ("education", candidate_data.education),
            ("location", candidate_data.location),
        ]
        
        for field_key, value in candidate_fields:
            if value is not None:
                fields[field_key] = {
                    "value": value,
                    "confidence": 0.9 if field_key in ["name", "email"] else 0.7,
                    "asked": False,
                    "answered": True,  # Assume answered if provided
                    "source": "manual"
                }
            else:
                fields[field_key] = {
                    "value": None,
                    "confidence": 0.0,
                    "asked": False,
                    "answered": False,
                    "source": None
                }
        
        return {"fields": fields}
    
    @staticmethod
    def _calculate_overall_confidence(candidate_data: CandidateCreate) -> float:
        """Calculate overall confidence score for candidate."""
        # Simple calculation based on completeness
        total_fields = 8  # name, email, phone, experience, skills, company, education, location
        filled_fields = 0
        
        if candidate_data.name:
            filled_fields += 1
        if candidate_data.email:
            filled_fields += 1
        if candidate_data.phone:
            filled_fields += 1
        if candidate_data.years_experience is not None:
            filled_fields += 1
        if candidate_data.skills:
            filled_fields += 1
        if candidate_data.current_company:
            filled_fields += 1
        if candidate_data.education:
            filled_fields += 1
        if candidate_data.location:
            filled_fields += 1
        
        return (filled_fields / total_fields) * 100 if total_fields > 0 else 0
    
    @staticmethod
    def _calculate_candidate_confidence(candidate: Candidate) -> float:
        """Calculate confidence based on conversation state."""
        if not candidate.conversation_state:
            return 0.0
        
        total_confidence = 0.0
        field_count = 0
        
        for field_state in candidate.conversation_state.get("fields", {}).values():
            if isinstance(field_state, dict):
                confidence = field_state.get("confidence", 0.0)
                if confidence > 0:
                    total_confidence += confidence
                    field_count += 1
        
        return (total_confidence / field_count * 100) if field_count > 0 else 0.0
    
    @staticmethod
    def _format_candidate_response(candidate: Candidate) -> Dict[str, Any]:
        """Format candidate for API response."""
        skills = [skill.skill for skill in candidate.skills]
        
        parsed_fields = []
        for pf in candidate.parsed_fields:
            parsed_fields.append({
                "name": pf.name,
                "value": pf.value,
                "confidence": pf.confidence,
                "raw_extraction": pf.raw_extraction,
                "source": pf.source
            })
        
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
        
        return {
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