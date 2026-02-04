# backend/app/models/models.py
"""
Enhanced database models with relationships and indexes
"""

import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Text, JSON, ForeignKey, Index, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY as PG_ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from pydantic import BaseModel, Field

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

class Base(DeclarativeBase):
    """Base class for all models"""
    pass

class Organization(Base):
    """Organization model"""
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="organization", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="organization", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_organizations_domain', 'domain'),
        Index('idx_organizations_created', 'created_at'),
    )

class User(Base):
    """User model with roles and permissions"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="RECRUITER")  # ADMIN, RECRUITER, VIEWER
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    candidates = relationship("Candidate", back_populates="owner", foreign_keys="Candidate.owner_id")
    assigned_jobs = relationship("Job", back_populates="assigned_to", foreign_keys="Job.assigned_to_id")
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_users_organization', 'organization_id'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
        UniqueConstraint('email', 'organization_id', name='uq_user_email_org'),
    )

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

class WorkExperience(Base):
    """Full employment history for a candidate"""
    __tablename__ = "work_experience"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    
    # Dates
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False)
    
    description = Column(Text, nullable=True)
    
    # Relationship
    candidate = relationship("Candidate", back_populates="work_experiences")

class Candidate(Base):
    """Candidate model with comprehensive fields"""
    __tablename__ = "candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Personal Information
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True, index=True)
    
    # Professional Information
    years_experience = Column(Integer, nullable=True)
    current_company = Column(String(255), nullable=True, index=True)
    current_title = Column(String(255), nullable=True)
    
    # Education
    education = Column(Text, nullable=True)
    degree = Column(String(100), nullable=True)
    university = Column(String(255), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    
    # Location
    location = Column(String(255), nullable=True, index=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Preferences
    notice_period = Column(String(50), nullable=True)
    expected_salary = Column(String(100), nullable=True)
    salary_currency = Column(String(10), default="USD")
    preferred_locations = Column(JSON, default=list)
    remote_preference = Column(String(20), nullable=True)  # remote, hybrid, office
    
    # Portfolio
    portfolio_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    
    # Status & Metadata
    status = Column(String(50), default="new", index=True)  # new, contacted, interested, not_interested, needs_clarification, scheduled, hired
    source = Column(String(100), nullable=True)  # resume_upload, manual_entry, referral, etc.
    overall_confidence = Column(Float, default=0.0, index=True)
    conversation_state = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    candidate_metadata = Column(JSON, default=dict)
    
    # Flags
    is_active = Column(Boolean, default=True, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    deleted_at = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="candidates")
    owner = relationship("User", back_populates="candidates", foreign_keys=[owner_id])
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    parsed_fields = relationship("ParsedField", back_populates="candidate", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="candidate", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="candidate", cascade="all, delete-orphan")
    work_experiences = relationship("WorkExperience", back_populates="candidate", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_candidates_org_status', 'organization_id', 'status'),
        Index('idx_candidates_org_confidence', 'organization_id', 'overall_confidence'),
        Index('idx_candidates_org_updated', 'organization_id', 'updated_at'),
        Index('idx_candidates_email_org', 'email', 'organization_id', unique=True),
        Index('idx_candidates_phone_org', 'phone', 'organization_id', unique=True),
        Index('idx_candidates_search', 'name', 'email', 'current_company'),
    )
    
    @hybrid_property
    def full_location(self):
        """Get full location string"""
        if self.city and self.country:
            return f"{self.city}, {self.country}"
        return self.location
    
    @hybrid_property
    def experience_level(self):
        """Categorize experience level"""
        if not self.years_experience:
            return "unknown"
        if self.years_experience <= 2:
            return "junior"
        elif self.years_experience <= 5:
            return "mid"
        elif self.years_experience <= 10:
            return "senior"
        else:
            return "expert"

class CandidateSkill(Base):
    """Candidate skills with confidence scores"""
    __tablename__ = "candidate_skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    skill = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=True)  # programming, framework, tool, language, etc.
    confidence = Column(Float, default=1.0)
    source = Column(String(50), nullable=True)  # resume, manual, conversation
    years_experience = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="skills")
    
    __table_args__ = (
        Index('idx_candidate_skills_skill', 'skill'),
        Index('idx_candidate_skills_candidate', 'candidate_id', 'skill', unique=True),
        Index('idx_candidate_skills_category', 'category'),
    )

class ParsedField(Base):
    """Parsed fields from resumes with confidence"""
    __tablename__ = "parsed_fields"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    raw_extraction = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)  # resume, conversation, manual
    parser_version = Column(String(50), nullable=True)
    extraction_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="parsed_fields")
    
    __table_args__ = (
        Index('idx_parsed_fields_candidate_name', 'candidate_id', 'name', unique=True),
        Index('idx_parsed_fields_source', 'source'),
    )

class Resume(Base):
    """Resume files with parsing metadata"""
    __tablename__ = "resumes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    
    # File Information
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, jpg, png
    file_size = Column(Integer, nullable=True)  # in bytes
    storage_path = Column(String(500), nullable=True)
    
    # Parsing Information
    raw_text = Column(Text, nullable=True)
    text_length = Column(Integer, nullable=True)
    language = Column(String(10), nullable=True)
    
    # Metadata
    parse_job_id = Column(UUID(as_uuid=True), nullable=True)
    parsing_engine = Column(String(50), nullable=True)
    parsing_version = Column(String(50), nullable=True)
    
    # Quality Metrics
    quality_score = Column(Float, nullable=True)
    readability_score = Column(Float, nullable=True)
    parsing_confidence = Column(Float, nullable=True)
    
    # Flags
    is_parsed = Column(Boolean, default=False, index=True)
    has_errors = Column(Boolean, default=False)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    parsed_at = Column(DateTime, nullable=True, index=True)
    reprocessed_at = Column(DateTime, nullable=True)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="resumes")
    jobs = relationship("Job", back_populates="resume", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_resumes_candidate_uploaded', 'candidate_id', 'uploaded_at'),
        Index('idx_resumes_is_parsed', 'is_parsed'),
        Index('idx_resumes_file_type', 'file_type'),
    )
    
    @hybrid_property
    def is_image_based(self):
        """Check if resume is image-based"""
        return self.file_type in ['jpg', 'jpeg', 'png']

class Message(Base):
    """Message model for conversation tracking"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    direction = Column(String(20), nullable=False, index=True)  # outgoing, incoming
    message_type = Column(String(50), default="text")  # text, template, automated
    
    # Metadata
    intent = Column(String(255), nullable=True)
    generated_by = Column(String(50), nullable=True)  # ai, manual, automated
    template_id = Column(String(100), nullable=True)
    asked_fields = Column(JSON, default=list)
    
    # Status
    status = Column(String(50), default="sent", index=True)  # sent, delivered, read, failed
    platform = Column(String(50), default="whatsapp")  # whatsapp, email, sms, internal
    
    # Analysis
    classification = Column(String(50), nullable=True, index=True)  # interested, not_interested, question, needs_clarification
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    suggested_reply = Column(Text, nullable=True)
    extracted_fields = Column(JSON, default=dict)
    
    # HR Review
    requires_hr_review = Column(Boolean, default=False, index=True)
    ai_suggested_reply = Column(Text, nullable=True)
    hr_approved = Column(Boolean, default=False, index=True)
    hr_approved_at = Column(DateTime, nullable=True)
    hr_approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Delivery Tracking
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    scheduled_for = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    message_metadata = Column(JSON, default=dict)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="messages")
    hr_approver = relationship("User", foreign_keys=[hr_approved_by])
    jobs = relationship("Job", back_populates="message", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_messages_candidate_direction', 'candidate_id', 'direction'),
        Index('idx_messages_candidate_timestamp', 'candidate_id', 'timestamp'),
        Index('idx_messages_requires_review', 'requires_hr_review', 'hr_approved'),
        Index('idx_messages_scheduled', 'scheduled_for', 'status'),
        Index('idx_messages_classification', 'classification'),
    )
    
    @hybrid_property
    def response_time_minutes(self):
        """Calculate response time if this is a reply"""
        if self.direction != 'incoming':
            return None
        
        # Find previous outgoing message
        # This would be calculated in queries
        return None

