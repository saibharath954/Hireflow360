/**
 * Updated useApi Hook
 * Provides real API calls with error handling
 */

import { useCallback, useMemo } from "react";
import { useToastContext } from "@/contexts/ToastContext";
import { api } from "@/services/api";
import type {
  Candidate,
  CandidateFilters,
  Message,
  MessagePreview,
  Job,
  DashboardStats,
  ActivityItem,
  AppSettings,
  PaginatedResponse,
  ApiResponse,
  Resume,
} from "@/types";

export function useApi() {
  const toast = useToastContext();

  // Helper to handle API errors
  const handleApiError = useCallback(
    (error: string, defaultMessage: string) => {
      console.error("API Error:", error);
      toast.error("API Error", error || defaultMessage);
      return null;
    },
    [toast]
  );

  // Helper to handle success messages
  const handleSuccess = useCallback(
    (message: string, title: string = "Success") => {
      toast.success(title, message);
    },
    [toast]
  );

  // Candidates
  const getCandidates = useCallback(
    async (filters?: CandidateFilters, page = 1, pageSize = 50) => {
      try {
        const response = await api.candidates.getAll(filters, page, pageSize);
        if (response.success && response.data) {
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to load candidates") || { items: [], total: 0, page, pageSize, hasMore: false };
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to load candidates"
        ) || { items: [], total: 0, page, pageSize, hasMore: false };
      }
    },
    [handleApiError]
  );

  const getCandidate = useCallback(
    async (id: string) => {
      try {
        const response = await api.candidates.getById(id);
        if (response.success && response.data) {
          return response.data;
        } else {
          return handleApiError(response.error, "Candidate not found");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to load candidate"
        );
      }
    },
    [handleApiError]
  );

  const updateCandidate = useCallback(
    async (id: string, updates: Partial<Candidate>) => {
      try {
        const response = await api.candidates.update(id, updates);
        if (response.success && response.data) {
          handleSuccess("Candidate updated successfully");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to update candidate");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to update candidate"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  const createCandidate = useCallback(
    async (candidateData: Partial<Candidate>) => {
      try {
        const response = await api.candidates.create(candidateData);
        if (response.success && response.data) {
          handleSuccess("Candidate created successfully");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to create candidate");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to create candidate"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  const deleteCandidate = useCallback(
    async (id: string) => {
      try {
        const response = await api.candidates.delete(id);
        if (response.success) {
          handleSuccess("Candidate deleted successfully");
          return true;
        } else {
          return handleApiError(response.error, "Failed to delete candidate") || false;
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to delete candidate"
        ) || false;
      }
    },
    [handleApiError, handleSuccess]
  );

  // Resumes
  const uploadResume = useCallback(
    async (file: File, url?: string) => {
      try {
        const response = await api.resumes.upload(file, url);
        if (response.success && response.data) {
          handleSuccess("Resume uploaded successfully. Processing started.");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to upload resume");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to upload resume"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  const getResume = useCallback(
    async (resumeId: string) => {
      try {
        const response = await api.resumes.getById(resumeId);
        if (response.success && response.data) {
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to load resume");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to load resume"
        );
      }
    },
    [handleApiError]
  );

  const reprocessResume = useCallback(
    async (resumeId: string) => {
      try {
        const response = await api.resumes.reprocess(resumeId);
        if (response.success && response.data) {
          handleSuccess("Resume reprocessing started");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to reprocess resume");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to reprocess resume"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  const deleteResume = useCallback(
    async (resumeId: string) => {
      try {
        const response = await api.resumes.delete(resumeId);
        if (response.success) {
          handleSuccess("Resume deleted successfully");
          return true;
        } else {
          return handleApiError(response.error, "Failed to delete resume") || false;
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to delete resume"
        ) || false;
      }
    },
    [handleApiError, handleSuccess]
  );

  // Messaging
  const generateMessagePreview = useCallback(
    async (intent: string, candidateId: string, pendingFields?: string[]) => {
      try {
        const response = await api.messaging.generatePreview(intent, candidateId, pendingFields);
        if (response.success && response.data) {
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to generate message preview");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to generate message"
        );
      }
    },
    [handleApiError]
  );

  const sendMessage = useCallback(
    async (candidateId: string, content: string, mode: "mock" | "automation" = "mock", askedFields?: string[]) => {
      try {
        const response = await api.messaging.send(candidateId, content, mode, askedFields);
        if (response.success && response.data) {
          handleSuccess("Message sent successfully");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to send message");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to send message"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  const simulateReply = useCallback(
    async (candidateId: string, content: string) => {
      try {
        const response = await api.messaging.receiveReply(candidateId, content);
        if (response.success && response.data) {
          handleSuccess("Reply simulated successfully");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to simulate reply");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to simulate reply"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  const approveAndSendMessage = useCallback(
    async (messageId: string, content: string) => {
      try {
        const response = await api.messaging.approveAndSend(messageId, content);
        if (response.success && response.data) {
          handleSuccess("Message approved and sent");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to approve and send message");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to approve message"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  const getConversation = useCallback(
    async (candidateId: string, limit = 50) => {
      try {
        const response = await api.messaging.getConversation(candidateId, limit);
        if (response.success && response.data) {
          return response.data;
        }
        return [];
      } catch (error) {
        console.error('Failed to fetch conversation:', error);
        return [];
      }
    },
    [] // Empty dependency array - function never changes
  );

  const getPendingReviews = useCallback(
    async (limit = 20) => {
      try {
        const response = await api.messaging.getPendingReviews(limit);
        if (response.success && response.data) {
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to load pending reviews") || [];
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to load pending reviews"
        ) || [];
      }
    },
    [handleApiError]
  );

  // Dashboard
  const getDashboardStats = useCallback(async () => {
    try {
      const response = await api.dashboard.getStats();
      if (response.success && response.data) {
        return response.data;
      } else {
        return handleApiError(response.error, "Failed to load dashboard stats");
      }
    } catch (error) {
      return handleApiError(
        error instanceof Error ? error.message : "Network error",
        "Failed to load dashboard"
      );
    }
  }, [handleApiError]);

  const getRecentActivity = useCallback(async (limit = 10) => {
    try {
      const response = await api.dashboard.getActivity(limit);
      if (response.success && response.data) {
        return response.data;
      } else {
        return handleApiError(response.error, "Failed to load activity") || [];
      }
    } catch (error) {
      return handleApiError(
        error instanceof Error ? error.message : "Network error",
        "Failed to load activity"
      ) || [];
    }
  }, [handleApiError]);

  // Export
  const exportCandidates = useCallback(
    async (options: { format: "xlsx" | "csv"; candidateIds?: string[]; includeMessages?: boolean; fields?: string[] }) => {
      try {
        const exportOptions = {
          format: options.format,
          candidateIds: options.candidateIds,
          includeMessages: options.includeMessages || false,
          fields: options.fields || undefined,
        };
        
        if (options.format === "xlsx") {
          const blob = await api.export.exportExcel(exportOptions);
          return blob;
        } else {
          const blob = await api.export.exportCsv(exportOptions);
          return blob;
        }
      } catch (error) {
        handleApiError(
          error instanceof Error ? error.message : "Export failed",
          "Failed to export candidates"
        );
        throw error;
      }
    },
    [handleApiError]
  );

  const syncGoogleSheets = useCallback(async () => {
    try {
      const response = await api.export.syncGoogleSheets();
      if (response.success && response.data) {
        handleSuccess(`Synced ${response.data.rowCount} candidates to Google Sheets`);
        return response.data;
      } else {
        return handleApiError(response.error, "Failed to sync to Google Sheets");
      }
    } catch (error) {
      return handleApiError(
        error instanceof Error ? error.message : "Network error",
        "Failed to sync to Google Sheets"
      );
    }
  }, [handleApiError, handleSuccess]);

  // Settings
  const getSettings = useCallback(async () => {
    try {
      const response = await api.settings.get();
      if (response.success && response.data) {
        return response.data;
      } else {
        return handleApiError(response.error, "Failed to load settings");
      }
    } catch (error) {
      return handleApiError(
        error instanceof Error ? error.message : "Network error",
        "Failed to load settings"
      );
    }
  }, [handleApiError]);

  const updateSettings = useCallback(
    async (updates: Partial<AppSettings>) => {
      try {
        const response = await api.settings.update(updates);
        if (response.success && response.data) {
          handleSuccess("Settings updated successfully");
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to update settings");
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to update settings"
        );
      }
    },
    [handleApiError, handleSuccess]
  );

  // Jobs
  const getJobs = useCallback(
    async (filters?: { type?: string; status?: string; candidateId?: string }) => {
      try {
        const response = await api.jobs.getAll(filters);
        if (response.success && response.data) {
          return response.data;
        } else {
          return handleApiError(response.error, "Failed to load jobs") || [];
        }
      } catch (error) {
        return handleApiError(
          error instanceof Error ? error.message : "Network error",
          "Failed to load jobs"
        ) || [];
      }
    },
    [handleApiError]
  );

  // FINAL RETURN: Wrap in useMemo
  return useMemo(() => ({
    // Candidates
    getCandidates,
    getCandidate,
    updateCandidate,
    createCandidate,
    deleteCandidate,
    
    // Resumes
    uploadResume,
    getResume,
    reprocessResume,
    deleteResume,
    
    // Messaging
    generateMessagePreview,
    sendMessage,
    simulateReply,
    approveAndSendMessage,
    getConversation,
    getPendingReviews,
    
    // Dashboard
    getDashboardStats,
    getRecentActivity,
    
    // Export
    exportCandidates,
    syncGoogleSheets,
    
    // Settings
    getSettings,
    updateSettings,
    
    // Jobs
    getJobs,
  }), [
    // List all dependencies here (basically all the functions above)
    getCandidates, getCandidate, updateCandidate, createCandidate, deleteCandidate,
    uploadResume, getResume, reprocessResume, deleteResume,
    generateMessagePreview, sendMessage, simulateReply, approveAndSendMessage, getConversation, getPendingReviews,
    getDashboardStats, getRecentActivity,
    exportCandidates, syncGoogleSheets,
    getSettings, updateSettings,
    getJobs
  ]);
}