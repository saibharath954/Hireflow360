/**
 * Conversation Checklist Component
 * Visual checklist showing field states: answered, asked, missing
 */

import { cn } from "@/lib/utils";
import { Check, Clock, X, HelpCircle } from "lucide-react";
import { BadgeConfidence } from "@/components/ui/BadgeConfidence";
import type { CandidateFieldKey, FieldState, ConversationState } from "@/types";

interface ConversationChecklistProps {
  conversationState: ConversationState;
  className?: string;
}

const FIELD_LABELS: Record<CandidateFieldKey, string> = {
  name: "Full Name",
  email: "Email Address",
  phone: "Phone Number",
  years_experience: "Years of Experience",
  skills: "Technical Skills",
  current_company: "Current Company",
  education: "Education",
  location: "Location",
  portfolio_url: "Portfolio URL",
  notice_period: "Notice Period",
  expected_salary: "Expected Salary",
};

const FIELD_ORDER: CandidateFieldKey[] = [
  "name",
  "email",
  "phone",
  "years_experience",
  "skills",
  "current_company",
  "education",
  "location",
];

function getFieldStatus(field: FieldState): "answered" | "asked" | "missing" {
  if (field.answered && field.value !== undefined && field.value !== null) {
    return "answered";
  }
  if (field.asked) {
    return "asked";
  }
  return "missing";
}

function getStatusIcon(status: "answered" | "asked" | "missing") {
  switch (status) {
    case "answered":
      return <Check className="h-4 w-4" />;
    case "asked":
      return <Clock className="h-4 w-4" />;
    case "missing":
      return <X className="h-4 w-4" />;
  }
}

function getStatusColor(status: "answered" | "asked" | "missing") {
  switch (status) {
    case "answered":
      return "text-success bg-success/10 border-success/20";
    case "asked":
      return "text-warning bg-warning/10 border-warning/20";
    case "missing":
      return "text-muted-foreground bg-muted border-border";
  }
}

function getStatusLabel(status: "answered" | "asked" | "missing") {
  switch (status) {
    case "answered":
      return "Answered";
    case "asked":
      return "Asked (awaiting)";
    case "missing":
      return "Not yet asked";
  }
}

function getSourceText(source?: "resume" | "reply" | "manual") {
  switch (source) {
    case "resume":
      return "Extracted from resume";
    case "reply":
      return "Answered in chat";
    case "manual":
      return "Manually entered";
    default:
      return "";
  }
}

