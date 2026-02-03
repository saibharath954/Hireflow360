/**
 * HR Review Panel Component
 * Shows messages requiring HR approval with AI suggested replies
 */

import { useState } from "react";
import { AlertTriangle, CheckCircle, Edit2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Message } from "@/types";

interface HRReviewPanelProps {
  message: Message;
  onApprove: (messageId: string, content: string) => Promise<void>;
  isApproving?: boolean;
  className?: string;
}

export function HRReviewPanel({
  message,
  onApprove,
  isApproving = false,
  className,
}: HRReviewPanelProps) {
  const [editedReply, setEditedReply] = useState(message.aiSuggestedReply || "");
  const [isEditing, setIsEditing] = useState(false);

  const handleApprove = async () => {
    await onApprove(message.id, editedReply);
  };

  if (message.hrApproved) {
    return (
      <div
        className={cn(
          "p-4 rounded-lg border border-success/20 bg-success/5",
          className
        )}
      >
        <div className="flex items-center gap-2 text-success">
          <CheckCircle className="h-4 w-4" />
          <span className="text-sm font-medium">Approved and sent</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "p-4 rounded-lg border border-warning/30 bg-warning/5 space-y-4",
        className
      )}
    >
      {/* Warning header */}
      <div className="flex items-start gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-warning/10 border border-warning/20">
          <AlertTriangle className="h-4 w-4 text-warning" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">HR Review Required</span>
            <Badge
              variant="outline"
              className="text-xs bg-warning/10 text-warning border-warning/20"
            >
              Question detected
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            The candidate asked a question that requires your review before
            responding.
          </p>
        </div>
      </div>

      {/* Candidate's question */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Candidate's Question
        </p>
        <div className="p-3 bg-muted rounded-lg">
          <p className="text-sm">{message.content}</p>
        </div>
      </div>

      {/* AI Suggested Reply */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            AI-Suggested Reply
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setIsEditing(!isEditing)}
          >
            <Edit2 className="h-3 w-3 mr-1" />
            {isEditing ? "Preview" : "Edit"}
          </Button>
        </div>

        {isEditing ? (
          <Textarea
            value={editedReply}
            onChange={(e) => setEditedReply(e.target.value)}
            rows={4}
            className="text-sm"
            placeholder="Edit the suggested reply..."
          />
        ) : (
          <div className="p-3 bg-primary/5 rounded-lg border border-primary/10">
            <p className="text-sm whitespace-pre-wrap">{editedReply}</p>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-2">
        <Button
          onClick={handleApprove}
          disabled={isApproving || !editedReply.trim()}
          className="flex-1"
        >
          {isApproving ? (
            <>
              <span className="animate-spin mr-2">⏳</span>
              Sending...
            </>
          ) : (
            <>
              <Send className="h-4 w-4 mr-2" />
              Approve & Send
            </>
          )}
        </Button>
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-muted-foreground text-center">
        ⚠️ No message will be sent until you approve
      </p>
    </div>
  );
}
