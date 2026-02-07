/**
 * Conversation Checklist Component - Modern & Responsive Redesign
 * Visual checklist showing field states: answered, asked, missing
 * Features: Progress tracking, filtering, search, responsive layouts
 */

import { cn } from "@/lib/utils";
import { 
  Check, 
  Clock, 
  X, 
  HelpCircle, 
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertCircle,
  MinusCircle,
  Sparkles,
  FileText,
  MessageSquare,
  User
} from "lucide-react";
import { BadgeConfidence } from "@/components/ui/BadgeConfidence";
import type { CandidateFieldKey, FieldState, ConversationState } from "@/types";
import { useState, useMemo } from "react";
import "@/styles/ConversationChacklist.css"

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

const FIELD_CATEGORIES: Record<string, { label: string; fields: CandidateFieldKey[]; icon: React.ComponentType<any> }> = {
  personal: {
    label: "Personal Information",
    icon: User,
    fields: ["name", "email", "phone", "location"],
  },
  professional: {
    label: "Professional Details",
    icon: FileText,
    fields: ["years_experience", "skills", "current_company", "education"],
  },
  additional: {
    label: "Additional Information",
    icon: Sparkles,
    fields: ["portfolio_url", "notice_period", "expected_salary"],
  },
};

type FilterType = "all" | "answered" | "asked" | "missing";

function getFieldStatus(field: FieldState): "answered" | "asked" | "missing" {
  if (field.answered && field.value !== undefined && field.value !== null) {
    return "answered";
  }
  if (field.asked) {
    return "asked";
  }
  return "missing";
}

function getStatusIcon(status: "answered" | "asked" | "missing", size: "sm" | "md" | "lg" = "md") {
  const sizeClass = size === "sm" ? "h-3.5 w-3.5" : size === "md" ? "h-4 w-4" : "h-5 w-5";
  
  switch (status) {
    case "answered":
      return <CheckCircle2 className={sizeClass} />;
    case "asked":
      return <Clock className={sizeClass} />;
    case "missing":
      return <MinusCircle className={sizeClass} />;
  }
}

function getStatusConfig(status: "answered" | "asked" | "missing") {
  switch (status) {
    case "answered":
      return {
        bgColor: "bg-emerald-50 dark:bg-emerald-950/20",
        borderColor: "border-emerald-200 dark:border-emerald-800",
        iconBgColor: "bg-emerald-100 dark:bg-emerald-900/40",
        iconColor: "text-emerald-600 dark:text-emerald-400",
        textColor: "text-emerald-700 dark:text-emerald-300",
        label: "Answered",
        badgeBg: "bg-emerald-100 dark:bg-emerald-900/40",
        badgeText: "text-emerald-700 dark:text-emerald-300",
      };
    case "asked":
      return {
        bgColor: "bg-amber-50 dark:bg-amber-950/20",
        borderColor: "border-amber-200 dark:border-amber-800",
        iconBgColor: "bg-amber-100 dark:bg-amber-900/40",
        iconColor: "text-amber-600 dark:text-amber-400",
        textColor: "text-amber-700 dark:text-amber-300",
        label: "Awaiting Response",
        badgeBg: "bg-amber-100 dark:bg-amber-900/40",
        badgeText: "text-amber-700 dark:text-amber-300",
      };
    case "missing":
      return {
        bgColor: "bg-slate-50 dark:bg-slate-900/20",
        borderColor: "border-slate-200 dark:border-slate-700",
        iconBgColor: "bg-slate-100 dark:bg-slate-800/40",
        iconColor: "text-slate-500 dark:text-slate-400",
        textColor: "text-slate-600 dark:text-slate-400",
        label: "Not Asked",
        badgeBg: "bg-slate-100 dark:bg-slate-800/40",
        badgeText: "text-slate-600 dark:text-slate-400",
      };
  }
}

function getSourceIcon(source?: "resume" | "reply" | "manual") {
  switch (source) {
    case "resume":
      return <FileText className="h-3 w-3" />;
    case "reply":
      return <MessageSquare className="h-3 w-3" />;
    case "manual":
      return <User className="h-3 w-3" />;
    default:
      return <HelpCircle className="h-3 w-3" />;
  }
}

