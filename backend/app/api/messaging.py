# backend/app/api/messaging.py
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from typing import List, Optional
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_recruiter_user
from app.schemas.schemas import (
    ApiResponse, Message, MessagePreview, MessageCreate,
    ReplyCreate, CandidateFieldKey, SendMessageRequest
)
from app.models.models import (
    User, Candidate, Message as MessageModel,
    Job, JobType, JobStatus
)
from app.services.messaging_service import MessagingService

router = APIRouter()

@router.get("/conversation", response_model=ApiResponse)
async def get_conversation(
    candidate_id: str = Query(...),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.organization_id == current_user.organization_id
    ).first()

    if not candidate:
        return ApiResponse(success=False, error="Candidate not found")

    messages = (
        db.query(MessageModel)
        .filter(MessageModel.candidate_id == candidate_id)
        .order_by(MessageModel.timestamp.desc())
        .limit(limit)
        .all()
    )

    return ApiResponse(
        success=True,
        data=[Message.from_orm(m) for m in messages]
    )


@router.post("/generate-preview", response_model=ApiResponse)
async def generate_message_preview(
    intent: str,
    candidate_id: str,
    pending_fields: Optional[List[CandidateFieldKey]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Generate message preview from intent"""
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.organization_id == current_user.organization_id
    ).first()
    
    if not candidate:
        return ApiResponse(success=False, error="Candidate not found")
    
    # Get conversation state
    conversation_state = candidate.conversation_state or {}
    
    # Determine which fields to ask
    fields_to_ask = pending_fields or []
    
    # Mock LLM generation (replace with real LLM in production)
    field_questions = {
        "name": "Could you confirm your full name?",
        "email": "What's the best email to reach you?",
        "phone": "What's your phone number for scheduling calls?",
        "experience": "How many years of experience do you have?",
        "skills": "What are your key technical skills?",
        "currentCompany": "Where are you currently working?",
        "education": "Could you share your educational background?",
        "location": "What's your current location?",
    }
    
    questions = [field_questions[f] for f in fields_to_ask if f in field_questions]
    
    # Build message
    content = f"Hi {candidate.name.split(' ')[0]}! {intent}"
    
    if candidate.current_company:
        content += f" I noticed your experience at {candidate.current_company}"
        if candidate.skills:
            skills_list = [skill.skill for skill in candidate.skills[:2]]
            content += f" with {', '.join(skills_list)} - very impressive!"
    
    if questions:
        content += f" I have a few quick questions: {' '.join(questions)}"
    
    content += " Looking forward to hearing from you!"
    
    return ApiResponse(
        success=True,
        data=MessagePreview(
            content=content,
            candidate_id=candidate_id,
            intent=intent,
            asked_fields=fields_to_ask,
            metadata={
                "tokensUsed": 150,
                "modelVersion": "mock-llm-v1"
            }
        )
    )

@router.post("/send", response_model=ApiResponse)
async def send_message(
    candidate_id: str = Query(...),
    mode: str = Query("mock"),
    payload: SendMessageRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Send message to candidate"""
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.organization_id == current_user.organization_id
    ).first()
    
    if not candidate:
        return ApiResponse(success=False, error="Candidate not found")
    
    # Create message
    message = MessageModel(
        id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        direction="outgoing",
        content=payload.content,
        timestamp=datetime.utcnow(),
        status="sent" if mode == "mock" else "pending",
        generated_by="ai",
        asked_fields=payload.asked_fields
    )
    
    db.add(message)
    
    # Update candidate
    candidate.last_message_at = datetime.utcnow()
    candidate.status = "contacted"
    candidate.updated_at = datetime.utcnow()
    
    # Update conversation state if asked_fields provided
    if payload.asked_fields and candidate.conversation_state:
        for field in payload.asked_fields:
            if field in candidate.conversation_state.get("fields", {}):
                candidate.conversation_state["fields"][field]["asked"] = True
    
    # Create send job for automation mode
    if mode == "automation":
        job = Job(
            id=str(uuid.uuid4()),
            type=JobType.SEND_MESSAGE,
            status=JobStatus.QUEUED,
            candidate_id=candidate_id,
            message_id=message.id,
            job_metadata={
                "mode": mode,
                "content": payload.content[:100]  # Store first 100 chars
            },
            created_at=datetime.utcnow()
        )
        db.add(job)
    
    db.commit()
    db.refresh(message)
    
    return ApiResponse(
        success=True,
        data=Message.from_orm(message)
    )

@router.post("/receive-reply", response_model=ApiResponse)
async def receive_reply(
    reply: ReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Receive and process incoming reply"""
    candidate = db.query(Candidate).filter(
        Candidate.id == reply.candidate_id,
        Candidate.organization_id == current_user.organization_id
    ).first()
    
    if not candidate:
        return ApiResponse(success=False, error="Candidate not found")
    
    # Mock classification
    lower_text = reply.content.lower()
    
    classification = "interested"
    suggested_reply = "Thank you for your interest! "
    requires_hr_review = False
    ai_suggested_reply = None
    
    # Enhanced question detection
    question_indicators = ["?", "what", "when", "how", "salary", "compensation", 
                          "package", "pay", "benefits", "remote", "hybrid", 
                          "location", "why", "who", "which"]
    has_question = any(indicator in lower_text for indicator in question_indicators)
    
    if any(phrase in lower_text for phrase in ["not interested", "no thanks", "pass", "decline"]):
        classification = "not_interested"
        suggested_reply = "Thank you for your time. We'll keep your profile on file."
    elif has_question:
        classification = "question"
        requires_hr_review = True
        
        if any(word in lower_text for word in ["salary", "compensation", "pay", "package"]):
            ai_suggested_reply = "Great question! The compensation range is competitive. Would you like to discuss further?"
        elif any(word in lower_text for word in ["remote", "hybrid", "office"]):
            ai_suggested_reply = "This role offers flexible work arrangements. Happy to discuss details."
        else:
            ai_suggested_reply = "Thanks for your question! I'd be happy to provide more details."
        
        suggested_reply = ai_suggested_reply
    elif any(word in lower_text for word in ["yes", "interested", "available", "sure"]):
        classification = "interested"
        suggested_reply = "Fantastic! Let's schedule a call to discuss further."
    elif any(word in lower_text for word in ["clarif", "more info"]):
        classification = "needs_clarification"
        suggested_reply = "Of course! Let me provide more details: "
    
    # Create message
    message = MessageModel(
        id=str(uuid.uuid4()),
        candidate_id=reply.candidate_id,
        direction="incoming",
        content=reply.content,
        timestamp=datetime.utcnow(),
        status="delivered",
        classification=classification,
        suggested_reply=suggested_reply,
        requires_hr_review=requires_hr_review,
        ai_suggested_reply=ai_suggested_reply,
        hr_approved=False
    )
    
    db.add(message)
    
    # Update candidate status if no HR review required
    if not requires_hr_review:
        candidate.status = classification
    
    candidate.last_message_at = datetime.utcnow()
    candidate.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    
    return ApiResponse(
        success=True,
        data=Message.from_orm(message)
    )

@router.post("/{message_id}/approve", response_model=ApiResponse)
async def approve_and_send(
    message_id: str,
    content: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Approve HR-reviewed message and send reply"""
    # Find incoming message
    incoming_msg = db.query(MessageModel).filter(
        MessageModel.id == message_id,
        MessageModel.direction == "incoming",
        MessageModel.requires_hr_review == True,
        MessageModel.candidate.has(organization_id=current_user.organization_id)
    ).first()
    
    if not incoming_msg:
        return ApiResponse(success=False, error="Message not found or not requiring approval")
    
    # Mark as approved
    incoming_msg.hr_approved = True
    incoming_msg.hr_approved_at = datetime.utcnow()
    
    # Create outgoing reply
    outgoing_msg = MessageModel(
        id=str(uuid.uuid4()),
        candidate_id=incoming_msg.candidate_id,
        direction="outgoing",
        content=content,
        timestamp=datetime.utcnow(),
        status="sent",
        generated_by="ai"
    )
    
    db.add(outgoing_msg)
    
    # Update candidate
    candidate = incoming_msg.candidate
    candidate.last_message_at = datetime.utcnow()
    candidate.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(outgoing_msg)
    
    return ApiResponse(
        success=True,
        data=Message.from_orm(outgoing_msg)
    )