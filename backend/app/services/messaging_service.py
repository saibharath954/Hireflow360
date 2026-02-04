# backend/app/services/messaging_service.py
"""
Enhanced Messaging Service with WhatsApp simulation and AI conversations
"""

import uuid
import random
import re
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc, func
import json

from app.models.models import (
    Message, Candidate, Job, JobType, JobStatus,
    ParsedField
)
from app.schemas.schemas import (
    MessagePreview, ReplyCreate, MessageCreate,
    CandidateFieldKey, FieldState, ConversationState
)
from app.core.logging import logger
from app.services.ai_service import AIService
from app.workers.background import send_message_job, process_candidate_reply
from app.core.config import settings


class MessagingService:
    """Production-grade messaging service with WhatsApp simulation"""
    
    # WhatsApp simulation settings
    WHATSAPP_SETTINGS = {
        "min_delay_seconds": 2,
        "max_delay_seconds": 10,
        "typing_indicator_delay": 1.5,
        "max_message_length": 1000,
        "typical_response_time_minutes": (5, 120)
    }
    
    @staticmethod
    async def generate_conversational_message(
        db: Session,
        intent: str,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        pending_fields: Optional[List[CandidateFieldKey]] = None
    ) -> Tuple[Optional[MessagePreview], Optional[str]]:
        """
        Generate human-like conversational message with AI
        """
        try:
            # Get candidate with conversation state
            candidate = db.query(Candidate).options(
                joinedload(Candidate.skills),
                joinedload(Candidate.messages)
            ).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None, "Candidate not found"
            
            # Get conversation history
            conversation_history = db.query(Message).filter(
                Message.candidate_id == candidate_id
            ).order_by(Message.timestamp.desc()).limit(5).all()
            
            # Format history for AI
            history_formatted = []
            for msg in reversed(conversation_history):  # Oldest first
                history_formatted.append({
                    "direction": msg.direction,
                    "content": msg.content[:200],
                    "timestamp": msg.timestamp.isoformat()
                })
            
            # Determine pending fields
            if not pending_fields:
                pending_fields = MessagingService._get_pending_fields(
                    candidate.conversation_state
                )
            
            # Limit to 2-3 questions for natural conversation
            if len(pending_fields) > 3:
                # Prioritize important fields
                priority_order = ['location', 'notice_period', 'expected_salary', 
                                 'availability', 'portfolio_url']
                pending_fields = [
                    field for field in priority_order 
                    if field in pending_fields
                ][:3]
            
            # Prepare candidate info for AI
            candidate_info = {
                "name": candidate.name,
                "current_company": candidate.current_company,
                "skills": [skill.skill for skill in candidate.skills[:5]],
                "years_experience": candidate.years_experience,
                "status": candidate.status,
                "location": candidate.location
            }
            
            # Generate message with AI
            message_content, asked_fields, metadata = AIService.generate_conversational_message(
                intent=intent,
                candidate_info=candidate_info,
                pending_fields=pending_fields,
                conversation_history=history_formatted
            )
            
            # Ensure message length is appropriate
            if len(message_content) > MessagingService.WHATSAPP_SETTINGS["max_message_length"]:
                message_content = message_content[:MessagingService.WHATSAPP_SETTINGS["max_message_length"]] + "..."
            
            # Create message preview
            preview = MessagePreview(
                content=message_content,
                candidate_id=str(candidate_id),
                intent=intent,
                asked_fields=asked_fields,
                metadata={
                    **metadata,
                    "pending_fields": pending_fields,
                    "history_count": len(conversation_history),
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Generated conversational message for candidate {candidate_id}, "
                       f"asked fields: {asked_fields}")
            return preview, None
            
        except Exception as e:
            logger.error(f"Failed to generate conversational message: {str(e)}")
            return None, str(e)
    
    @staticmethod
    async def send_whatsapp_message(
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
        Send message with WhatsApp simulation
        """
        try:
            # Get candidate
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None, "Candidate not found"
            
            # Simulate human typing delay
            if mode == "mock" and settings.SIMULATE_HUMAN_BEHAVIOR:
                await asyncio.sleep(MessagingService.WHATSAPP_SETTINGS["typing_indicator_delay"])
            
            # Create message record
            message = Message(
                id=uuid.uuid4(),
                candidate_id=candidate_id,
                direction="outgoing",
                content=content,
                timestamp=datetime.utcnow(),
                status="sent" if mode == "mock" else "queued",
                intent=intent,
                generated_by=generated_by,
                asked_fields=asked_fields,
                metadata={
                    "mode": mode,
                    "simulated": mode == "mock",
                    "sent_at": datetime.utcnow().isoformat()
                }
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
                        "asked_fields": asked_fields,
                        "platform": "whatsapp"
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
            
            # Simulate delivery and read receipts for mock mode
            if mode == "mock" and settings.SIMULATE_HUMAN_BEHAVIOR:
                await MessagingService._simulate_message_delivery(db, message)
            
            logger.info(f"WhatsApp message sent to candidate {candidate_id} "
                       f"(mode: {mode}, length: {len(content)})")
            return message, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return None, str(e)
    
    @staticmethod
    async def _simulate_message_delivery(db: Session, message: Message):
        """Simulate WhatsApp message delivery and read receipts"""
        try:
            # Simulate delivery delay (1-3 seconds)
            await asyncio.sleep(random.uniform(1, 3))
            
            message.status = "delivered"
            message.metadata = {
                **message.metadata,
                "delivered_at": datetime.utcnow().isoformat()
            }
            
            # Simulate read receipt (50% chance, after 5-30 seconds)
            if random.random() > 0.5:
                await asyncio.sleep(random.uniform(5, 30))
                message.status = "read"
                message.metadata = {
                    **message.metadata,
                    "read_at": datetime.utcnow().isoformat()
                }
            
            db.commit()
            
        except Exception as e:
            logger.warning(f"Failed to simulate message delivery: {str(e)}")
    
    @staticmethod
    async def process_incoming_reply(
        db: Session,
        reply_data: ReplyCreate,
        organization_id: uuid.UUID,
        simulate_delay: bool = True
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Process incoming reply with AI analysis
        """
        try:
            # Get candidate with last message
            candidate = db.query(Candidate).options(
                joinedload(Candidate.messages)
            ).filter(
                Candidate.id == reply_data.candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None, "Candidate not found"
            
            # Simulate human response time
            if simulate_delay and settings.SIMULATE_HUMAN_BEHAVIOR:
                delay_minutes = random.uniform(*MessagingService.WHATSAPP_SETTINGS["typical_response_time_minutes"])
                await asyncio.sleep(delay_minutes * 60)
            
            # Get last outgoing message to know what was asked
            last_outgoing = db.query(Message).filter(
                Message.candidate_id == reply_data.candidate_id,
                Message.direction == "outgoing"
            ).order_by(desc(Message.timestamp)).first()
            
            asked_fields = last_outgoing.asked_fields if last_outgoing else []
            
            # Analyze reply with AI
            candidate_info = {
                "name": candidate.name,
                "status": candidate.status,
                "current_company": candidate.current_company
            }
            
            analysis = AIService.analyze_candidate_reply(
                reply_text=reply_data.content,
                candidate_info=candidate_info,
                asked_fields=asked_fields
            )
            
            # Create message
            message = Message(
                id=uuid.uuid4(),
                candidate_id=reply_data.candidate_id,
                direction="incoming",
                content=reply_data.content,
                timestamp=datetime.utcnow(),
                status="delivered",
                classification=analysis["classification"],
                suggested_reply=analysis["suggested_reply"],
                extracted_fields=analysis["extracted_data"],
                requires_hr_review=analysis["requires_hr_review"],
                ai_suggested_reply=analysis.get("suggested_reply"),
                hr_approved=False,
                metadata={
                    "analysis": {
                        "confidence_scores": analysis.get("confidence_scores", {}),
                        "candidate_questions": analysis.get("candidate_questions", []),
                        "extracted_count": len(analysis.get("extracted_data", {}))
                    },
                    "received_at": datetime.utcnow().isoformat()
                }
            )
            
            db.add(message)
            
            # Update candidate
            candidate.last_message_at = datetime.utcnow()
            
            # Update candidate status if no HR review required
            if not analysis["requires_hr_review"]:
                candidate.status = analysis["classification"]
            
            # Update candidate data with extracted information
            MessagingService._update_candidate_from_extracted_data(
                db, candidate, analysis["extracted_data"]
            )
            
            # Update conversation state
            MessagingService._update_conversation_state_from_reply(
                candidate, asked_fields, analysis["extracted_data"]
            )
            
            candidate.updated_at = datetime.utcnow()
            db.commit()
            
            # Trigger automated response if no HR review needed
            if not analysis["requires_hr_review"] and analysis.get("suggested_reply"):
                await asyncio.sleep(1)  # Small delay before auto-responding
                
                auto_reply = await MessagingService.send_whatsapp_message(
                    db=db,
                    candidate_id=reply_data.candidate_id,
                    content=analysis["suggested_reply"],
                    organization_id=organization_id,
                    mode="mock",
                    generated_by="ai_auto"
                )
            
            logger.info(f"Reply processed from candidate {reply_data.candidate_id}, "
                       f"classification: {analysis['classification']}, "
                       f"HR review: {analysis['requires_hr_review']}")
            return message, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process incoming reply: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def _update_candidate_from_extracted_data(
        db: Session,
        candidate: Candidate,
        extracted_data: Dict[str, Any]
    ):
        """Update candidate with extracted data from reply"""
        updates = {}
        
        # Map extracted data to candidate fields
        field_mapping = {
            'notice_period': 'notice_period',
            'expected_salary': 'expected_salary',
            'location': 'location',
            'portfolio_url': 'portfolio_url'
        }
        
        for extracted_key, candidate_key in field_mapping.items():
            if extracted_key in extracted_data:
                value = extracted_data[extracted_key]
                if value:
                    setattr(candidate, candidate_key, value)
                    
                    # Also create parsed field record
                    parsed_field = ParsedField(
                        candidate_id=candidate.id,
                        name=candidate_key,
                        value=str(value),
                        confidence=85.0,
                        raw_extraction=str(value),
                        source="reply_analysis"
                    )
                    db.add(parsed_field)
    
    @staticmethod
    def _update_conversation_state_from_reply(
        candidate: Candidate,
        asked_fields: List[str],
        extracted_data: Dict[str, Any]
    ):
        """Update conversation state based on reply"""
        if not candidate.conversation_state:
            candidate.conversation_state = {"fields": {}}
        
        # Mark asked fields as answered if data was extracted
        for field in asked_fields:
            if field in candidate.conversation_state.get("fields", {}):
                field_state = candidate.conversation_state["fields"][field]
                
                # Check if this field was answered
                field_key = MessagingService._map_to_conversation_key(field)
                if field_key in extracted_data:
                    field_state["answered"] = True
                    field_state["value"] = extracted_data[field_key]
                    field_state["confidence"] = 0.9
                    field_state["source"] = "reply"
                else:
                    # Field was asked but not answered
                    field_state["asked"] = True
                    field_state["answered"] = False
        
        # Recalculate overall confidence
        if candidate.conversation_state.get("fields"):
            filled_fields = sum(
                1 for field in candidate.conversation_state["fields"].values()
                if isinstance(field, dict) and field.get("value")
            )
            total_fields = len(candidate.conversation_state["fields"])
            candidate.overall_confidence = (filled_fields / total_fields * 100) if total_fields > 0 else 0
    
    @staticmethod
    def _map_to_conversation_key(field: str) -> str:
        """Map field name to conversation state key"""
        mapping = {
            "location": "location",
            "notice_period": "noticePeriod",
            "expected_salary": "expectedSalary",
            "portfolio_url": "portfolioUrl",
            "experience": "experience",
            "skills": "skills"
        }
        return mapping.get(field, field)
    
    @staticmethod
    def _get_pending_fields(conversation_state: Optional[Dict]) -> List[str]:
        """Get pending fields from conversation state"""
        if not conversation_state or "fields" not in conversation_state:
            return []
        
        pending = []
        
        for field_key, field_state in conversation_state["fields"].items():
            if isinstance(field_state, dict):
                asked = field_state.get("asked", False)
                answered = field_state.get("answered", False)
                value = field_state.get("value")
                
                # Field is pending if not answered or has low confidence value
                if not answered or (value is None and not asked):
                    pending.append(field_key)
        
        return pending
    
    @staticmethod
    async def handle_candidate_question(
        db: Session,
        message_id: uuid.UUID,
        organization_id: uuid.UUID,
        hr_response: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Handle candidate questions flagged for HR review
        """
        try:
            # Get the incoming message with question
            incoming_msg = db.query(Message).join(Candidate).filter(
                Message.id == message_id,
                Message.direction == "incoming",
                Message.requires_hr_review == True,
                Candidate.organization_id == organization_id
            ).first()
            
            if not incoming_msg:
                return None, "Message not found or not requiring review"
            
            candidate = incoming_msg.candidate
            
            # If HR provided response, use it
            if hr_response:
                response_content = hr_response
            else:
                # Generate AI-suggested response
                response_content = incoming_msg.ai_suggested_reply or MessagingService._generate_default_response(incoming_msg)
            
            # Mark as approved
            incoming_msg.hr_approved = True
            incoming_msg.hr_approved_at = datetime.utcnow()
            
            # Send response
            response_msg, error = await MessagingService.send_whatsapp_message(
                db=db,
                candidate_id=candidate.id,
                content=response_content,
                organization_id=organization_id,
                mode="mock",
                intent="HR response to question",
                generated_by="hr"
            )
            
            if error:
                return None, error
            
            # Update candidate
            candidate.last_message_at = datetime.utcnow()
            candidate.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"HR responded to candidate question, message {message_id}")
            return response_msg, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to handle candidate question: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def _generate_default_response(message: Message) -> str:
        """Generate default response for candidate questions"""
        question_types = {
            "salary": "Thanks for asking about compensation! The role offers a competitive package. Would you be available for a quick call to discuss details?",
            "remote": "Great question about work arrangements! We offer flexible options. Would you prefer remote, hybrid, or in-office?",
            "role": "Thanks for your interest in the role details! I'll send you the complete job description. Would you like me to schedule a call with the hiring manager?",
            "default": "Thanks for your question! Let me get you the information you need. Could we schedule a quick call to discuss further?"
        }
        
        content_lower = message.content.lower()
        
        if any(word in content_lower for word in ["salary", "compensation", "pay", "package"]):
            return question_types["salary"]
        elif any(word in content_lower for word in ["remote", "hybrid", "office", "location"]):
            return question_types["remote"]
        elif any(word in content_lower for word in ["role", "responsibilities", "job", "position"]):
            return question_types["role"]
        else:
            return question_types["default"]
    
    @staticmethod
    def get_conversation_analytics(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get analytics for a conversation
        """
        try:
            messages = db.query(Message).filter(
                Message.candidate_id == candidate_id
            ).order_by(Message.timestamp).all()
            
            if not messages:
                return {"error": "No messages found"}
            
            # Calculate metrics
            outgoing_count = sum(1 for m in messages if m.direction == "outgoing")
            incoming_count = sum(1 for m in messages if m.direction == "incoming")
            
            response_times = []
            last_outgoing_time = None
            
            for msg in messages:
                if msg.direction == "outgoing":
                    last_outgoing_time = msg.timestamp
                elif msg.direction == "incoming" and last_outgoing_time:
                    response_time = (msg.timestamp - last_outgoing_time).total_seconds() / 60
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else None
            
            # Classification distribution
            classifications = {}
            for msg in messages:
                if msg.classification:
                    classifications[msg.classification] = classifications.get(msg.classification, 0) + 1
            
            # Extract information gathered
            extracted_fields = []
            for msg in messages:
                if msg.extracted_fields:
                    if isinstance(msg.extracted_fields, dict):
                        extracted_fields.extend(msg.extracted_fields.keys())
                    elif isinstance(msg.extracted_fields, list):
                        for field in msg.extracted_fields:
                            if isinstance(field, dict) and 'name' in field:
                                extracted_fields.append(field['name'])
            
            unique_extracted = list(set(extracted_fields))
            
            return {
                "total_messages": len(messages),
                "outgoing_count": outgoing_count,
                "incoming_count": incoming_count,
                "response_rate": (incoming_count / outgoing_count * 100) if outgoing_count > 0 else 0,
                "avg_response_time_minutes": round(avg_response_time, 2) if avg_response_time else None,
                "classifications": classifications,
                "extracted_fields": unique_extracted,
                "hr_review_required": sum(1 for m in messages if m.requires_hr_review),
                "hr_approved": sum(1 for m in messages if m.hr_approved),
                "conversation_duration_days": (
                    (messages[-1].timestamp - messages[0].timestamp).total_seconds() / 86400
                ) if len(messages) > 1 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation analytics: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def schedule_follow_up(
        db: Session,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        delay_hours: int = 24,
        follow_up_type: str = "reminder"
    ) -> Tuple[Optional[Job], Optional[str]]:
        """
        Schedule a follow-up message
        """
        try:
            candidate = db.query(Candidate).filter(
                Candidate.id == candidate_id,
                Candidate.organization_id == organization_id
            ).first()
            
            if not candidate:
                return None, "Candidate not found"
            
            # Calculate follow-up time
            follow_up_time = datetime.utcnow() + timedelta(hours=delay_hours)
            
            # Create follow-up job
            job = Job(
                id=uuid.uuid4(),
                type=JobType.FOLLOW_UP,
                status=JobStatus.QUEUED,
                candidate_id=candidate_id,
                metadata={
                    "follow_up_type": follow_up_type,
                    "scheduled_for": follow_up_time.isoformat(),
                    "delay_hours": delay_hours,
                    "candidate_status": candidate.status
                },
                scheduled_for=follow_up_time,
                created_at=datetime.utcnow()
            )
            
            db.add(job)
            db.commit()
            
            logger.info(f"Scheduled follow-up for candidate {candidate_id} "
                       f"at {follow_up_time} (type: {follow_up_type})")
            return job, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to schedule follow-up: {str(e)}")
            return None, str(e)