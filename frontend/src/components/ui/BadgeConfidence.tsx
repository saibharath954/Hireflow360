/**
 * Badge Confidence Component
 * Displays a confidence score with color-coded indicator
 */

import { cn } from "@/lib/utils";
import { getConfidenceLevel, formatConfidence } from "@/styles/design-tokens";

interface BadgeConfidenceProps {
  confidence: number;
  showLabel?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function BadgeConfidence({
  confidence,
  showLabel = true,
  size = "md",
  className,
}: BadgeConfidenceProps) {
  const level = getConfidenceLevel(confidence);

  const levelClasses = {
    high: "bg-success/10 text-success border-success/20",
    medium: "bg-warning/10 text-warning border-warning/20",
    low: "bg-destructive/10 text-destructive border-destructive/20",
  };

  const sizeClasses = {
    sm: "text-xs px-1.5 py-0.5",
    md: "text-sm px-2 py-1",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border font-medium",
        levelClasses[level],
        sizeClasses[size],
        className
      )}
      title={`Confidence: ${formatConfidence(confidence)}`}
    >
      <span
        className={cn(
          "rounded-full",
          size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2",
          level === "high" && "bg-success",
          level === "medium" && "bg-warning",
          level === "low" && "bg-destructive"
        )}
      />
      {showLabel && formatConfidence(confidence)}
    </span>
  );
}
