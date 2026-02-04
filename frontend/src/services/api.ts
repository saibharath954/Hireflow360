/**
 * Real API Service - Replaces mockApi.ts
 * Handles all HTTP requests to the FastAPI backend
 */

import {
  API_BASE_URL,
  ApiResponse,
  PaginatedResponse,
  User,
  Candidate,
  CandidateFilters,
  Message,
  MessagePreview,
  Job,
  DashboardStats,
  ActivityItem,
  AppSettings,
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  RegisterUserRequest,
  RegisterResponse,
  PasswordResetRequestData,
  PasswordResetConfirmData,
  PasswordResetResponse,
  TokenRefreshResponse,
  ValidateTokenResponse,
  RefreshTokenRequest,
  ExportOptions,
  ReplyCreate,
  Resume
} from "@/types";
import { authService } from "./authService";

// API Configuration
const API_CONFIG = {
  timeout: 30000, // 30 seconds
  retries: 3,
  retryDelay: 1000, // 1 second
  timeoutErrorMessage: "Request timeout. Please check your connection.",
};

// Custom fetch with timeout
const fetchWithTimeout = async (
  url: string,
  options: RequestInit,
  timeout = API_CONFIG.timeout
): Promise<Response> => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
};

// Retry logic
const retryRequest = async <T>(
  fn: () => Promise<T>,
  retries = API_CONFIG.retries,
  delay = API_CONFIG.retryDelay,
  shouldRetry: (error: any) => boolean = () => true
): Promise<T> => {
  try {
    return await fn();
  } catch (error) {
    if (retries > 0 && shouldRetry(error)) {
      await new Promise((r) => setTimeout(r, delay));
      return retryRequest(fn, retries - 1, delay * 2, shouldRetry);
    }
    throw error;
  }
};


// Request wrapper
const apiRequest = async <T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> => {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = authService.getToken();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const requestFn = async () => {
    const response = await fetchWithTimeout(url, {
      ...options,
      headers,
    });
    const isRefreshEndpoint = endpoint.includes("/auth/refresh");
    // Handle 401 Unauthorized - refresh token
    if (response.status === 401) {
      if (isRefreshEndpoint) {
        authService.clear();
        throw new Error("UNAUTHORIZED");
      }

      const refreshed = await authService.refreshToken();
      if (!refreshed) {
        authService.clear();
        throw new Error("UNAUTHORIZED");
      }

      headers["Authorization"] = `Bearer ${authService.getToken()}`;
      const retryResponse = await fetchWithTimeout(url, {
        ...options,
        headers,
      });
      return handleResponse<T>(retryResponse);
    }
    return handleResponse<T>(response);
  };

  try {
    return await retryRequest(
    requestFn,
    API_CONFIG.retries,
    API_CONFIG.retryDelay,
    (error) => error.message !== "UNAUTHORIZED"
);

  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return {
        success: false,
        error: API_CONFIG.timeoutErrorMessage,
      };
    }
    return {
      success: false,
      error: error instanceof Error ? error.message : "Network error occurred",
    };
  }
};

const handleResponse = async <T>(response: Response): Promise<ApiResponse<T>> => {
  const contentType = response.headers.get("content-type");
  
  if (!contentType?.includes("application/json")) {
    if (response.ok) {
      return { success: true } as ApiResponse<T>;
    }
    return {
      success: false,
      error: `HTTP ${response.status}: ${response.statusText}`,
    };
  }

  const data = await response.json();
  
  if (!response.ok) {
    return {
      success: false,
      error: data.detail || data.error || `HTTP ${response.status}`,
      message: data.message,
    };
  }

  return {
    success: true,
    data: data.data ?? data,
    message: data.message,
  };
};

// File upload helper
const uploadFile = async (
  endpoint: string,
  file: File,
  additionalData: Record<string, string> = {}
): Promise<ApiResponse<any>> => {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = authService.getToken();
  const formData = new FormData();
  
  formData.append("file", file);
  
  Object.entries(additionalData).forEach(([key, value]) => {
    formData.append(key, value);
  });

  const headers: HeadersInit = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetchWithTimeout(url, {
      method: "POST",
      headers,
      body: formData,
    });

    return await handleResponse(response);
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Upload failed",
    };
  }
};

// ==================== Authentication ====================

