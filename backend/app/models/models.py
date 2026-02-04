# backend/app/models/models.py
import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, JSON, Text, Enum as SQLEnum,
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base

# ==========================================
# Enums
# ==========================================

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

# ==========================================
# Core Models
# ==========================================

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    logo = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    # Added cascade to prevent orphaned users/candidates if org is deleted
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    role = Column(SQLEnum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.RECRUITER)
    avatar_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    candidates = relationship("Candidate", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")

# ==========================================
# Security & Logging
# ==========================================

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    success = Column(Boolean, nullable=False, default=False)
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")

# ==========================================
# Candidate & Recruiting
# ==========================================

class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_candidate_org_email"),
        Index("ix_candidate_org_owner", "organization_id", "owner_id"),
    )

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
    status = Column(SQLEnum(CandidateStatus, name="candidate_status_enum"), default=CandidateStatus.NEW, nullable=False)
    overall_confidence = Column(Float, default=0.0, nullable=False)
    
    # Conversation state as JSON
    conversation_state = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
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
    __table_args__ = (
        UniqueConstraint("candidate_id", "skill", name="uq_candidate_skill"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    skill = Column(String, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    candidate = relationship("Candidate", back_populates="skills")

class ParsedField(Base):
    __tablename__ = "parsed_fields"
    __table_args__ = (
        Index("ix_parsed_field_candidate_name", "candidate_id", "name"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    name = Column(String, nullable=False)  # matches frontend ParsedFieldName
    value = Column(String, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    raw_extraction = Column(Text, nullable=True)
    source = Column(String, nullable=True)  # resume, reply, manual
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    candidate = relationship("Candidate", back_populates="parsed_fields")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, docx, image-pdf
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    parsed_at = Column(DateTime(timezone=True), nullable=True)
    parse_job_id = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    
    candidate = relationship("Candidate", back_populates="resumes")

# ==========================================
# Messaging & Jobs
# ==========================================

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    direction = Column(String, nullable=False)  # incoming, outgoing
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(SQLEnum(MessageStatus, name="message_status_enum"), default=MessageStatus.PENDING, nullable=False)
    
    # For outgoing messages
    intent = Column(String, nullable=True)
    generated_by = Column(String, nullable=True)  # ai, manual
    asked_fields = Column(JSON, nullable=True)  # List of field keys
    
    # For incoming messages
    classification = Column(SQLEnum(ReplyClassification, name="reply_classification_enum"), nullable=True)
    suggested_reply = Column(Text, nullable=True)
    extracted_fields = Column(JSON, nullable=True)
    
    # HR Review fields
    requires_hr_review = Column(Boolean, default=False, nullable=False)
    ai_suggested_reply = Column(Text, nullable=True)
    hr_approved = Column(Boolean, default=False, nullable=False)
    hr_approved_at = Column(DateTime(timezone=True), nullable=True)
    
    candidate = relationship("Candidate", back_populates="messages")

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_job_status_type", "status", "type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    type = Column(SQLEnum(JobType, name="job_type_enum"), nullable=False)
    status = Column(
        SQLEnum(JobStatus, name="job_status_enum"),
        default=JobStatus.QUEUED,
        nullable=False,
    )

    progress = Column(Integer)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    locked_at = Column(DateTime(timezone=True))
    locked_by = Column(String)

    error = Column(Text)
    job_metadata = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"))
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))

    candidate = relationship("Candidate")