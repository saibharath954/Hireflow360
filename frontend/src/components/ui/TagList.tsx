/**
 * Tag List Component
 * Displays a list of tags (e.g., skills) with optional limit
 */

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface TagListProps {
  tags: string[];
  limit?: number;
  size?: "sm" | "md";
  className?: string;
  onTagClick?: (tag: string) => void;
}

export function TagList({
  tags,
  limit = 5,
  size = "sm",
  className,
  onTagClick,
}: TagListProps) {
  const visibleTags = limit ? tags.slice(0, limit) : tags;
  const remainingCount = tags.length - visibleTags.length;

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {visibleTags.map((tag) => (
        <Badge
          key={tag}
          variant="secondary"
          className={cn(
            "font-normal",
            size === "sm" && "text-xs px-1.5 py-0",
            onTagClick && "cursor-pointer hover:bg-secondary/80"
          )}
          onClick={onTagClick ? () => onTagClick(tag) : undefined}
        >
          {tag}
        </Badge>
      ))}
      {remainingCount > 0 && (
        <Badge
          variant="outline"
          className={cn(
            "font-normal text-muted-foreground",
            size === "sm" && "text-xs px-1.5 py-0"
          )}
        >
          +{remainingCount}
        </Badge>
      )}
    </div>
  );
}
