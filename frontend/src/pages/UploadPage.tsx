/**
 * Advanced Resume Upload Component with drag-drop, URL input, and batch processing
 */

import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Upload, 
  Link, 
  FileText, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/useApi';
import type { ResumeUploadResult } from '@/types/index';

interface UploadFileInfo {
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: ResumeUploadResult;
  error?: string;
}

const UploadPage: React.FC = () => {
  const [files, setFiles] = useState<UploadFileInfo[]>([]);
  const [url, setUrl] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('upload');
  const [batchProgress, setBatchProgress] = useState(0);
  
  const { toast } = useToast();
  const { uploadResume } = useApi();
  
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFileInfo[] = acceptedFiles.map(file => ({
      file,
      status: 'pending',
      progress: 0
    }));
    
    setFiles(prev => [...prev, ...newFiles]);
    
    toast({
      title: 'Files added',
      description: `Added ${acceptedFiles.length} file(s) to upload queue`,
    });
  }, [toast]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'text/plain': ['.txt']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  });
  
  const handleUpload = async () => {
    if (files.length === 0) {
      toast({
        title: 'No files selected',
        description: 'Please add files to upload',
        variant: 'destructive'
      });
      return;
    }
    
    setIsUploading(true);
    setBatchProgress(0);
    
    const successfulUploads: ResumeUploadResult[] = [];
    const failedUploads: { file: string; error: string }[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const fileInfo = files[i];
      
      // Skip already completed or failed files
      if (fileInfo.status === 'completed' || fileInfo.status === 'failed') {
        continue;
      }
      
      // Update file status
      setFiles(prev => prev.map((f, idx) => 
        idx === i ? { ...f, status: 'uploading', progress: 10 } : f
      ));
      
      try {
        const result = await uploadResume(fileInfo.file);
        
        if (result) {
          successfulUploads.push(result);
          
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { 
              ...f, 
              status: 'processing', 
              progress: 50,
              result 
            } : f
          ));
          
          // Simulate processing progress
          const interval = setInterval(() => {
            setFiles(prev => prev.map((f, idx) => {
              if (idx === i && f.status === 'processing' && f.progress < 90) {
                return { ...f, progress: f.progress + 10 };
              }
              return f;
            }));
          }, 500);
          
          // Wait for processing simulation
          await new Promise(resolve => setTimeout(resolve, 3000));
          clearInterval(interval);
          
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { 
              ...f, 
              status: 'completed', 
              progress: 100 
            } : f
          ));
        } else {
          throw new Error('Upload failed');
        }
        
      } catch (error) {
        failedUploads.push({
          file: fileInfo.file.name,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        
        setFiles(prev => prev.map((f, idx) => 
          idx === i ? { 
            ...f, 
            status: 'failed', 
            error: error instanceof Error ? error.message : 'Upload failed'
          } : f
        ));
      }
      
      // Update batch progress
      setBatchProgress(((i + 1) / files.length) * 100);
    }
    
    setIsUploading(false);
    
    // Show summary toast
    toast({
      title: 'Batch upload complete',
      description: `Success: ${successfulUploads.length}, Failed: ${failedUploads.length}`,
      variant: successfulUploads.length > 0 ? 'default' : 'destructive'
    });
  };
  
  const handleUrlUpload = async () => {
    if (!url.trim()) {
      toast({
        title: 'URL required',
        description: 'Please enter a resume URL',
        variant: 'destructive'
      });
      return;
    }
    
    setIsUploading(true);
    
    try {
      // Fetch the resume from URL and upload as a file
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch URL');
      }
      const blob = await response.blob();
      const filename = url.split('/').pop() || 'resume.pdf';
      const file = new File([blob], filename, { type: blob.type });
      
      const result = await uploadResume(file);
      
      if (result) {
        toast({
          title: 'URL submitted',
          description: 'Resume will be processed shortly',
        });
        
        setUrl('');
        setActiveTab('upload');
      }
    } catch (error) {
      toast({
        title: 'Upload failed',
        description: error instanceof Error ? error.message : 'Failed to upload from URL',
        variant: 'destructive'
      });
    } finally {
      setIsUploading(false);
    }
  };
  
  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };
  
  const clearAll = () => {
    setFiles([]);
  };
  
  const getStatusIcon = (status: UploadFileInfo['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'uploading':
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };
  
  const getStatusColor = (status: UploadFileInfo['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'uploading':
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="upload">
            <Upload className="h-4 w-4 mr-2" />
            File Upload
          </TabsTrigger>
          <TabsTrigger value="url">
            <Link className="h-4 w-4 mr-2" />
            URL Import
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Drag & Drop Resumes</CardTitle>
              <CardDescription>
                Supported formats: PDF, DOCX, DOC, Images (JPG, PNG), TXT
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-lg font-medium mb-2">
                  {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  or click to browse files
                </p>
                <Button variant="outline">
                  Select Files
                </Button>
              </div>
              
              {files.length > 0 && (
                <div className="mt-6">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-medium">
                      Upload Queue ({files.length} files)
                    </h3>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={clearAll}
                      disabled={isUploading}
                    >
                      Clear All
                    </Button>
                  </div>
                  
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {files.map((fileInfo, index) => (
                      <div
                        key={`${fileInfo.file.name}-${index}`}
                        className="border rounded-lg p-4"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            {getStatusIcon(fileInfo.status)}
                            <div className="min-w-0">
                              <p className="font-medium truncate">
                                {fileInfo.file.name}
                              </p>
                              <p className="text-sm text-gray-500">
                                {(fileInfo.file.size / 1024 / 1024).toFixed(2)} MB
                              </p>
                            </div>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <Badge className={getStatusColor(fileInfo.status)}>
                              {fileInfo.status}
                            </Badge>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeFile(index)}
                              disabled={isUploading && fileInfo.status !== 'pending'}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        
                        <Progress value={fileInfo.progress} className="h-2" />
                        
                        {fileInfo.error && (
                          <div className="mt-2 p-2 bg-red-50 rounded-md">
                            <div className="flex items-center text-red-700">
                              <AlertCircle className="h-4 w-4 mr-2" />
                              <span className="text-sm">{fileInfo.error}</span>
                            </div>
                          </div>
                        )}
                        
                        {fileInfo.result && (
                          <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-gray-500">Candidate:</span>{' '}
                              <span className="font-medium">
                                {fileInfo.result.candidateName || 'Processing...'}
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-500">Job ID:</span>{' '}
                              <span className="font-mono text-xs">
                                {fileInfo.result.jobId?.substring(0, 8)}...
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {batchProgress > 0 && batchProgress < 100 && (
                    <div className="mt-4">
                      <div className="flex justify-between text-sm mb-1">
                        <span>Batch Progress</span>
                        <span>{Math.round(batchProgress)}%</span>
                      </div>
                      <Progress value={batchProgress} className="h-2" />
                    </div>
                  )}
                  
                  <Button
                    onClick={handleUpload}
                    disabled={isUploading || files.length === 0}
                    className="w-full mt-6"
                  >
                    {isUploading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload className="h-4 w-4 mr-2" />
                        Upload {files.length} File{files.length !== 1 ? 's' : ''}
                      </>
                    )}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="url" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Import from URL</CardTitle>
              <CardDescription>
                Enter a public URL to a resume (PDF, DOCX, or image)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Input
                    type="url"
                    placeholder="https://example.com/resume.pdf"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="w-full"
                  />
                  <p className="text-sm text-gray-500 mt-2">
                    Supported: Google Drive, Dropbox, public URLs
                  </p>
                </div>
                
                <Button
                  onClick={handleUrlUpload}
                  disabled={isUploading || !url.trim()}
                  className="w-full"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Import from URL
                    </>
                  )}
                </Button>
                
                <div className="p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-start">
                    <AlertCircle className="h-5 w-5 text-blue-500 mr-2 mt-0.5" />
                    <div className="text-sm text-blue-700">
                      <p className="font-medium mb-1">Tips for URL import:</p>
                      <ul className="list-disc pl-4 space-y-1">
                        <li>Ensure the URL is publicly accessible</li>
                        <li>PDF and DOCX files work best</li>
                        <li>Google Drive links should be shared as "Anyone with link can view"</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default UploadPage;