# backend/app/services/messaging_service.py
"""
Messaging Service
Handles all business logic related to messaging and conversation management.
"""

import uuid
import random
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc

from app.models.models import (
    Message, Candidate, Job, JobType, JobStatus
)
from app.schemas.schemas import (
    MessagePreview, ReplyCreate, MessageCreate,
    CandidateFieldKey, FieldState
)
from app.core.logging import logger
from app.workers.background import send_message_job


class MessagingService:
    """Service for messaging-related operations"""
    
    # Field questions mapping
    FIELD_QUESTIONS = {
        "name": "Could you confirm your full name?",
        "email": "What's the best email to reach you?",
        "phone": "What's your phone number for scheduling calls?",
        "experience": "How many years of experience do you have?",
        "skills": "What are your key technical skills?",
        "currentCompany": "Where are you currently working?",
        "education": "Could you share your educational background?",
        "location": "What's your current location?",
    }
    
    @staticmethod
    def generate_message_preview(
        db: Session,
        intent: str,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        pending_fields: Optional[List[CandidateFieldKey]] = None
    ) -> Tuple[Optional[MessagePreview], Optional[str]]:
        """
        Generate a preview message from intent.
        
        Args:
            db: Database session
            intent: HR intent/prompt
            candidate_id: Candidate ID
            organization_id: Organization ID
            pending_fields: Optional list of fields to ask about
            
        Returns:
            Tuple of (message_preview, error_message)
        """
        try:
            # Get candidate with conversation state
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None, "Candidate not found"
            
            # Get conversation state
            conversation_state = candidate.conversation_state or {"fields": {}}
            
            # Determine which fields to ask
            if pending_fields:
                fields_to_ask = pending_fields
            else:
                # Auto-determine pending fields
                fields_to_ask = MessagingService._get_pending_fields_from_state(conversation_state)
            
            # Build message content
            content = MessagingService._build_message_content(
                candidate=candidate,
                intent=intent,
                fields_to_ask=fields_to_ask
            )
            
            # Create message preview
            preview = MessagePreview(
                content=content,
                candidate_id=str(candidate_id),
                intent=intent,
                asked_fields=fields_to_ask,
                metadata={
                    "tokensUsed": len(content.split()),  # Mock token count
                    "modelVersion": "mock-llm-v1",
                    "generatedAt": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Generated message preview for candidate {candidate_id}")
            return preview, None
            
        except Exception as e:
            logger.error(f"Failed to generate message preview: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def send_message(
        db: Session,
        candidate_id: uuid.UUID,
        content: str,
        organization_id: uuid.UUID,
        mode: str = "mock",
        asked_fields: Optional[List[str]] = None,
        intent: Optional[str] = None,
        generated_by: str = "ai"
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Send message to candidate.
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            content: Message content
            organization_id: Organization ID
            mode: "mock" or "automation"
            asked_fields: Fields asked in this message
            intent: HR intent
            generated_by: "ai" or "manual"
            
        Returns:
            Tuple of (message, error_message)
        """
        try:
            # Get candidate
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None, "Candidate not found"
            
            # Create message record
            message = Message(
                id=uuid.uuid4(),
                candidate_id=candidate_id,
                direction="outgoing",
                content=content,
                timestamp=datetime.utcnow(),
                status="sent" if mode == "mock" else "pending",
                intent=intent,
                generated_by=generated_by,
                asked_fields=asked_fields
            )
            
            db.add(message)
            
            # Update candidate
            candidate.last_message_at = datetime.utcnow()
            candidate.status = "contacted"
            candidate.updated_at = datetime.utcnow()
            
            # Update conversation state for asked fields
            if asked_fields and candidate.conversation_state:
                for field in asked_fields:
                    if field in candidate.conversation_state.get("fields", {}):
                        candidate.conversation_state["fields"][field]["asked"] = True
            
            # Create send job for automation mode
            if mode == "automation":
                job = Job(
                    id=uuid.uuid4(),
                    type=JobType.SEND_MESSAGE,
                    status=JobStatus.QUEUED,
                    candidate_id=candidate_id,
                    message_id=message.id,
                    metadata={
                        "mode": mode,
                        "content_preview": content[:100],
                        "asked_fields": asked_fields
                    },
                    created_at=datetime.utcnow()
                )
                db.add(job)
                
                # Trigger background job
                send_message_job.delay(
                    message_id=str(message.id),
                    job_id=str(job.id)
                )
            
            db.commit()
            db.refresh(message)
            
            logger.info(f"Message sent to candidate {candidate_id} (mode: {mode})")
            return message, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to send message: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def receive_reply(
        db: Session,
        reply_data: ReplyCreate,
        organization_id: uuid.UUID
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Process incoming reply from candidate.
        
        Args:
            db: Database session
            reply_data: Reply data
            organization_id: Organization ID
            
        Returns:
            Tuple of (message, error_message)
        """
        try:
            # Get candidate
            candidate = db.query(Candidate).filter(
                Candidate.id == reply_data.candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None, "Candidate not found"
            
            # Classify reply
            classification_result = MessagingService._classify_reply(reply_data.content)
            
            # Extract structured data from reply
            extracted_data = MessagingService._extract_data_from_reply(reply_data.content)
            
            # Create message
            message = Message(
                id=uuid.uuid4(),
                candidate_id=reply_data.candidate_id,
                direction="incoming",
                content=reply_data.content,
                timestamp=datetime.utcnow(),
                status="delivered",
                classification=classification_result["classification"],
                suggested_reply=classification_result["suggested_reply"],
                extracted_fields=extracted_data,
                requires_hr_review=classification_result["requires_hr_review"],
                ai_suggested_reply=classification_result["ai_suggested_reply"],
                hr_approved=False
            )
            
            db.add(message)
            
            # Update candidate
            candidate.last_message_at = datetime.utcnow()
            
            # Update candidate status if no HR review required
            if not classification_result["requires_hr_review"]:
                candidate.status = classification_result["classification"]
            
            # Update conversation state with extracted data
            if extracted_data and candidate.conversation_state:
                MessagingService._update_conversation_state_from_reply(
                    candidate, extracted_data, classification_result["classification"]
                )
            
            candidate.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(message)
            
            logger.info(f"Reply received from candidate {reply_data.candidate_id}, classification: {classification_result['classification']}")
            return message, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process reply: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def approve_and_send_reply(
        db: Session,
        message_id: uuid.UUID,
        approved_content: str,
        organization_id: uuid.UUID
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Approve HR-reviewed message and send reply.
        
        Args:
            db: Database session
            message_id: Original message ID
            approved_content: Approved reply content
            organization_id: Organization ID
            
        Returns:
            Tuple of (outgoing_message, error_message)
        """
        try:
            # Get incoming message
            incoming_msg = db.query(Message).join(Candidate).filter(
                Message.id == message_id,
                Message.direction == "incoming",
                Message.requires_hr_review == True,
                Candidate.organization_id == organization_id
            ).first()
            
            if not incoming_msg:
                return None, "Message not found or not requiring approval"
            
            # Mark as approved
            incoming_msg.hr_approved = True
            incoming_msg.hr_approved_at = datetime.utcnow()
            
            # Create outgoing reply
            outgoing_msg = Message(
                id=uuid.uuid4(),
                candidate_id=incoming_msg.candidate_id,
                direction="outgoing",
                content=approved_content,
                timestamp=datetime.utcnow(),
                status="sent",
                generated_by="ai",
                intent="HR-approved reply"
            )
            
            db.add(outgoing_msg)
            
            # Update candidate
            candidate = incoming_msg.candidate
            candidate.last_message_at = datetime.utcnow()
            candidate.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(outgoing_msg)
            
            logger.info(f"HR-approved reply sent for message {message_id}")
            return outgoing_msg, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to approve and send reply: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def get_conversation_history(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int = 50
    ) -> List[Message]:
        """
        Get conversation history for a candidate.
        
        Args:
            db: Database session
            candidate_id: Candidate ID
            organization_id: Organization ID
            limit: Maximum number of messages
            
        Returns:
            List of messages
        """
        try:
            messages = db.query(Message).join(Candidate).filter(
                Message.candidate_id == candidate_id,
                Candidate.organization_id == organization_id
            ).order_by(
                desc(Message.timestamp)
            ).limit(limit).all()
            
            return messages
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            raise
    
    @staticmethod
    def get_messages_requiring_review(
        db: Session,
        organization_id: uuid.UUID,
        limit: int = 20
    ) -> List[Message]:
        """
        Get messages requiring HR review.
        
        Args:
            db: Database session
            organization_id: Organization ID
            limit: Maximum number of messages
            
        Returns:
            List of messages
        """
        try:
            messages = db.query(Message).join(Candidate).filter(
                Message.direction == "incoming",
                Message.requires_hr_review == True,
                Message.hr_approved == False,
                Candidate.organization_id == organization_id
            ).order_by(
                desc(Message.timestamp)
            ).limit(limit).all()
            
            return messages
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get messages requiring review: {str(e)}")
            raise
    
    # Helper Methods
    
    @staticmethod
    def _get_pending_fields_from_state(conversation_state: Dict[str, Any]) -> List[str]:
        """Get list of pending fields from conversation state."""
        pending_fields = []
        
        for field_key, field_data in conversation_state.get("fields", {}).items():
            if isinstance(field_data, dict):
                asked = field_data.get("asked", False)
                answered = field_data.get("answered", False)
                value = field_data.get("value")
                
                # Field is pending if not answered or has no value
                if not answered or value is None:
                    pending_fields.append(field_key)
        
        return pending_fields
    
    @staticmethod
    def _build_message_content(
        candidate: Candidate,
        intent: str,
        fields_to_ask: List[str]
    ) -> str:
        """Build personalized message content."""
        # Start with greeting
        first_name = candidate.name.split()[0] if candidate.name else "there"
        content = f"Hi {first_name}! {intent}\n\n"
        
        # Add personalization based on candidate data
        personalization = []
        
        if candidate.current_company:
            personalization.append(f"I noticed your experience at {candidate.current_company}")
        
        if candidate.skills:
            skill_names = [skill.skill for skill in candidate.skills[:3]]
            if skill_names:
                personalization.append(f"your skills in {', '.join(skill_names)}")
        
        if personalization:
            content += f"Based on {' and '.join(personalization)}, I think you'd be a great fit!\n\n"
        
        # Add questions for pending fields
        if fields_to_ask:
            content += "I have a few questions to better understand your profile:\n"
            for field in fields_to_ask:
                if field in MessagingService.FIELD_QUESTIONS:
                    content += f"• {MessagingService.FIELD_QUESTIONS[field]}\n"
        
        # Add closing
        content += "\nLooking forward to hearing from you!"
        
        return content
    
    @staticmethod
    def _classify_reply(content: str) -> Dict[str, Any]:
        """Classify candidate reply."""
        lower_content = content.lower()
        
        # Default classification
        result = {
            "classification": "interested",
            "suggested_reply": "Thank you for your interest! Let's schedule a call to discuss further.",
            "requires_hr_review": False,
            "ai_suggested_reply": None
        }
        
        # Question detection keywords
        question_keywords = [
            "?", "what", "when", "how", "why", "who", "which",
            "salary", "compensation", "package", "pay", "benefits",
            "remote", "hybrid", "office", "location", "relocation",
            "team", "project", "role", "responsibilities", "hours",
            "vacation", "pto", "insurance", "401k", "equity"
        ]
        
        # Check for not interested
        not_interested_keywords = [
            "not interested", "no thanks", "pass", "decline",
            "not looking", "not available", "not right now"
        ]
        
        # Check for clarification needed
        clarification_keywords = [
            "clarif", "more info", "more details", "explain",
            "could you tell", "can you share", "what about"
        ]
        
        # Check for positive response
        positive_keywords = [
            "yes", "interested", "available", "sure", "definitely",
            "absolutely", "would love", "sounds good", "let's do it"
        ]
        
        # Classification logic
        if any(keyword in lower_content for keyword in not_interested_keywords):
            result["classification"] = "not_interested"
            result["suggested_reply"] = "Thank you for your time. We'll keep your profile on file for future opportunities."
        
        elif any(keyword in lower_content for keyword in question_keywords):
            result["classification"] = "question"
            result["requires_hr_review"] = True
            
            # Generate AI suggested reply based on question type
            if any(word in lower_content for word in ["salary", "compensation", "pay", "package"]):
                result["ai_suggested_reply"] = (
                    "Great question about compensation! The role offers a competitive package including "
                    "base salary, bonus, and benefits. The exact range depends on experience but starts "
                    "at $X for this level. Would you like to discuss specifics on a call?"
                )
            elif any(word in lower_content for word in ["remote", "hybrid", "office", "location"]):
                result["ai_suggested_reply"] = (
                    "Thanks for asking about work arrangements! We offer flexible options including "
                    "remote, hybrid, or in-office based on your preference. Our team is distributed "
                    "across multiple time zones. Would you like more details about our work policy?"
                )
            elif any(word in lower_content for word in ["team", "project", "role"]):
                result["ai_suggested_reply"] = (
                    "Excellent question! You'd be joining our [Team Name] team working on [Project Name]. "
                    "The role involves [brief description]. Our team culture emphasizes collaboration "
                    "and continuous learning. Would you like to schedule a call with the hiring manager?"
                )
            else:
                result["ai_suggested_reply"] = (
                    "Thanks for your question! I'd be happy to provide more details. "
                    "[HR: Please customize this response based on the specific question asked.] "
                    "Would you be available for a quick call to discuss this further?"
                )
            
            result["suggested_reply"] = result["ai_suggested_reply"]
        
        elif any(keyword in lower_content for keyword in clarification_keywords):
            result["classification"] = "needs_clarification"
            result["suggested_reply"] = (
                "Of course! Let me provide more details about the role and our company. "
                "The position involves [brief description]. Our company focuses on [company focus]. "
                "Is there anything specific you'd like me to clarify further?"
            )
        
        elif any(keyword in lower_content for keyword in positive_keywords):
            result["classification"] = "interested"
            result["suggested_reply"] = (
                "Fantastic! Let's schedule a call to discuss this further. "
                "Are you available any time next week for a 30-minute chat?"
            )
        
        return result
    
    @staticmethod
    def _extract_data_from_reply(content: str) -> List[Dict[str, Any]]:
        """Extract structured data from reply."""
        extracted_fields = []
        lower_content = content.lower()
        
        # Extract notice period pattern
        notice_patterns = [
            r"(\d+)\s*(week|month|day)s?\s*notice",
            r"notice\s*(?:period)?\s*(?:of)?\s*(\d+)\s*(week|month|day)s?",
            r"available\s*(?:in)?\s*(\d+)\s*(week|month|day)s?"
        ]
        
        for pattern in notice_patterns:
            match = re.search(pattern, lower_content)
            if match:
                value = f"{match.group(1)} {match.group(2)}s"
                extracted_fields.append({
                    "name": "notice_period",
                    "value": value,
                    "confidence": 85.0,
                    "raw_extraction": match.group(0),
                    "source": "reply"
                })
                break
        
        # Extract salary expectation
        salary_patterns = [
            r"\$(\d{2,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K)?",
            r"(\d{2,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K)\s*(?:salary|base)",
            r"expect(?:ing)?\s*(?:salary)?\s*(?:of)?\s*\$?(\d{2,3}(?:,\d{3})*(?:\.\d{2})?)"
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, content)  # Use original for $ sign
            if match:
                value = f"${match.group(1)}"
                extracted_fields.append({
                    "name": "expected_salary",
                    "value": value,
                    "confidence": 80.0,
                    "raw_extraction": match.group(0),
                    "source": "reply"
                })
                break
        
        # Extract location
        location_keywords = ["based in", "located in", "from", "in", "near"]
        locations = [
            "san francisco", "new york", "remote", "austin", "seattle",
            "boston", "chicago", "los angeles", "london", "toronto"
        ]
        
        for location in locations:
            if location in lower_content:
                extracted_fields.append({
                    "name": "location",
                    "value": location.title(),
                    "confidence": 90.0,
                    "raw_extraction": location,
                    "source": "reply"
                })
                break
        
        # Extract portfolio/links
        url_pattern = r"(https?://[^\s]+|www\.[^\s]+)"
        urls = re.findall(url_pattern, content)
        for url in urls[:3]:  # Limit to first 3 URLs
            if any(domain in url.lower() for domain in ["github", "linkedin", "portfolio", "behance"]):
                extracted_fields.append({
                    "name": "portfolio_url",
                    "value": url if url.startswith("http") else f"https://{url}",
                    "confidence": 95.0,
                    "raw_extraction": url,
                    "source": "reply"
                })
                break
        
        return extracted_fields
    
    @staticmethod
    def _update_conversation_state_from_reply(
        candidate: Candidate,
        extracted_fields: List[Dict[str, Any]],
        classification: str
    ):
        """Update conversation state with data extracted from reply."""
        if not candidate.conversation_state:
            candidate.conversation_state = {"fields": {}}
        
        for field_data in extracted_fields:
            field_name = field_data["name"]
            
            # Map field names to conversation state keys
            field_mapping = {
                "notice_period": "noticePeriod",
                "expected_salary": "expectedSalary",
                "location": "location",
                "portfolio_url": "portfolioUrl"
            }
            
            state_key = field_mapping.get(field_name)
            if state_key:
                candidate.conversation_state["fields"][state_key] = {
                    "value": field_data["value"],
                    "confidence": field_data["confidence"],
                    "asked": True,
                    "answered": True,
                    "source": "reply"
                }
        
        # Update overall confidence
        if candidate.conversation_state.get("fields"):
            filled_fields = sum(
                1 for field in candidate.conversation_state["fields"].values()
                if isinstance(field, dict) and field.get("value")
            )
            total_fields = len(candidate.conversation_state["fields"])
            candidate.overall_confidence = (filled_fields / total_fields * 100) if total_fields > 0 else 0