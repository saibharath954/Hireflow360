/**
 * Message Bubble Component
 * Displays chat-style messages (incoming/outgoing)
 */

import { cn } from "@/lib/utils";
import { Check, CheckCheck, Clock, AlertCircle, AlertTriangle } from "lucide-react";
import type { MessageStatus, ReplyClassification } from "@/styles/design-tokens";
import { Badge } from "@/components/ui/badge";

interface MessageBubbleProps {
  content: string;
  direction: "incoming" | "outgoing";
  timestamp: string;
  status?: MessageStatus;
  classification?: ReplyClassification;
  suggestedReply?: string;
  requiresHRReview?: boolean;
  className?: string;
}

const statusIcons = {
  pending: Clock,
  sent: Check,
  delivered: CheckCheck,
  failed: AlertCircle,
};

const classificationLabels: Record<ReplyClassification, string> = {
  interested: "Interested",
  not_interested: "Not Interested",
  needs_clarification: "Needs Clarification",
  question: "Question",
};

const classificationColors: Record<ReplyClassification, string> = {
  interested: "bg-success/10 text-success border-success/20",
  not_interested: "bg-destructive/10 text-destructive border-destructive/20",
  needs_clarification: "bg-warning/10 text-warning border-warning/20",
  question: "bg-info/10 text-info border-info/20",
};

export function MessageBubble({
  content,
  direction,
  timestamp,
  status = "delivered",
  classification,
  suggestedReply,
  requiresHRReview,
  className,
}: MessageBubbleProps) {
  const isOutgoing = direction === "outgoing";
  const StatusIcon = statusIcons[status];
  const formattedTime = new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={cn(
        "flex flex-col max-w-[85%] gap-1",
        isOutgoing ? "ml-auto items-end" : "mr-auto items-start",
        className
      )}
    >
      {classification && (
        <Badge
          variant="outline"
          className={cn("text-xs mb-1", classificationColors[classification])}
        >
          {classificationLabels[classification]}
        </Badge>
      )}
      {requiresHRReview && !isOutgoing && (
        <Badge
          variant="outline"
          className="text-xs mb-1 bg-warning/10 text-warning border-warning/20 flex items-center gap-1"
        >
          <AlertTriangle className="h-3 w-3" />
          HR review required
        </Badge>
      )}
      <div
        className={cn(
          "rounded-2xl px-4 py-2.5 text-sm",
          isOutgoing
            ? "bg-primary text-primary-foreground rounded-br-md"
            : "bg-muted text-foreground rounded-bl-md"
        )}
      >
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
      <div className="flex items-center gap-1.5 px-1">
        <span className="text-xs text-muted-foreground">{formattedTime}</span>
        {isOutgoing && (
          <StatusIcon
            className={cn(
              "h-3.5 w-3.5",
              status === "failed" ? "text-destructive" : "text-muted-foreground"
            )}
          />
        )}
      </div>
      {suggestedReply && !requiresHRReview && (
        <div className="mt-2 p-3 bg-muted/50 rounded-lg border border-dashed">
          <p className="text-xs font-medium text-muted-foreground mb-1">
            Suggested Reply
          </p>
          <p className="text-sm text-foreground">{suggestedReply}</p>
        </div>
      )}
    </div>
  );
}