export const authApi = {
  login: async (email: string, password: string): Promise<ApiResponse<LoginResponse>> => {
    const requestBody: LoginRequest = { email, password };
    
    return apiRequest<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
  },

  logout: async (): Promise<ApiResponse<LogoutResponse>> => {
    return apiRequest<LogoutResponse>("/auth/logout", {
      method: "POST",
    });
  },

  refreshToken: async (): Promise<ApiResponse<TokenRefreshResponse>> => {
    const refreshToken = authService.getRefreshToken();
    if (!refreshToken) {
      return { success: false, error: "No refresh token available" };
    }

    const requestBody: RefreshTokenRequest = { refresh_token: refreshToken };
    
    return apiRequest<TokenRefreshResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
  },

  getProfile: async (): Promise<ApiResponse<User>> => {
    return apiRequest<User>("/auth/me");
  },

  validateToken: async (): Promise<ApiResponse<ValidateTokenResponse>> => {
    return apiRequest<ValidateTokenResponse>("/auth/validate-token");
  },

  requestPasswordReset: async (email: string): Promise<ApiResponse<PasswordResetResponse>> => {
    const requestBody: PasswordResetRequestData = { email };
    
    return apiRequest<PasswordResetResponse>("/auth/password-reset-request", {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
  },

  confirmPasswordReset: async (token: string, password: string): Promise<ApiResponse<PasswordResetResponse>> => {
    const requestBody: PasswordResetConfirmData = { token, password };
    
    return apiRequest<PasswordResetResponse>("/auth/password-reset-confirm", {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
  },

  register: async (userData: RegisterUserRequest): Promise<ApiResponse<RegisterResponse>> => {
    return apiRequest<RegisterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    });
  },
};

// ==================== Candidates ====================

export const candidatesApi = {
  getAll: async (filters?: CandidateFilters, page = 1, pageSize = 50): Promise<ApiResponse<PaginatedResponse<Candidate>>> => {
    const params = new URLSearchParams({
      page: page.toString(),
      pageSize: pageSize.toString(),
    });

    if (filters?.search) params.append("search", filters.search);
    if (filters?.status?.length) params.append("status", filters.status.join(","));
    if (filters?.skills?.length) params.append("skills", filters.skills.join(","));
    if (filters?.minExperience) params.append("minExperience", filters.minExperience.toString());
    if (filters?.maxExperience) params.append("maxExperience", filters.maxExperience.toString());
    if (filters?.location) params.append("location", filters.location);
    if (filters?.dateRange) {
      params.append("dateFrom", filters.dateRange.from);
      params.append("dateTo", filters.dateRange.to);
    }

    return apiRequest<PaginatedResponse<Candidate>>(`/candidates?${params.toString()}`);
  },

  getById: async (id: string): Promise<ApiResponse<Candidate>> => {
    return apiRequest<Candidate>(`/candidates/${id}`);
  },

  update: async (id: string, updates: Partial<Candidate>): Promise<ApiResponse<Candidate>> => {
    return apiRequest<Candidate>(`/candidates/${id}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    });
  },

  create: async (candidateData: Partial<Candidate>): Promise<ApiResponse<Candidate>> => {
    return apiRequest<Candidate>("/candidates", {
      method: "POST",
      body: JSON.stringify(candidateData),
    });
  },

  delete: async (id: string): Promise<ApiResponse> => {
    return apiRequest(`/candidates/${id}`, {
      method: "DELETE",
    });
  },
};

// ==================== Resumes ====================

export const resumesApi = {
  upload: async (file: File, url?: string): Promise<ApiResponse<{ resumeId: string; candidateId: string; jobId: string }>> => {
    if (url) {
      return apiRequest<{ resumeId: string; candidateId: string; jobId: string }>("/resumes/upload", {
        method: "POST",
        body: JSON.stringify({ url, file_name: file.name }),
      });
    }

    return uploadFile("/resumes/upload", file);
  },

  reprocess: async (resumeId: string): Promise<ApiResponse<{ jobId: string }>> => {
    return apiRequest<{ jobId: string }>(`/resumes/${resumeId}/reprocess`, {
      method: "POST",
    });
  },

  getById: async (resumeId: string): Promise<ApiResponse<Resume>> => {
    return apiRequest<Resume>(`/resumes/${resumeId}`);
  },

  delete: async (resumeId: string): Promise<ApiResponse> => {
    return apiRequest(`/resumes/${resumeId}`, {
      method: "DELETE",
    });
  },
};

// ==================== Messaging ====================

export const messagingApi = {
  generatePreview: async (
    intent: string,
    candidateId: string,
    pendingFields?: string[]
  ): Promise<ApiResponse<MessagePreview>> => {
    const params = new URLSearchParams({
      intent,
      candidate_id: candidateId,
    });

    if (pendingFields?.length) {
      params.append("pending_fields", pendingFields.join(","));
    }

    return apiRequest<MessagePreview>(`/messaging/generate-preview?${params.toString()}`);
  },

  send: async (
    candidateId: string,
    content: string,
    mode: "mock" | "automation" = "mock",
    askedFields?: string[]
  ): Promise<ApiResponse<Message>> => {
    return apiRequest<Message>("/messaging/send", {
      method: "POST",
      body: JSON.stringify({
        candidate_id: candidateId,
        content,
        mode,
        asked_fields: askedFields,
      }),
    });
  },

  receiveReply: async (candidateId: string, content: string): Promise<ApiResponse<Message>> => {
    const replyData: ReplyCreate = {
      candidate_id: candidateId,
      content,
    };

    return apiRequest<Message>("/messaging/receive-reply", {
      method: "POST",
      body: JSON.stringify(replyData),
    });
  },

  approveAndSend: async (
    messageId: string,
    content: string
  ): Promise<ApiResponse<Message>> => {
    return apiRequest<Message>(`/messaging/${messageId}/approve`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  getConversation: async (candidateId: string, limit = 50): Promise<ApiResponse<Message[]>> => {
    const params = new URLSearchParams({
      candidate_id: candidateId,
      limit: limit.toString(),
    });

    return apiRequest<Message[]>(`/messaging/conversation?${params.toString()}`);
  },

  getPendingReviews: async (limit = 20): Promise<ApiResponse<Message[]>> => {
    return apiRequest<Message[]>(`/messaging/pending-reviews?limit=${limit}`);
  },
};

// ==================== Jobs ====================

export const jobsApi = {
  getAll: async (filters?: {
    type?: string;
    status?: string;
    candidateId?: string;
  }): Promise<ApiResponse<Job[]>> => {
    const params = new URLSearchParams();
    
    if (filters?.type) params.append("type", filters.type);
    if (filters?.status) params.append("status", filters.status);
    if (filters?.candidateId) params.append("candidate_id", filters.candidateId);

    const query = params.toString();
    return apiRequest<Job[]>(`/jobs${query ? `?${query}` : ""}`);
  },

  getById: async (id: string): Promise<ApiResponse<Job>> => {
    return apiRequest<Job>(`/jobs/${id}`);
  },

  retry: async (id: string): Promise<ApiResponse<Job>> => {
    return apiRequest<Job>(`/jobs/${id}/retry`, {
      method: "POST",
    });
  },

  cancel: async (id: string): Promise<ApiResponse> => {
    return apiRequest(`/jobs/${id}/cancel`, {
      method: "POST",
    });
  },

  getStats: async (days = 7): Promise<ApiResponse<any>> => {
    return apiRequest(`/jobs/stats?days=${days}`);
  },
};

// ==================== Export ====================

export const exportApi = {
  exportExcel: async (options: ExportOptions): Promise<Blob> => {
    const response = await apiRequest<Blob>("/export/excel", {
      method: "POST",
      body: JSON.stringify(options),
    });

    if (!response.success || !response.data) {
      throw new Error(response.error || "Export failed");
    }

    return response.data;
  },

  exportCsv: async (options: ExportOptions): Promise<Blob> => {
    const response = await apiRequest<Blob>("/export/csv", {
      method: "POST",
      body: JSON.stringify(options),
    });

    if (!response.success || !response.data) {
      throw new Error(response.error || "Export failed");
    }

    return response.data;
  },

  syncGoogleSheets: async (): Promise<ApiResponse<{ syncedAt: string; rowCount: number }>> => {
    return apiRequest<{ syncedAt: string; rowCount: number }>("/export/google-sheets/sync", {
      method: "POST",
    });
  },
};

// ==================== Dashboard ====================

export const dashboardApi = {
  getStats: async (): Promise<ApiResponse<DashboardStats>> => {
    return apiRequest<DashboardStats>("/dashboard/stats");
  },

  getActivity: async (limit = 10): Promise<ApiResponse<ActivityItem[]>> => {
    return apiRequest<ActivityItem[]>(`/dashboard/activity?limit=${limit}`);
  },
};

// ==================== Settings ====================

export const settingsApi = {
  get: async (): Promise<ApiResponse<AppSettings>> => {
    return apiRequest<AppSettings>("/settings");
  },

  update: async (updates: Partial<AppSettings>): Promise<ApiResponse<AppSettings>> => {
    return apiRequest<AppSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(updates),
    });
  },
};

// Export all APIs
export const api = {
  auth: authApi,
  candidates: candidatesApi,
  resumes: resumesApi,
  messaging: messagingApi,
  jobs: jobsApi,
  export: exportApi,
  dashboard: dashboardApi,
  settings: settingsApi,
};