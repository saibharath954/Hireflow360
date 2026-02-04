/**
 * Updated Jobs Context
 * Manages real-time job updates from backend
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { Job } from "@/types";
import { api } from "@/services/api";

interface JobsContextType {
  jobs: Job[];
  isLoading: boolean;
  pendingCount: number;
  refreshJobs: () => Promise<void>;
  getJobById: (id: string) => Job | undefined;
  retryJob: (id: string) => Promise<void>;
  cancelJob: (id: string) => Promise<void>;
}

const JobsContext = createContext<JobsContextType | undefined>(undefined);

// Polling interval in milliseconds
// const POLL_INTERVAL = 10000; // 10 seconds
// const ACTIVE_JOB_POLL_INTERVAL = 5000; // 5 seconds for active jobs

export function JobsProvider({ children }: { children: React.ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasActiveJobs, setHasActiveJobs] = useState(false);

  const refreshJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.jobs.getAll();
      if (response.success && response.data) {
        setJobs(response.data);
        
        // Check if there are active jobs (queued or processing)
        const activeJobs = response.data.filter(
          (j) => j.status === "queued" || j.status === "processing"
        );
        setHasActiveJobs(activeJobs.length > 0);
      } else {
        console.error("Failed to fetch jobs:", response.error);
      }
    } catch (error) {
      console.error("Error fetching jobs:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getJobById = useCallback(
    (id: string) => {
      return jobs.find((j) => j.id === id);
    },
    [jobs]
  );

  const retryJob = useCallback(async (id: string) => {
    try {
      const response = await api.jobs.retry(id);
      if (response.success) {
        await refreshJobs();
      } else {
        throw new Error(response.error || "Failed to retry job");
      }
    } catch (error) {
      console.error("Error retrying job:", error);
      throw error;
    }
  }, [refreshJobs]);

  const cancelJob = useCallback(async (id: string) => {
    try {
      const response = await api.jobs.cancel(id);
      if (response.success) {
        await refreshJobs();
      } else {
        throw new Error(response.error || "Failed to cancel job");
      }
    } catch (error) {
      console.error("Error cancelling job:", error);
      throw error;
    }
  }, [refreshJobs]);

  // Poll for job updates
  useEffect(() => {
    refreshJobs();
  }, []);

  const pendingCount = jobs.filter(
    (j) => j.status === "queued" || j.status === "processing"
  ).length;

  return (
    <JobsContext.Provider
      value={{
        jobs,
        isLoading,
        pendingCount,
        refreshJobs,
        getJobById,
        retryJob,
        cancelJob,
      }}
    >
      {children}
    </JobsContext.Provider>
  );
}

export function useJobsContext() {
  const context = useContext(JobsContext);
  if (context === undefined) {
    throw new Error("useJobsContext must be used within a JobsProvider");
  }
  return context;
}