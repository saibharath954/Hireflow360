/**
 * Updated Type Definitions for Backend Integration
 * Matches FastAPI Pydantic schemas exactly
 */

import type {
  MessageStatus,
  CandidateStatus,
  ReplyClassification,
  JobStatus,
  JobType,
} from "@/styles/design-tokens";

// Use VITE_API_BASE_URL env var or fallback to localhost v1
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  status?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// Authentication Types
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number;
  user: User;
}

export interface TokenRefreshResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
}

export interface LogoutResponse {
  message: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  password: string;
}

export interface PasswordResetResponse {
  message: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  organization_id?: string;
  role?: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  name: string;
  organization_id?: string;
  created_at: string;
}

export interface ValidateTokenResponse {
  valid: boolean;
  user?: User;
}

// ... (Rest of the file remains unchanged)

// POST /api/v1/auth/login
export interface LoginRequest {
  email: string;
  password: string;
}

// POST /api/v1/auth/refresh
export interface RefreshTokenRequest {
  refresh_token: string;
}

// POST /api/v1/auth/password-reset-request
export interface PasswordResetRequestData {
  email: string;
}

// POST /api/v1/auth/password-reset-confirm
export interface PasswordResetConfirmData {
  token: string;
  password: string;
}

// POST /api/v1/auth/register
export interface RegisterUserRequest {
  email: string;
  password: string;
  name: string;
  organization_id?: string;
  role?: string;
}

// User & Organization
export type UserRole = "ADMIN" | "RECRUITER";

export interface User {
  id: string;
  email: string;
  name: string;
  organizationId: string;
  organizationName: string;
  role: UserRole;
  avatarUrl?: string;
}

export interface Organization {
  id: string;
  name: string;
  logo?: string;
}

// Conversation State
export type CandidateFieldKey =
  | "name"
  | "email"
  | "phone"
  | "experience"
  | "skills"
  | "currentCompany"
  | "education"
  | "location";

export interface FieldState {
  value?: string | string[] | number | null;
  confidence: number;
  asked: boolean;
  answered: boolean;
  source?: "resume" | "reply" | "manual";
}

export interface ConversationState {
  fields: Record<CandidateFieldKey, FieldState>;
}

// Parsed Fields
export interface ParsedField {
  name: string;
  value: string | string[] | number | null;
  confidence: number;
  rawExtraction?: string;
  source?: "resume" | "reply" | "manual";
}

// Resume
export interface Resume {
  id: string;
  candidateId: string;
  fileName: string;
  fileUrl: string;
  fileType: "pdf" | "docx" | "image-pdf";
  uploadedAt: string;
  parsedAt?: string;
  parseJobId?: string;
  rawText?: string;
}

// Candidate
export interface Candidate {
  id: string;
  name: string;
  email: string;
  phone?: string;
  yearsExperience?: number;
  skills: string[];
  currentCompany?: string;
  education?: string;
  location?: string;
  portfolioUrl?: string;
  noticePeriod?: string;
  expectedSalary?: string;
  status: CandidateStatus;
  parsedFields: ParsedField[];
  resumes: Resume[];
  messages: Message[];
  lastMessageAt?: string;
  overallConfidence: number;
  conversationState?: ConversationState;
  createdAt: string;
  updatedAt: string;
}

// Message
export interface Message {
  id: string;
  candidateId: string;
  direction: "incoming" | "outgoing";
  content: string;
  timestamp: string;
  status: MessageStatus;
  intent?: string;
  generatedBy?: "ai" | "manual";
  classification?: ReplyClassification;
  suggestedReply?: string;
  extractedFields?: ParsedField[];
  requiresHRReview?: boolean;
  aiSuggestedReply?: string;
  hrApproved?: boolean;
  hrApprovedAt?: string;
  askedFields?: CandidateFieldKey[];
}

export interface MessagePreview {
  content: string;
  candidateId: string;
  intent: string;
  askedFields?: CandidateFieldKey[];
  metadata?: {
    tokensUsed?: number;
    modelVersion?: string;
  };
}

// Job
export interface Job {
  id: string;
  type: JobType;
  status: JobStatus;
  progress?: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  metadata?: Record<string, unknown>;
  candidateId?: string;
  resumeId?: string;
  messageId?: string;
  candidateName?: string;
  candidateEmail?: string;
}

// Filters
export interface CandidateFilters {
  search?: string;
  skills?: string[];
  status?: CandidateStatus[];
  minExperience?: number;
  maxExperience?: number;
  location?: string;
  dateRange?: {
    from: string;
    to: string;
  };
}

// Export
export interface ExportOptions {
  format: "xlsx" | "csv";
  fields?: string[];
  includeMessages?: boolean;
  candidateIds?: string[];
}

// Settings
export interface AppSettings {
  mode: "mock" | "automation";
  theme: "light" | "dark" | "system";
  defaultIntentTemplates: string[];
}

// Dashboard
export interface DashboardStats {
  totalCandidates: number;
  resumesProcessed: number;
  messagesSent: number;
  repliesReceived: number;
  pendingJobs: number;
  interestedCandidates: number;
}

export interface ActivityItem {
  id: string;
  type: "resume_uploaded" | "resume_parsed" | "message_sent" | "reply_received" | "candidate_updated";
  description: string;
  timestamp: string;
  candidateId?: string;
  candidateName?: string;
}

// API Error Types
export interface ApiError {
  status: number;
  message: string;
  details?: any;
}

export interface NetworkError {
  message: string;
  isNetworkError: boolean;
}

export interface ReplyCreate {
  candidate_id: string;
  content: string;
}