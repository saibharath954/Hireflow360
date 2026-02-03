/**
 * Custom Toast Component
 * Displays toast notifications from ToastContext
 */

import { cn } from "@/lib/utils";
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { useToastContext, type ToastType } from "@/contexts/ToastContext";

const iconMap: Record<ToastType, React.ComponentType<{ className?: string }>> = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const colorMap: Record<ToastType, string> = {
  success: "border-success/30 bg-success/10",
  error: "border-destructive/30 bg-destructive/10",
  warning: "border-warning/30 bg-warning/10",
  info: "border-info/30 bg-info/10",
};

const iconColorMap: Record<ToastType, string> = {
  success: "text-success",
  error: "text-destructive",
  warning: "text-warning",
  info: "text-info",
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastContext();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const Icon = iconMap[toast.type];
        return (
          <div
            key={toast.id}
            className={cn(
              "flex items-start gap-3 p-4 rounded-lg border shadow-elevated animate-slide-in-from-bottom bg-card",
              colorMap[toast.type]
            )}
            role="alert"
          >
            <Icon className={cn("h-5 w-5 flex-shrink-0 mt-0.5", iconColorMap[toast.type])} />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground">{toast.title}</p>
              {toast.description && (
                <p className="text-sm text-muted-foreground mt-0.5">
                  {toast.description}
                </p>
              )}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="flex-shrink-0 p-1 rounded hover:bg-muted transition-colors"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
