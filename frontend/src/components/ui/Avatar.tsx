/**
 * Avatar Component
 * Displays user avatar with initials fallback
 */

import { cn } from "@/lib/utils";

interface AvatarProps {
  name: string;
  src?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeClasses = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function getAvatarColor(name: string): string {
  // Generate consistent color based on name
  const colors = [
    "bg-primary",
    "bg-info",
    "bg-success",
    "bg-warning",
    "bg-destructive",
  ];
  const index = name.charCodeAt(0) % colors.length;
  return colors[index];
}

export function Avatar({ name, src, size = "md", className }: AvatarProps) {
  const initials = getInitials(name);
  const colorClass = getAvatarColor(name);

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        className={cn(
          "rounded-full object-cover",
          sizeClasses[size],
          className
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        "rounded-full flex items-center justify-center font-medium text-primary-foreground",
        sizeClasses[size],
        colorClass,
        className
      )}
      aria-label={name}
    >
      {initials}
    </div>
  );
}
