# backend/app/schemas/schemas.py
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
import uuid

# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

# User & Auth

class TokenRefresh(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
class UserBase(BaseSchema):
    email: str
    name: str
    organization_id: uuid.UUID
    organization_name: str
    role: str
    
class User(UserBase):
    id: uuid.UUID

class UserCreate(BaseSchema):
    email: str
    name: str
    password: str
    organization_name: str
    role: str = "RECRUITER"

class UserResponse(BaseSchema):
    id: uuid.UUID
    email: str
    name: str
    organization_name: str
    role: str

class UserLogin(BaseSchema):
    email: str
    password: str

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: User

# Conversation State
class FieldState(BaseSchema):
    value: Optional[Union[str, List[str], int]] = None
    confidence: float = Field(ge=0, le=1)
    asked: bool = False
    answered: bool = False
    source: Optional[str] = None

class ConversationState(BaseSchema):
    fields: Dict[str, FieldState]

# Parsed Fields
class ParsedField(BaseSchema):
    name: str
    value: Optional[Union[str, List[str], int]] = None
    confidence: float = Field(ge=0, le=100)
    raw_extraction: Optional[str] = None
    source: Optional[str] = None

class ConfidenceScore(BaseSchema):
    field: str
    score: float
    is_verified: bool

# Resume
class ResumeBase(BaseSchema):
    file_name: str
    file_url: str
    file_type: str
    uploaded_at: datetime
    parsed_at: Optional[datetime] = None
    parse_job_id: Optional[str] = None
    raw_text: Optional[str] = None

class Resume(ResumeBase):
    id: uuid.UUID
    candidate_id: uuid.UUID

# Candidate
class CandidateBase(BaseSchema):
    name: str
    email: str
    phone: Optional[str] = None
    years_experience: Optional[int] = None
    skills: List[str] = []
    current_company: Optional[str] = None
    education: Optional[str] = None
    location: Optional[str] = None
    portfolio_url: Optional[str] = None
    notice_period: Optional[str] = None
    expected_salary: Optional[str] = None

class CandidateCreate(CandidateBase):
    organization_id: uuid.UUID

class CandidateUpdate(BaseSchema):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    years_experience: Optional[int] = None
    skills: Optional[List[str]] = None
    current_company: Optional[str] = None
    education: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    overall_confidence: Optional[float] = None
    conversation_state: Optional[ConversationState] = None

class Candidate(CandidateBase):
    id: uuid.UUID
    status: str
    parsed_fields: List[ParsedField] = []
    resumes: List[Resume] = []
    messages: List["Message"] = []
    last_message_at: Optional[datetime] = None
    overall_confidence: float
    conversation_state: Optional[ConversationState] = None
    created_at: datetime
    updated_at: datetime

class CandidateFieldKey(str, Enum):
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    YEARS_EXPERIENCE = "years_experience"
    SKILLS = "skills"
    CURRENT_COMPANY = "current_company"
    EDUCATION = "education"
    LOCATION = "location"
    PORTFOLIO_URL = "portfolio_url"
    NOTICE_PERIOD = "notice_period"
    EXPECTED_SALARY = "expected_salary"

# Message
class MessageBase(BaseSchema):
    content: str
    direction: str
    timestamp: datetime
    status: str

class SendMessageRequest(BaseSchema):
    content: str
    asked_fields: List[str] = []

class MessageCreate(BaseSchema):
    candidate_id: uuid.UUID
    content: str
    direction: str = "outgoing"
    intent: Optional[str] = None
    generated_by: Optional[str] = None
    asked_fields: Optional[List[str]] = None
    requires_hr_review: Optional[bool] = False

class ReplyCreate(BaseSchema):
    candidate_id: uuid.UUID
    content: str
    classification: Optional[str] = None

class Message(MessageBase):
    id: uuid.UUID
    candidate_id: uuid.UUID
    intent: Optional[str] = None
    generated_by: Optional[str] = None
    classification: Optional[str] = None
    suggested_reply: Optional[str] = None
    extracted_fields: Dict[str, Any] = {}
    requires_hr_review: Optional[bool] = False
    ai_suggested_reply: Optional[str] = None
    hr_approved: Optional[bool] = False
    hr_approved_at: Optional[datetime] = None
    asked_fields: Optional[List[str]] = None

class MessagePreview(BaseSchema):
    content: str
    candidate_id: uuid.UUID
    intent: str
    asked_fields: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

# Job
class JobBase(BaseSchema):
    type: str
    status: str
    progress: Optional[int] = None
    error: Optional[str] = None
    job_metadata: Optional[Dict[str, Any]] = None
    candidate_id: Optional[uuid.UUID] = None
    resume_id: Optional[uuid.UUID] = None
    message_id: Optional[uuid.UUID] = None

class Job(JobBase):
    id: uuid.UUID
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# Filters & Pagination
class CandidateFilters(BaseSchema):
    search: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[List[str]] = None
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    location: Optional[str] = None
    date_range: Optional[Dict[str, datetime]] = None

class PaginatedResponse(BaseSchema):
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_more: bool

class ApiResponse(BaseSchema):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None

# Export & Settings
class ExportOptions(BaseSchema):
    format: str = "xlsx"
    fields: Optional[List[str]] = None
    include_messages: Optional[bool] = False
    candidate_ids: Optional[List[uuid.UUID]] = None

class GoogleSheetsSyncConfig(BaseSchema):
    sheet_id: str
    sheet_name: str
    last_sync_at: Optional[datetime] = None
    auto_sync: bool = False
    sync_interval: Optional[int] = None

class AppSettings(BaseSchema):
    mode: str = "mock"
    theme: str = "light"
    google_sheets_config: Optional[GoogleSheetsSyncConfig] = None
    default_intent_templates: List[str] = []

# Dashboard
class DashboardStats(BaseSchema):
    total_candidates: int
    resumes_processed: int
    messages_sent: int
    replies_received: int
    pending_jobs: int
    interested_candidates: int

class ActivityItem(BaseSchema):
    id: str
    type: str
    description: str
    timestamp: datetime
    candidate_id: Optional[uuid.UUID] = None
    candidate_name: Optional[str] = None