function getSourceText(source?: "resume" | "reply" | "manual") {
  switch (source) {
    case "resume":
      return "From resume";
    case "reply":
      return "From conversation";
    case "manual":
      return "Manually added";
    default:
      return "From resume";
  }
}

function formatValue(value: any): string {
  if (Array.isArray(value)) {
    return value.slice(0, 3).join(", ") + (value.length > 3 ? ` +${value.length - 3} more` : "");
  }
  return String(value);
}

export function ConversationChecklist({
  conversationState,
  className,
}: ConversationChecklistProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<FilterType>("all");
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(Object.keys(FIELD_CATEGORIES))
  );

  // Calculate statistics
  const stats = useMemo(() => {
    const allFields = Object.keys(FIELD_LABELS) as CandidateFieldKey[];
    const answered = allFields.filter(
      (key) => getFieldStatus(conversationState.fields[key]) === "answered"
    ).length;
    const asked = allFields.filter(
      (key) => getFieldStatus(conversationState.fields[key]) === "asked"
    ).length;
    const missing = allFields.filter(
      (key) => getFieldStatus(conversationState.fields[key]) === "missing"
    ).length;
    const total = allFields.length;
    const progress = Math.round((answered / total) * 100);

    return { answered, asked, missing, total, progress };
  }, [conversationState]);

  // Filter fields
  const filteredCategories = useMemo(() => {
    const result: Record<string, CandidateFieldKey[]> = {};

    Object.entries(FIELD_CATEGORIES).forEach(([categoryKey, category]) => {
      const filtered = category.fields.filter((fieldKey) => {
        const field = conversationState.fields[fieldKey];
        const status = getFieldStatus(field);
        const label = FIELD_LABELS[fieldKey].toLowerCase();
        
        // Apply search filter
        if (searchQuery && !label.includes(searchQuery.toLowerCase())) {
          return false;
        }

        // Apply status filter
        if (filterType !== "all" && status !== filterType) {
          return false;
        }

        return true;
      });

      if (filtered.length > 0) {
        result[categoryKey] = filtered;
      }
    });

    return result;
  }, [conversationState, searchQuery, filterType]);

  const toggleCategory = (categoryKey: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryKey)) {
        next.delete(categoryKey);
      } else {
        next.add(categoryKey);
      }
      return next;
    });
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Progress Overview */}
      <div className="relative overflow-hidden rounded-xl border border-border bg-gradient-to-br from-primary/5 via-background to-background p-6">
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-foreground">Collection Progress</h3>
              <p className="text-sm text-muted-foreground">Track candidate information gathering</p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-primary">{stats.progress}%</div>
              <div className="text-xs text-muted-foreground">Complete</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="relative h-3 rounded-full bg-muted overflow-hidden mb-4">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-500 to-emerald-600 transition-all duration-500 ease-out"
              style={{ width: `${stats.progress}%` }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <div className="flex-1">
                <div className="text-xs text-emerald-700 dark:text-emerald-300 font-medium">Answered</div>
                <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{stats.answered}</div>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
              <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <div className="flex-1">
                <div className="text-xs text-amber-700 dark:text-amber-300 font-medium">Pending</div>
                <div className="text-lg font-bold text-amber-600 dark:text-amber-400">{stats.asked}</div>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-700">
              <MinusCircle className="h-4 w-4 text-slate-500 dark:text-slate-400" />
              <div className="flex-1">
                <div className="text-xs text-slate-600 dark:text-slate-400 font-medium">Missing</div>
                <div className="text-lg font-bold text-slate-600 dark:text-slate-400">{stats.missing}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search fields..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          />
        </div>

        {/* Filter Buttons */}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {[
            { type: "all" as FilterType, label: "All", icon: Filter },
            { type: "answered" as FilterType, label: "Answered", icon: CheckCircle2 },
            { type: "asked" as FilterType, label: "Pending", icon: Clock },
            { type: "missing" as FilterType, label: "Missing", icon: MinusCircle },
          ].map(({ type, label, icon: Icon }) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
                filterType === type
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Field Categories */}
      <div className="space-y-3">
        {Object.entries(filteredCategories).map(([categoryKey, fields]) => {
          const category = FIELD_CATEGORIES[categoryKey];
          const isExpanded = expandedCategories.has(categoryKey);
          const Icon = category.icon;

          // Calculate category stats
          const categoryStats = {
            answered: fields.filter(
              (key) => getFieldStatus(conversationState.fields[key]) === "answered"
            ).length,
            total: fields.length,
          };

          return (
            <div key={categoryKey} className="rounded-xl border border-border bg-card overflow-hidden">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(categoryKey)}
                className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-left">
                    <div className="font-semibold text-sm text-foreground">{category.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {categoryStats.answered} of {categoryStats.total} collected
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {/* Mini progress */}
                  <div className="hidden sm:flex items-center gap-2">
                    <div className="w-24 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 transition-all"
                        style={{
                          width: `${(categoryStats.answered / categoryStats.total) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-medium text-muted-foreground min-w-[3ch] text-right">
                      {Math.round((categoryStats.answered / categoryStats.total) * 100)}%
                    </span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              </button>

              {/* Category Fields */}
              {isExpanded && (
                <div className="border-t border-border bg-muted/30">
                  <div className="p-3 space-y-2">
                    {fields.map((fieldKey) => {
                      const field = conversationState.fields[fieldKey];
                      const status = getFieldStatus(field);
                      const config = getStatusConfig(status);

                      return (
                        <div
                          key={fieldKey}
                          className={cn(
                            "group relative rounded-lg border p-4 transition-all hover:shadow-sm",
                            config.bgColor,
                            config.borderColor
                          )}
                        >
                          <div className="flex items-start gap-3">
                            {/* Status Icon */}
                            <div
                              className={cn(
                                "flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-full transition-transform group-hover:scale-110",
                                config.iconBgColor
                              )}
                            >
                              <div className={config.iconColor}>
                                {getStatusIcon(status, "md")}
                              </div>
                            </div>

                            {/* Field Content */}
                            <div className="flex-1 min-w-0">
                              {/* Header */}
                              <div className="flex items-start justify-between gap-2 mb-1">
                                <h4 className="font-medium text-sm text-foreground">
                                  {FIELD_LABELS[fieldKey]}
                                </h4>
                                <span
                                  className={cn(
                                    "flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium",
                                    config.badgeBg,
                                    config.badgeText
                                  )}
                                >
                                  {config.label}
                                </span>
                              </div>

                              {/* Value */}
                              {status === "answered" && field.value !== undefined && (
                                <div className="space-y-2">
                                  <p className="text-sm text-foreground font-medium">
                                    {formatValue(field.value)}
                                  </p>

                                  {/* Metadata */}
                                  <div className="flex items-center gap-3 text-xs">
                                    {field.source && (
                                      <div className="flex items-center gap-1 text-muted-foreground">
                                        {getSourceIcon(field.source)}
                                        <span>{getSourceText(field.source)}</span>
                                      </div>
                                    )}
                                    {field.confidence > 0 && (
                                      <div className="flex items-center gap-1">
                                        <BadgeConfidence
                                          confidence={field.confidence * 100}
                                          size="sm"
                                        />
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}

                              {status === "asked" && (
                                <p className="text-xs text-muted-foreground">
                                  Waiting for candidate response
                                </p>
                              )}

                              {status === "missing" && (
                                <p className="text-xs text-muted-foreground">
                                  This field hasn't been requested yet
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {Object.keys(filteredCategories).length === 0 && (
        <div className="text-center py-12">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
            <Search className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No fields found</h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto">
            {searchQuery
              ? `No fields match "${searchQuery}". Try adjusting your search.`
              : "Try changing your filter to see more fields."}
          </p>
        </div>
      )}
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
    years_experience: candidate.yearsExperience || 0,
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