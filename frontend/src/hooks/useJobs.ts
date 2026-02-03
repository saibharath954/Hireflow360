/**
 * useJobs Hook
 * Provides job management and status tracking
 */

import { useJobsContext } from "@/contexts/JobsContext";
import type { Job } from "@/types";
import type { JobStatus, JobType } from "@/styles/design-tokens";

interface UseJobsReturn {
  jobs: Job[];
  isLoading: boolean;
  pendingCount: number;
  refreshJobs: () => Promise<void>;
  getJobById: (id: string) => Job | undefined;
  getJobsByType: (type: JobType) => Job[];
  getJobsByStatus: (status: JobStatus) => Job[];
  getJobsForCandidate: (candidateId: string) => Job[];
}

export function useJobs(): UseJobsReturn {
  const { jobs, isLoading, pendingCount, refreshJobs, getJobById } = useJobsContext();

  const getJobsByType = (type: JobType): Job[] => {
    return jobs.filter((j) => j.type === type);
  };

  const getJobsByStatus = (status: JobStatus): Job[] => {
    return jobs.filter((j) => j.status === status);
  };

  const getJobsForCandidate = (candidateId: string): Job[] => {
    return jobs.filter((j) => j.candidateId === candidateId);
  };

  return {
    jobs,
    isLoading,
    pendingCount,
    refreshJobs,
    getJobById,
    getJobsByType,
    getJobsByStatus,
    getJobsForCandidate,
  };
}
