/**
 * File Uploader Component
 * Drag-and-drop file upload with URL input option
 */

import { useState, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Upload, Link, X, FileText, Image, File } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/msword": [".doc"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

interface FileUploaderProps {
  onUpload: (files: File[], url?: string) => void;
  isUploading?: boolean;
  multiple?: boolean;
  className?: string;
}

interface SelectedFile {
  file: File;
  preview?: string;
}

export function FileUploader({
  onUpload,
  isUploading = false,
  multiple = true,
  className,
}: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): string | null => {
    const acceptedMimes = Object.keys(ACCEPTED_TYPES);
    if (!acceptedMimes.includes(file.type)) {
      return `File type not supported: ${file.name}`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File too large: ${file.name} (max 10MB)`;
    }
    return null;
  }, []);

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      const validFiles: SelectedFile[] = [];
      let errorMsg: string | null = null;

      for (const file of fileArray) {
        const validationError = validateFile(file);
        if (validationError) {
          errorMsg = validationError;
        } else {
          validFiles.push({ file });
        }
      }

      if (errorMsg) {
        setError(errorMsg);
      } else {
        setError(null);
      }

      if (validFiles.length > 0) {
        setSelectedFiles(multiple ? [...selectedFiles, ...validFiles] : validFiles);
      }
    },
    [multiple, selectedFiles, validateFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        handleFiles(e.target.files);
      }
    },
    [handleFiles]
  );

  const removeFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpload = useCallback(() => {
    if (selectedFiles.length > 0) {
      onUpload(selectedFiles.map((f) => f.file));
      setSelectedFiles([]);
    } else if (urlInput.trim()) {
      onUpload([], urlInput.trim());
      setUrlInput("");
      setShowUrlInput(false);
    }
  }, [selectedFiles, urlInput, onUpload]);

  const getFileIcon = (file: File) => {
    if (file.type.startsWith("image/")) return Image;
    if (file.type === "application/pdf") return FileText;
    return File;
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Drop zone */}
      <div
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50",
          isUploading && "opacity-50 pointer-events-none"
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={Object.values(ACCEPTED_TYPES).flat().join(",")}
          multiple={multiple}
          onChange={handleFileSelect}
          className="hidden"
          aria-label="Upload resume files"
        />
        <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
        <p className="text-foreground font-medium mb-1">
          Drag and drop resume files here
        </p>
        <p className="text-sm text-muted-foreground mb-4">
          PDF, DOCX, or image files up to 10MB
        </p>
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="secondary"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            Browse files
          </Button>
          <Button
            variant="ghost"
            onClick={() => setShowUrlInput(!showUrlInput)}
            disabled={isUploading}
          >
            <Link className="h-4 w-4 mr-2" />
            Add URL
          </Button>
        </div>
      </div>

      {/* URL input */}
      {showUrlInput && (
        <div className="flex gap-2">
          <Input
            type="url"
            placeholder="Enter resume URL (e.g., LinkedIn, portfolio)"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            className="flex-1"
          />
          <Button
            variant="outline"
            size="icon"
            onClick={() => setShowUrlInput(false)}
            aria-label="Close URL input"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {/* Selected files */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Selected files:</p>
          {selectedFiles.map((item, index) => {
            const Icon = getFileIcon(item.file);
            return (
              <div
                key={index}
                className="flex items-center gap-3 p-3 bg-muted rounded-lg"
              >
                <Icon className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{item.file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(item.file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFile(index)}
                  aria-label={`Remove ${item.file.name}`}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload button */}
      {(selectedFiles.length > 0 || urlInput.trim()) && (
        <Button
          onClick={handleUpload}
          disabled={isUploading}
          className="w-full"
        >
          {isUploading ? "Uploading..." : "Upload and Parse"}
        </Button>
      )}
    </div>
  );
}
