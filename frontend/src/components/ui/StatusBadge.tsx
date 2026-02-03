/**
 * Status Badge Component
 * Displays candidate status with appropriate colors
 */

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { CandidateStatus } from "@/styles/design-tokens";

interface StatusBadgeProps {
  status: CandidateStatus;
  className?: string;
}

const statusConfig: Record<CandidateStatus, { label: string; className: string }> = {
  new: {
    label: "New",
    className: "bg-muted text-muted-foreground border-muted",
  },
  contacted: {
    label: "Contacted",
    className: "bg-info/10 text-info border-info/20",
  },
  interested: {
    label: "Interested",
    className: "bg-success/10 text-success border-success/20",
  },
  not_interested: {
    label: "Not Interested",
    className: "bg-destructive/10 text-destructive border-destructive/20",
  },
  needs_clarification: {
    label: "Needs Clarification",
    className: "bg-warning/10 text-warning border-warning/20",
  },
  hired: {
    label: "Hired",
    className: "bg-success/10 text-success border-success/20",
  },
  rejected: {
    label: "Rejected",
    className: "bg-muted text-muted-foreground border-muted",
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <Badge
      variant="outline"
      className={cn("font-medium", config.className, className)}
    >
      {config.label}
    </Badge>
  );
}
