/**
 * Reprocess Resume Button Component
 * Allows admins to reprocess a candidate's resume
 */

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useAuth } from "@/contexts/AuthContext";

interface ReprocessResumeButtonProps {
  resumeId: string;
  onReprocess: (resumeId: string) => Promise<void>;
  isReprocessing?: boolean;
  className?: string;
}

export function ReprocessResumeButton({
  resumeId,
  onReprocess,
  isReprocessing = false,
  className,
}: ReprocessResumeButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const { user } = useAuth();

  // Only show for ADMIN users
  if (user?.role !== "ADMIN") {
    return null;
  }

  const handleConfirm = async () => {
    setShowConfirm(false);
    await onReprocess(resumeId);
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowConfirm(true)}
        disabled={isReprocessing}
        className={className}
      >
        <RefreshCw
          className={`h-4 w-4 mr-2 ${isReprocessing ? "animate-spin" : ""}`}
        />
        {isReprocessing ? "Reprocessing..." : "Reprocess Resume"}
      </Button>

      <ConfirmDialog
        open={showConfirm}
        onOpenChange={setShowConfirm}
        title="Reprocess Resume"
        description="This will re-run parsing on the uploaded resume and may update extracted fields. Previous field values with higher confidence will be preserved. Are you sure you want to continue?"
        confirmLabel="Reprocess"
        onConfirm={handleConfirm}
      />
    </>
  );
}
