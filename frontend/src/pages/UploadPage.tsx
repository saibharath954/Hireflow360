/**
 * Upload Page - Resume upload with drag-and-drop
 */
import { useState } from "react";
import { FileUploader } from "@/components/ui/FileUploader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/hooks/useApi";
import { useToastContext } from "@/contexts/ToastContext";

export default function UploadPage() {
  const [isUploading, setIsUploading] = useState(false);
  const { uploadResume } = useApi();
  const toast = useToastContext();

  const handleUpload = async (files: File[], url?: string) => {
    setIsUploading(true);
    try {
      if (url) {
        const result = await uploadResume(files[0], url);
        if (result) {
          toast.success("URL submitted", "Resume will be parsed shortly");
        }
      } else {
        const uploadPromises = files.map(file => uploadResume(file));
        const results = await Promise.allSettled(uploadPromises);
        
        const successfulUploads = results.filter(result => result.status === 'fulfilled').length;
        
        if (successfulUploads > 0) {
          toast.success("Upload complete", `${successfulUploads} resume(s) queued for parsing`);
        }
        
        if (successfulUploads < files.length) {
          toast.warning("Partial upload", `${files.length - successfulUploads} file(s) failed to upload`);
        }
      }
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Upload failed", "Please try again");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-bold">Upload Resumes</h1><p className="text-muted-foreground">Add candidates to your pipeline</p></div>
      <Card>
        <CardHeader><CardTitle>Resume Upload</CardTitle><CardDescription>PDF, DOCX, or image files</CardDescription></CardHeader>
        <CardContent><FileUploader onUpload={handleUpload} isUploading={isUploading} /></CardContent>
      </Card>
    </div>
  );
}