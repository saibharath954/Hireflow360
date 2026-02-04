/**
 * Updated useJobs Hook
 * Provides job management functionality
 */

import { useCallback } from "react";
import { useToastContext } from "@/contexts/ToastContext";
import { api } from "@/services/api";
import type { Job } from "@/types";

export function useJobs() {
  const toast = useToastContext();

  const getJobs = useCallback(async (filters?: {
    type?: string;
    status?: string;
    candidateId?: string;
  }) => {
    try {
      const response = await api.jobs.getAll(filters);
      if (response.success && response.data) {
        return response.data;
      } else {
        toast.error("Failed to load jobs", response.error || "Unknown error");
        return [];
      }
    } catch (error) {
      toast.error("Network Error", "Failed to load jobs. Please check your connection.");
      return [];
    }
  }, [toast]);

  const getJob = useCallback(async (id: string) => {
    try {
      const response = await api.jobs.getById(id);
      if (response.success && response.data) {
        return response.data;
      } else {
        toast.error("Job not found", response.error || "Unknown error");
        return null;
      }
    } catch (error) {
      toast.error("Network Error", "Failed to load job details.");
      return null;
    }
  }, [toast]);

  const retryJob = useCallback(async (id: string) => {
    try {
      const response = await api.jobs.retry(id);
      if (response.success) {
        toast.success("Job Retried", "The job has been queued for retry.");
        return true;
      } else {
        toast.error("Retry Failed", response.error || "Failed to retry job");
        return false;
      }
    } catch (error) {
      toast.error("Network Error", "Failed to retry job. Please try again.");
      return false;
    }
  }, [toast]);

  const cancelJob = useCallback(async (id: string) => {
    try {
      const response = await api.jobs.cancel(id);
      if (response.success) {
        toast.success("Job Cancelled", "The job has been cancelled.");
        return true;
      } else {
        toast.error("Cancel Failed", response.error || "Failed to cancel job");
        return false;
      }
    } catch (error) {
      toast.error("Network Error", "Failed to cancel job. Please try again.");
      return false;
    }
  }, [toast]);

  const getJobStats = useCallback(async (days = 7) => {
    try {
      const response = await api.jobs.getStats(days);
      if (response.success && response.data) {
        return response.data;
      } else {
        console.error("Failed to get job stats:", response.error);
        return null;
      }
    } catch (error) {
      console.error("Error getting job stats:", error);
      return null;
    }
  }, []);

  return {
    getJobs,
    getJob,
    retryJob,
    cancelJob,
    getJobStats,
  };
}