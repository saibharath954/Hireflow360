# backend/app/models/models.py
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, JSON, Text, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

# Enums matching frontend
import enum

class UserRole(str, enum.Enum):
    RECRUITER = "RECRUITER"
    ADMIN = "ADMIN"

class MessageStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"

class CandidateStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    NEEDS_CLARIFICATION = "needs_clarification"

class ReplyClassification(str, enum.Enum):
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    NEEDS_CLARIFICATION = "needs_clarification"
    QUESTION = "question"

class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobType(str, enum.Enum):
    PARSE_RESUME = "parse_resume"
    SEND_MESSAGE = "send_message"
    REPROCESS_RESUME = "reprocess_resume"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.RECRUITER)
    avatar_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    organization = relationship("Organization", back_populates="users")
    candidates = relationship("Candidate", back_populates="owner")

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    logo = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    users = relationship("User", back_populates="organization")
    candidates = relationship("Candidate", back_populates="organization")

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Parsed fields
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    years_experience = Column(Integer, nullable=True)
    current_company = Column(String, nullable=True)
    education = Column(String, nullable=True)
    location = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    notice_period = Column(String, nullable=True)
    expected_salary = Column(String, nullable=True)
    
    # Metadata
    status = Column(SQLEnum(CandidateStatus), default=CandidateStatus.NEW)
    overall_confidence = Column(Float, default=0.0)
    
    # Conversation state as JSON
    conversation_state = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="candidates")
    owner = relationship("User", back_populates="candidates")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="candidate", cascade="all, delete-orphan")
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    parsed_fields = relationship("ParsedField", back_populates="candidate", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="candidate")

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    skill = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    candidate = relationship("Candidate", back_populates="skills")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, docx, image-pdf
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    parsed_at = Column(DateTime(timezone=True), nullable=True)
    parse_job_id = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    
    candidate = relationship("Candidate", back_populates="resumes")

class ParsedField(Base):
    __tablename__ = "parsed_fields"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    name = Column(String, nullable=False)  # matches frontend ParsedFieldName
    value = Column(String, nullable=True)
    confidence = Column(Float, nullable=False)
    raw_extraction = Column(Text, nullable=True)
    source = Column(String, nullable=True)  # resume, reply, manual
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    candidate = relationship("Candidate", back_populates="parsed_fields")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    direction = Column(String, nullable=False)  # incoming, outgoing
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.PENDING)
    
    # For outgoing messages
    intent = Column(String, nullable=True)
    generated_by = Column(String, nullable=True)  # ai, manual
    asked_fields = Column(JSON, nullable=True)  # List of field keys
    
    # For incoming messages
    classification = Column(SQLEnum(ReplyClassification), nullable=True)
    suggested_reply = Column(Text, nullable=True)
    extracted_fields = Column(JSON, nullable=True)
    
    # HR Review fields
    requires_hr_review = Column(Boolean, default=False)
    ai_suggested_reply = Column(Text, nullable=True)
    hr_approved = Column(Boolean, default=False)
    hr_approved_at = Column(DateTime(timezone=True), nullable=True)
    
    candidate = relationship("Candidate", back_populates="messages")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED)
    progress = Column(Integer, nullable=True)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    job_metadata = Column(JSON, nullable=True)
    
    # References
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    
    candidate = relationship("Candidate", back_populates="jobs")