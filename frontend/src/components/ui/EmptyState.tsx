/**
 * Empty State Component
 * Displays a placeholder when no data is available
 */

import { cn } from "@/lib/utils";
import { FileText, Users, MessageSquare, Inbox } from "lucide-react";

type EmptyStateType = "candidates" | "messages" | "files" | "generic";

interface EmptyStateProps {
  type?: EmptyStateType;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

const iconMap = {
  candidates: Users,
  messages: MessageSquare,
  files: FileText,
  generic: Inbox,
};

export function EmptyState({
  type = "generic",
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  const Icon = iconMap[type];

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-12 px-4 text-center",
        className
      )}
    >
      <div className="rounded-full bg-muted p-4 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground max-w-sm mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}
