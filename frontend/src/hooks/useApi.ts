/**
 * useApi Hook
 * Provides typed access to all mock API endpoints
 */

import { useState, useCallback } from "react";
import {
  mockCandidatesApi,
  mockResumeApi,
  mockMessagingApi,
  mockJobsApi,
  mockExportApi,
  mockDashboardApi,
} from "@/services/mockApi";
import type {
  Candidate,
  CandidateFilters,
  Message,
  Job,
  DashboardStats,
  ActivityItem,
  CandidateFieldKey,
} from "@/types";

interface UseApiReturn {
  // State
  isLoading: boolean;
  error: string | null;
  
  // Candidates
  getCandidates: (filters?: CandidateFilters) => Promise<Candidate[]>;
  getCandidate: (id: string) => Promise<Candidate | null>;
  updateCandidate: (id: string, updates: Partial<Candidate>) => Promise<Candidate | null>;
  
  // Resume
  uploadResume: (file: File | string) => Promise<{ resumeId: string; candidateId: string; jobId: string } | null>;
  reprocessResume: (resumeId: string) => Promise<{ jobId: string } | null>;
  
  // Messaging
  generateMessagePreview: (intent: string, candidateId: string, pendingFields?: CandidateFieldKey[]) => Promise<{ content: string; askedFields?: CandidateFieldKey[] } | null>;
  sendMessage: (candidateId: string, content: string, mode: "mock" | "automation", askedFields?: CandidateFieldKey[]) => Promise<Message | null>;
  simulateReply: (candidateId: string, replyText: string) => Promise<Message | null>;
  approveAndSendMessage: (candidateId: string, messageId: string, content: string) => Promise<Message | null>;
  
  // Jobs
  getJobs: () => Promise<Job[]>;
  getJob: (id: string) => Promise<Job | null>;
  
  // Export
  exportToExcel: (candidateIds?: string[]) => Promise<Blob | null>;
  syncGoogleSheets: () => Promise<{ syncedAt: string; rowCount: number } | null>;
  
  // Dashboard
  getDashboardStats: () => Promise<DashboardStats | null>;
  getRecentActivity: () => Promise<ActivityItem[]>;
}

export function useApi(): UseApiReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRequest = useCallback(async <T>(
    request: () => Promise<T>
  ): Promise<T | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await request();
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Candidates
  const getCandidates = useCallback(
    async (filters?: CandidateFilters) => {
      const result = await handleRequest(() => mockCandidatesApi.getAll(filters));
      return result?.items ?? [];
    },
    [handleRequest]
  );

  const getCandidate = useCallback(
    async (id: string) => {
      const result = await handleRequest(() => mockCandidatesApi.getById(id));
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  const updateCandidate = useCallback(
    async (id: string, updates: Partial<Candidate>) => {
      const result = await handleRequest(() => mockCandidatesApi.update(id, updates));
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  // Resume
  const uploadResume = useCallback(
    async (file: File | string) => {
      const result = await handleRequest(() => mockResumeApi.upload(file));
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  const reprocessResume = useCallback(
    async (resumeId: string) => {
      const result = await handleRequest(() => mockResumeApi.reprocess(resumeId));
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  // Messaging
  const generateMessagePreview = useCallback(
    async (intent: string, candidateId: string, pendingFields?: CandidateFieldKey[]) => {
      const result = await handleRequest(() =>
        mockMessagingApi.generatePreview(intent, candidateId, pendingFields)
      );
      return result?.success && result.data 
        ? { content: result.data.content, askedFields: result.data.askedFields } 
        : null;
    },
    [handleRequest]
  );

  const sendMessage = useCallback(
    async (candidateId: string, content: string, mode: "mock" | "automation", askedFields?: CandidateFieldKey[]) => {
      const result = await handleRequest(() =>
        mockMessagingApi.send(candidateId, content, mode)
      );
      // Note: askedFields would be tracked in real implementation
      // TODO: Pass askedFields to backend for conversation state tracking
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  const simulateReply = useCallback(
    async (candidateId: string, replyText: string) => {
      const result = await handleRequest(() =>
        mockMessagingApi.simulateReply(candidateId, replyText)
      );
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  const approveAndSendMessage = useCallback(
    async (candidateId: string, messageId: string, content: string) => {
      const result = await handleRequest(() =>
        mockMessagingApi.approveAndSend(candidateId, messageId, content)
      );
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  // Jobs
  const getJobs = useCallback(async () => {
    const result = await handleRequest(() => mockJobsApi.getAll());
    return result ?? [];
  }, [handleRequest]);

  const getJob = useCallback(
    async (id: string) => {
      const result = await handleRequest(() => mockJobsApi.getById(id));
      return result?.success ? result.data ?? null : null;
    },
    [handleRequest]
  );

  // Export
  const exportToExcel = useCallback(
    async (candidateIds?: string[]) => {
      return handleRequest(() => mockExportApi.exportExcel(candidateIds));
    },
    [handleRequest]
  );

  const syncGoogleSheets = useCallback(async () => {
    const result = await handleRequest(() => mockExportApi.syncGoogleSheets());
    return result?.success ? result.data ?? null : null;
  }, [handleRequest]);

  // Dashboard
  const getDashboardStats = useCallback(async () => {
    return handleRequest(() => mockDashboardApi.getStats());
  }, [handleRequest]);

  const getRecentActivity = useCallback(async () => {
    const result = await handleRequest(() => mockDashboardApi.getRecentActivity());
    return result ?? [];
  }, [handleRequest]);

  return {
    isLoading,
    error,
    getCandidates,
    getCandidate,
    updateCandidate,
    uploadResume,
    reprocessResume,
    generateMessagePreview,
    sendMessage,
    simulateReply,
    approveAndSendMessage,
    getJobs,
    getJob,
    exportToExcel,
    syncGoogleSheets,
    getDashboardStats,
    getRecentActivity,
  };
}
