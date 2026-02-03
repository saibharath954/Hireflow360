/**
 * Type definitions for the AI Resume Intake & HR Communication Platform
 */

import type {
  MessageStatus,
  CandidateStatus,
  ReplyClassification,
  JobStatus,
  JobType,
  ParsedFieldName,
} from "@/styles/design-tokens";

// User & Authentication
export type UserRole = "RECRUITER" | "ADMIN";

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

// Conversation State Types (for tracking asked/answered fields)
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
  confidence: number; // 0-1
  asked: boolean;
  answered: boolean;
  source?: "resume" | "reply" | "manual";
}

export interface ConversationState {
  fields: Record<CandidateFieldKey, FieldState>;
}

// Parsed Fields & Confidence
export interface ParsedField {
  name: ParsedFieldName;
  value: string | string[] | number | null;
  confidence: number; // 0-100
  rawExtraction?: string; // Original text from extraction
  source?: "resume" | "reply" | "manual";
}

export interface ConfidenceScore {
  field: ParsedFieldName;
  score: number;
  isVerified: boolean;
}

// Resume & Candidate
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

export interface Candidate {
  id: string;
  // Parsed fields
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
  // Metadata
  status: CandidateStatus;
  parsedFields: ParsedField[];
  resumes: Resume[];
  messages: Message[];
  lastMessageAt?: string;
  createdAt: string;
  updatedAt: string;
  // Confidence scores
  overallConfidence: number;
  // Conversation state tracking
  conversationState?: ConversationState;
}

// Messaging
export interface Message {
  id: string;
  candidateId: string;
  direction: "incoming" | "outgoing";
  content: string;
  timestamp: string;
  status: MessageStatus;
  // For outgoing messages
  intent?: string;
  generatedBy?: "ai" | "manual";
  // For incoming messages
  classification?: ReplyClassification;
  suggestedReply?: string;
  extractedFields?: ParsedField[];
  // HR Review fields (for questions requiring approval)
  requiresHRReview?: boolean;
  aiSuggestedReply?: string;
  hrApproved?: boolean;
  hrApprovedAt?: string;
  // Track which fields were asked in outgoing messages
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

// Background Jobs
export interface Job {
  id: string;
  type: JobType;
  status: JobStatus;
  progress?: number; // 0-100
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  metadata?: Record<string, unknown>;
  // References
  candidateId?: string;
  resumeId?: string;
  messageId?: string;
}

// API Responses
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// Filters & Search
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

// Export & Sync
export interface ExportOptions {
  format: "xlsx" | "csv";
  fields?: ParsedFieldName[];
  includeMessages?: boolean;
  candidateIds?: string[];
}

export interface GoogleSheetsSyncConfig {
  sheetId: string;
  sheetName: string;
  lastSyncAt?: string;
  autoSync: boolean;
  syncInterval?: number; // minutes
}

// App Settings
export interface AppSettings {
  mode: "mock" | "automation";
  theme: "light" | "dark" | "system";
  googleSheetsConfig?: GoogleSheetsSyncConfig;
  defaultIntentTemplates: string[];
}

// Dashboard Stats
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