class Job(Base):
    """Background job tracking"""
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Job Information
    type = Column(String(50), nullable=False, index=True)  # parse_resume, send_message, follow_up, export, sync
    status = Column(String(50), default="queued", index=True)  # queued, processing, completed, failed, cancelled
    priority = Column(Integer, default=0)  # 0=normal, 1=high, 2=urgent
    
    # References
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=True, index=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True, index=True)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Progress Tracking
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(100), nullable=True)
    total_steps = Column(Integer, nullable=True)
    
    # Error Tracking
    error = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Scheduling
    scheduled_for = Column(DateTime, nullable=True, index=True)
    timeout_seconds = Column(Integer, default=3600)  # 1 hour default
    
    # Metadata
    job_metadata = Column(JSON, default=dict)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="jobs")
    candidate = relationship("Candidate", back_populates="jobs")
    resume = relationship("Resume", back_populates="jobs")
    message = relationship("Message", back_populates="jobs")
    assigned_to = relationship("User", back_populates="assigned_jobs", foreign_keys=[assigned_to_id])
    
    __table_args__ = (
        Index('idx_jobs_org_status', 'organization_id', 'status'),
        Index('idx_jobs_org_type', 'organization_id', 'type'),
        Index('idx_jobs_created_status', 'created_at', 'status'),
        Index('idx_jobs_scheduled_status', 'scheduled_for', 'status'),
    )
    
    @hybrid_property
    def duration_seconds(self):
        """Calculate job duration in seconds"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    @hybrid_property
    def is_stuck(self):
        """Check if job is stuck (processing for too long)"""
        if self.status != 'processing' or not self.started_at:
            return False
        
        duration = (datetime.utcnow() - self.started_at).total_seconds()
        return duration > self.timeout_seconds

class ConversationStage(Base):
    """Conversation stage tracking for candidates"""
    __tablename__ = "conversation_stages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    
    stage = Column(String(50), nullable=False, index=True)  # introduction, screening, follow_up, closing
    status = Column(String(50), default="pending")  # pending, in_progress, completed, skipped
    completed_fields = Column(JSON, default=list)
    pending_fields = Column(JSON, default=list)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate")
    
    __table_args__ = (
        Index('idx_conversation_stages_candidate_stage', 'candidate_id', 'stage', unique=True),
        Index('idx_conversation_stages_status', 'status'),
    )

class ExportJob(Base):
    """Export job tracking"""
    __tablename__ = "export_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Export Information
    format = Column(String(20), nullable=False)  # excel, csv, json, pdf
    filters = Column(JSON, default=dict)
    include_fields = Column(JSON, default=list)
    file_name = Column(String(255), nullable=True)
    file_url = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(50), default="queued")  # queued, processing, completed, failed
    progress = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_export_jobs_org_status', 'organization_id', 'status'),
        Index('idx_export_jobs_user', 'user_id', 'created_at'),
    )

class SyncJob(Base):
    """Sync job tracking for external integrations"""
    __tablename__ = "sync_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Sync Information
    platform = Column(String(50), nullable=False)  # google_sheets, ats, crm
    direction = Column(String(20), default="export")  # import, export, bidirectional
    config = Column(JSON, default=dict)
    
    # Status
    status = Column(String(50), default="queued")
    progress = Column(Integer, default=0)
    items_processed = Column(Integer, default=0)
    items_total = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_sync_jobs_org_platform', 'organization_id', 'platform'),
        Index('idx_sync_jobs_last_sync', 'last_sync_at'),
    )

class ActivityLog(Base):
    """Activity logging for audit trail"""
    __tablename__ = "activity_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Activity Information
    action = Column(String(100), nullable=False, index=True)  # candidate.created, resume.uploaded, message.sent
    resource_type = Column(String(50), nullable=False)  # candidate, resume, message, job
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)
    
    # Details
    details = Column(JSON, default=dict)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_activity_logs_org_action', 'organization_id', 'action'),
        Index('idx_activity_logs_created', 'created_at'),
        Index('idx_activity_logs_resource', 'resource_type', 'resource_id'),
    )