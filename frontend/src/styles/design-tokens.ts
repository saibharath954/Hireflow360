/**
 * Design Tokens for AI Resume Intake & HR Communication Platform
 * Centralized type definitions for design system values
 */

// Typography scale (in pixels, used for reference)
export const typography = {
  h1: 32,
  h2: 24,
  h3: 20,
  body: 16,
  small: 13,
} as const;

// Spacing scale (in pixels)
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  "2xl": 32,
} as const;

// Confidence thresholds
export const confidenceThresholds = {
  high: 80, // 80-100%
  medium: 50, // 50-79%
  low: 0, // 0-49%
} as const;

// Message status types
export type MessageStatus = "pending" | "sent" | "delivered" | "failed";

// Candidate status types
export type CandidateStatus =
  | "new"
  | "contacted"
  | "interested"
  | "not_interested"
  | "needs_clarification"
  | "hired"
  | "rejected";

// Reply classification types
export type ReplyClassification =
  | "interested"
  | "not_interested"
  | "needs_clarification"
  | "question";

// Job status types
export type JobStatus = "queued" | "processing" | "completed" | "failed";

// Job types
export type JobType = "parse_resume" | "send_message" | "sync_sheets" | "export";

// Parsed field names
export type ParsedFieldName =
  | "name"
  | "email"
  | "phone"
  | "years_experience"
  | "skills"
  | "current_company"
  | "education"
  | "location"
  | "portfolio"
  | "notice_period"
  | "expected_salary";

// Helper function to get confidence level
export function getConfidenceLevel(
  confidence: number
): "high" | "medium" | "low" {
  if (confidence >= confidenceThresholds.high) return "high";
  if (confidence >= confidenceThresholds.medium) return "medium";
  return "low";
}

// Helper function to format confidence as percentage
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence)}%`;
}