export function ConversationChecklist({
  conversationState,
  className,
}: ConversationChecklistProps) {
  const answeredCount = FIELD_ORDER.filter(
    (key) => getFieldStatus(conversationState.fields[key]) === "answered"
  ).length;

  const askedCount = FIELD_ORDER.filter(
    (key) => getFieldStatus(conversationState.fields[key]) === "asked"
  ).length;

  return (
    <div className={cn("space-y-4", className)}>
      {/* Summary */}
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5">
          <Check className="h-4 w-4 text-success" />
          <span className="text-muted-foreground">
            {answeredCount}/{FIELD_ORDER.length} answered
          </span>
        </div>
        {askedCount > 0 && (
          <div className="flex items-center gap-1.5">
            <Clock className="h-4 w-4 text-warning" />
            <span className="text-muted-foreground">{askedCount} pending</span>
          </div>
        )}
      </div>

      {/* Field list */}
      <div className="space-y-2">
        {FIELD_ORDER.map((fieldKey) => {
          const field = conversationState.fields[fieldKey];
          const status = getFieldStatus(field);

          return (
            <div
              key={fieldKey}
              className={cn(
                "flex items-center gap-3 p-3 rounded-lg border transition-colors",
                status === "answered" && "bg-success/5 border-success/20",
                status === "asked" && "bg-warning/5 border-warning/20",
                status === "missing" && "bg-muted/50 border-border"
              )}
            >
              {/* Status icon */}
              <div
                className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-full border",
                  getStatusColor(status)
                )}
              >
                {getStatusIcon(status)}
              </div>

              {/* Field info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">
                    {FIELD_LABELS[fieldKey]}
                  </span>
                  <span
                    className={cn(
                      "text-xs px-1.5 py-0.5 rounded",
                      getStatusColor(status)
                    )}
                  >
                    {getStatusLabel(status)}
                  </span>
                </div>

                {status === "answered" && field.value !== undefined && (
                  <div className="mt-1">
                    <p className="text-sm text-foreground truncate">
                      {Array.isArray(field.value)
                        ? field.value.slice(0, 3).join(", ") +
                          (field.value.length > 3 ? "..." : "")
                        : String(field.value)}
                    </p>
                    {field.source && (
                      <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                        <HelpCircle className="h-3 w-3" />
                        {getSourceText(field.source)}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Confidence badge (only for answered fields) */}
              {status === "answered" && field.confidence > 0 && (
                <BadgeConfidence
                  confidence={field.confidence * 100}
                  size="sm"
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Helper function to derive ConversationState from candidate data
export function deriveConversationState(
  candidate: {
    name?: string;
    email?: string;
    phone?: string;
    yearsExperience?: number;
    skills?: string[];
    currentCompany?: string;
    education?: string;
    location?: string;
    parsedFields?: Array<{
      name: string;
      value: unknown;
      confidence: number;
      source?: string;
    }>;
    messages?: Array<{
      direction: string;
      askedFields?: CandidateFieldKey[];
      extractedFields?: Array<{ name: string; value: unknown; confidence: number }>;
    }>;
  }
): ConversationState {
  // Map from candidate fields to parsed field names
  const fieldMapping: Record<CandidateFieldKey, string> = {
    name: "name",
    email: "email",
    phone: "phone",
    years_experience: "years_experience",
    skills: "skills",
    current_company: "current_company",
    education: "education",
    location: "location",
    portfolio_url: "portfolio_url",
    notice_period: "notice_period",
    expected_salary: "expected_salary",
  };

  // Initialize all fields
  const fields: Record<CandidateFieldKey, FieldState> = {
    name: { confidence: 0, asked: false, answered: false },
    email: { confidence: 0, asked: false, answered: false },
    phone: { confidence: 0, asked: false, answered: false },
    years_experience: { confidence: 0, asked: false, answered: false },
    skills: { confidence: 0, asked: false, answered: false },
    current_company: { confidence: 0, asked: false, answered: false },
    education: { confidence: 0, asked: false, answered: false },
    location: { confidence: 0, asked: false, answered: false },
    portfolio_url: { confidence: 0, asked: false, answered: false },
    notice_period: { confidence: 0, asked: false, answered: false },
    expected_salary: { confidence: 0, asked: false, answered: false },
  };

  // Populate from candidate top-level fields
  const directFieldValues: Record<CandidateFieldKey, unknown> = {
    name: candidate.name,
    email: candidate.email,
    phone: candidate.phone,
    years_experience: candidate.yearsExperience,
    skills: candidate.skills,
    current_company: candidate.currentCompany,
    education: candidate.education,
    location: candidate.location,
    portfolio_url: undefined,
    notice_period: undefined,
    expected_salary: undefined,
  };

  // Get confidence from parsed fields
  const parsedFieldsMap = new Map(
    (candidate.parsedFields || []).map((pf) => [pf.name, pf])
  );

  // Process each field
  (Object.keys(fields) as CandidateFieldKey[]).forEach((key) => {
    const parsedFieldName = fieldMapping[key];
    const parsedField = parsedFieldsMap.get(parsedFieldName);
    const directValue = directFieldValues[key];

    // Check if field has a value
    const hasValue =
      directValue !== undefined &&
      directValue !== null &&
      directValue !== "" &&
      (!Array.isArray(directValue) || directValue.length > 0);

    if (hasValue) {
      fields[key] = {
        value: directValue as FieldState["value"],
        confidence: parsedField ? parsedField.confidence / 100 : 0.5,
        asked: false,
        answered: true,
        source: (parsedField?.source as FieldState["source"]) || "resume",
      };
    }
  });

  // Process messages to update asked status
  (candidate.messages || []).forEach((msg) => {
    if (msg.direction === "outgoing" && msg.askedFields) {
      msg.askedFields.forEach((fieldKey) => {
        if (fields[fieldKey] && !fields[fieldKey].answered) {
          fields[fieldKey].asked = true;
        }
      });
    }

    // Check extracted fields from replies
    if (msg.direction === "incoming" && msg.extractedFields) {
      Object.entries(msg.extractedFields).forEach(
        ([parsedName, ef]: [string, any]) => {

          const fieldKey = (Object.entries(fieldMapping).find(
            ([, v]) => v === parsedName
          )?.[0] || "") as CandidateFieldKey;

          if (fieldKey && fields[fieldKey]) {
            fields[fieldKey] = {
              value: ef.value as FieldState["value"],
              confidence: (ef.confidence ?? 50) / 100,
              asked: false,
              answered: true,
              source: "reply",
            };
          }
        }
      );
    }
  });

  return { fields };
}

// Get pending fields (not answered and not asked)
export function getPendingFields(
  conversationState: ConversationState
): CandidateFieldKey[] {
  return (Object.entries(conversationState.fields) as [CandidateFieldKey, FieldState][])
    .filter(([, field]) => !field.answered && !field.asked)
    .map(([key]) => key);
}
