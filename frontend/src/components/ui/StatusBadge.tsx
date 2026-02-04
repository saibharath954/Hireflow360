/**
 * Status Badge Component
 * Displays candidate status with appropriate colors
 */

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
// import type { CandidateStatus } from "@/styles/design-tokens"; // Removed strictly typed import to prevent TS errors on unknown statuses

interface StatusBadgeProps {
  status: string; // Changed to string to accept any backend value without crashing
  className?: string;
}

// 1. Add a Default Configuration
const defaultConfig = {
  label: "Unknown",
  className: "bg-gray-100 text-gray-500 border-gray-200",
};

const statusConfig: Record<string, { label: string; className: string }> = {
  new: {
    label: "New",
    className: "bg-muted text-muted-foreground border-muted",
  },
  contacted: {
    label: "Contacted",
    className: "bg-blue-100 text-blue-700 border-blue-200", // Adjusted to standard colors if 'info' token is missing
  },
  interested: {
    label: "Interested",
    className: "bg-green-100 text-green-700 border-green-200",
  },
  not_interested: {
    label: "Not Interested",
    className: "bg-red-100 text-red-700 border-red-200",
  },
  needs_clarification: {
    label: "Needs Clarification",
    className: "bg-yellow-100 text-yellow-700 border-yellow-200",
  },
  interview: { // Added likely missing status
    label: "Interview",
    className: "bg-orange-100 text-orange-700 border-orange-200",
  },
  hired: {
    label: "Hired",
    className: "bg-emerald-100 text-emerald-700 border-emerald-200",
  },
  rejected: {
    label: "Rejected",
    className: "bg-gray-200 text-gray-700 border-gray-300",
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  // 2. SAFETY CHECK:
  // If status is null/undefined, or not in the list, use defaultConfig.
  // We also lowercase it to handle "New" vs "new".
  const safeStatus = status?.toLowerCase() || "";
  const config = statusConfig[safeStatus] || defaultConfig;

  return (
    <Badge
      variant="outline"
      className={cn("font-medium", config.className, className)}
    >
      {config.label}
    </Badge>
  );
}