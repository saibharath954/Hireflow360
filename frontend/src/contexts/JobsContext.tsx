/**
 * Jobs Context
 * Manages background job polling and status updates
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { Job } from "@/types";
import { mockJobsApi } from "@/services/mockApi";

interface JobsContextType {
  jobs: Job[];
  isLoading: boolean;
  pendingCount: number;
  refreshJobs: () => Promise<void>;
  getJobById: (id: string) => Job | undefined;
}

const JobsContext = createContext<JobsContextType | undefined>(undefined);

const POLL_INTERVAL = 5000; // 5 seconds

export function JobsProvider({ children }: { children: React.ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const refreshJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const fetchedJobs = await mockJobsApi.getAll();
      setJobs(fetchedJobs);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
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

  // Poll for job updates
  useEffect(() => {
    refreshJobs();
    const interval = setInterval(refreshJobs, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refreshJobs]);

  const pendingCount = jobs.filter(
    (j) => j.status === "queued" || j.status === "processing"
  ).length;

  return (
    <JobsContext.Provider
      value={{ jobs, isLoading, pendingCount, refreshJobs, getJobById }}
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
