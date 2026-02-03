/**
 * Mock API Service
 * Simulates backend API calls with configurable delays and error rates
 * 
 * TODO: Replace mock implementations with real API calls
 * Expected API endpoints:
 * - POST /api/parse-resume - Upload and parse resume
 * - GET /api/candidates - Get all candidates
 * - GET /api/candidates/:id - Get candidate details
 * - POST /api/generate-message - Generate personalized message
 * - POST /api/send-message - Send message to candidate
 * - POST /api/receive-reply - Webhook for incoming replies
 * - POST /api/google-sheets/sync - Sync to Google Sheets
 * - GET /api/jobs - Get background jobs status
 */

import type {
  Candidate,
  Message,
  Job,
  MessagePreview,
  DashboardStats,
  ActivityItem,
  CandidateFilters,
  PaginatedResponse,
  ApiResponse,
  AppSettings,
  UserRole,
  CandidateFieldKey,
  ConversationState,
  FieldState,
} from "@/types";
import { sampleCandidates, sampleIntentTemplates } from "@/data/sampleCandidates";

// Configuration
const CONFIG = {
  simulateDelay: true,
  minDelay: 300,
  maxDelay: 1500,
  errorRate: 0.05, // 5% chance of error
};

// Simulate network delay
const delay = (ms?: number): Promise<void> => {
  if (!CONFIG.simulateDelay) return Promise.resolve();
  const time = ms ?? Math.random() * (CONFIG.maxDelay - CONFIG.minDelay) + CONFIG.minDelay;
  return new Promise((resolve) => setTimeout(resolve, time));
};

// Simulate random errors
const maybeThrowError = (): void => {
  if (Math.random() < CONFIG.errorRate) {
    throw new Error("Network error: Failed to connect to server");
  }
};

// In-memory storage (simulates database)
let candidates = [...sampleCandidates];
let jobs: Job[] = [];
let settings: AppSettings = {
  mode: "mock",
  theme: "light",
  defaultIntentTemplates: sampleIntentTemplates,
};

// Generate unique IDs
const generateId = (prefix: string): string => 
  `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// ==================== Authentication ====================
// TODO: Replace with real authentication API

export const mockAuth = {
  login: async (email: string, _password: string): Promise<ApiResponse<{ token: string; user: { id: string; email: string; name: string; organizationId: string; organizationName: string; role: UserRole } }>> => {
    await delay(800);
    maybeThrowError();
    
    // Mock validation
    if (!email.includes("@")) {
      return { success: false, error: "Invalid email format" };
    }
    
    // Admin users have "admin" in their email
    const isAdmin = email.toLowerCase().includes("admin");
    
    return {
      success: true,
      data: {
        token: "mock_jwt_token_" + Date.now(),
        user: {
          id: "user_001",
          email,
          name: email.split("@")[0].replace(".", " ").replace(/\b\w/g, (l) => l.toUpperCase()),
          organizationId: "org_001",
          organizationName: "Acme Recruiting",
          role: isAdmin ? "ADMIN" : "RECRUITER",
        },
      },
    };
  },
  
  logout: async (): Promise<void> => {
    await delay(200);
  },
};

// ==================== Candidates ====================

export const mockCandidatesApi = {
  getAll: async (filters?: CandidateFilters): Promise<PaginatedResponse<Candidate>> => {
    await delay();
    maybeThrowError();
    
    let filtered = [...candidates];
    
    if (filters?.search) {
      const search = filters.search.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.name.toLowerCase().includes(search) ||
          c.email.toLowerCase().includes(search) ||
          c.skills.some((s) => s.toLowerCase().includes(search)) ||
          c.currentCompany?.toLowerCase().includes(search) ||
          c.location?.toLowerCase().includes(search)
      );
    }
    
    if (filters?.skills?.length) {
      filtered = filtered.filter((c) =>
        filters.skills!.some((skill) =>
          c.skills.some((s) => s.toLowerCase() === skill.toLowerCase())
        )
      );
    }
    
    if (filters?.status?.length) {
      filtered = filtered.filter((c) => filters.status!.includes(c.status));
    }
    
    if (filters?.minExperience !== undefined) {
      filtered = filtered.filter(
        (c) => (c.yearsExperience ?? 0) >= filters.minExperience!
      );
    }
    
    if (filters?.maxExperience !== undefined) {
      filtered = filtered.filter(
        (c) => (c.yearsExperience ?? 0) <= filters.maxExperience!
      );
    }
    
    return {
      items: filtered,
      total: filtered.length,
      page: 1,
      pageSize: 50,
      hasMore: false,
    };
  },
  
  getById: async (id: string): Promise<ApiResponse<Candidate>> => {
    await delay();
    maybeThrowError();
    
    const candidate = candidates.find((c) => c.id === id);
    if (!candidate) {
      return { success: false, error: "Candidate not found" };
    }
    
    return { success: true, data: candidate };
  },
  
  update: async (id: string, updates: Partial<Candidate>): Promise<ApiResponse<Candidate>> => {
    await delay();
    maybeThrowError();
    
    const index = candidates.findIndex((c) => c.id === id);
    if (index === -1) {
      return { success: false, error: "Candidate not found" };
    }
    
    candidates[index] = { ...candidates[index], ...updates, updatedAt: new Date().toISOString() };
    return { success: true, data: candidates[index] };
  },
};

// ==================== Resume Upload & Parsing ====================
// TODO: Replace with real file upload and parsing API
// Expected: POST /api/parse-resume
// Body: FormData with 'file' or { url: string }
// Response: { resumeId: string, jobId: string }

export const mockResumeApi = {
  upload: async (file: File | string): Promise<ApiResponse<{ resumeId: string; candidateId: string; jobId: string }>> => {
    await delay(500);
    maybeThrowError();
    
    const resumeId = generateId("resume");
    const candidateId = generateId("cand");
    const jobId = generateId("job");
    
    // Create parse job
    const parseJob: Job = {
      id: jobId,
      type: "parse_resume",
      status: "queued",
      createdAt: new Date().toISOString(),
      candidateId,
      resumeId,
    };
    jobs.push(parseJob);
    
    // Simulate parsing in background
    setTimeout(() => {
      const jobIndex = jobs.findIndex((j) => j.id === jobId);
      if (jobIndex !== -1) {
        jobs[jobIndex] = { ...jobs[jobIndex], status: "processing", startedAt: new Date().toISOString() };
      }
      
      setTimeout(() => {
        // Create new candidate from parsed resume
        const newCandidate: Candidate = {
          id: candidateId,
          name: typeof file === "string" ? "URL Upload Candidate" : file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " "),
          email: `candidate_${Date.now()}@email.com`,
          skills: ["JavaScript", "React"],
          status: "new",
          parsedFields: [],
          resumes: [{
            id: resumeId,
            candidateId,
            fileName: typeof file === "string" ? "url_resume.pdf" : file.name,
            fileUrl: typeof file === "string" ? file : URL.createObjectURL(file),
            fileType: "pdf",
            uploadedAt: new Date().toISOString(),
            parsedAt: new Date().toISOString(),
          }],
          messages: [],
          overallConfidence: 75,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        candidates.push(newCandidate);
        
        // Complete the job
        const ji = jobs.findIndex((j) => j.id === jobId);
        if (ji !== -1) {
          jobs[ji] = { ...jobs[ji], status: "completed", completedAt: new Date().toISOString() };
        }
      }, 2000);
    }, 500);
    
    return {
      success: true,
      data: { resumeId, candidateId, jobId },
    };
  },
  
  reprocess: async (resumeId: string): Promise<ApiResponse<{ jobId: string }>> => {
    await delay();
    maybeThrowError();
    
    const jobId = generateId("job");
    const parseJob: Job = {
      id: jobId,
      type: "parse_resume",
      status: "queued",
      createdAt: new Date().toISOString(),
      resumeId,
    };
    jobs.push(parseJob);
    
    // Simulate reprocessing
    setTimeout(() => {
      const index = jobs.findIndex((j) => j.id === jobId);
      if (index !== -1) {
        jobs[index] = { ...jobs[index], status: "completed", completedAt: new Date().toISOString() };
      }
    }, 3000);
    
    return { success: true, data: { jobId } };
  },
};

// ==================== Messaging ====================
// TODO: Replace with real LLM and messaging API
// Expected: POST /api/generate-message
// Body: { intent: string, candidateId: string, candidateContext: object, pendingFields: CandidateFieldKey[] }
// Response: { content: string, askedFields: CandidateFieldKey[], metadata: { tokensUsed: number } }

export const mockMessagingApi = {
  generatePreview: async (intent: string, candidateId: string, pendingFields?: CandidateFieldKey[]): Promise<ApiResponse<MessagePreview>> => {
    await delay(1000); // Simulate LLM generation time
    maybeThrowError();
    
    const candidate = candidates.find((c) => c.id === candidateId);
    if (!candidate) {
      return { success: false, error: "Candidate not found" };
    }
    
    // Determine which fields to ask about based on pendingFields
    const fieldsToAsk = pendingFields || [];
    
    // Build questions for pending fields
    const fieldQuestions: Record<CandidateFieldKey, string> = {
      name: "Could you confirm your full name?",
      email: "What's the best email to reach you?",
      phone: "What's your phone number for scheduling calls?",
      experience: "How many years of experience do you have?",
      skills: "What are your key technical skills?",
      currentCompany: "Where are you currently working?",
      education: "Could you share your educational background?",
      location: "What's your current location?",
    };
    
    const questions = fieldsToAsk.map(f => fieldQuestions[f]).filter(Boolean);
    
    // Mock LLM-generated message
    let content = `Hi ${candidate.name.split(" ")[0]}! ${intent}`;
    
    if (candidate.currentCompany) {
      content += ` I noticed your experience at ${candidate.currentCompany}${candidate.skills.length ? ` with ${candidate.skills.slice(0, 2).join(" and ")}` : ""} - very impressive!`;
    }
    
    if (questions.length > 0) {
      content += ` I have a few quick questions: ${questions.join(" ")}`;
    }
    
    content += " Looking forward to hearing from you!";
    
    return {
      success: true,
      data: {
        content,
        candidateId,
        intent,
        askedFields: fieldsToAsk,
        metadata: {
          tokensUsed: Math.floor(Math.random() * 100) + 50,
          modelVersion: "mock-llm-v1",
        },
      },
    };
  },
  
  send: async (candidateId: string, content: string, mode: "mock" | "automation"): Promise<ApiResponse<Message>> => {
    await delay(800);
    maybeThrowError();
    
    const message: Message = {
      id: generateId("msg"),
      candidateId,
      direction: "outgoing",
      content,
      timestamp: new Date().toISOString(),
      status: mode === "mock" ? "sent" : "pending",
      generatedBy: "ai",
    };
    
    // Add message to candidate
    const candidateIndex = candidates.findIndex((c) => c.id === candidateId);
    if (candidateIndex !== -1) {
      candidates[candidateIndex].messages.push(message);
      candidates[candidateIndex].lastMessageAt = message.timestamp;
      candidates[candidateIndex].status = "contacted";
      candidates[candidateIndex].updatedAt = new Date().toISOString();
    }
    
    // Create send job for automation mode
    if (mode === "automation") {
      const jobId = generateId("job");
      jobs.push({
        id: jobId,
        type: "send_message",
        status: "queued",
        createdAt: new Date().toISOString(),
        candidateId,
        messageId: message.id,
      });
      
      // Simulate sending
      setTimeout(() => {
        const ji = jobs.findIndex((j) => j.id === jobId);
        if (ji !== -1) {
          jobs[ji] = { ...jobs[ji], status: "completed", completedAt: new Date().toISOString() };
        }
        // Update message status
        const ci = candidates.findIndex((c) => c.id === candidateId);
        if (ci !== -1) {
          const mi = candidates[ci].messages.findIndex((m) => m.id === message.id);
          if (mi !== -1) {
            candidates[ci].messages[mi].status = "sent";
          }
        }
      }, 2000);
    }
    
    return { success: true, data: message };
  },
  
  simulateReply: async (candidateId: string, replyText: string): Promise<ApiResponse<Message>> => {
    await delay(500);
    maybeThrowError();
    
    // Mock classification with enhanced question detection
    let classification: Message["classification"] = "interested";
    let suggestedReply = "Thank you for your interest! ";
    let requiresHRReview = false;
    let aiSuggestedReply: string | undefined;
    
    const lowerText = replyText.toLowerCase();
    
    // Enhanced question detection heuristics
    const questionIndicators = ["?", "what", "when", "how", "salary", "compensation", "package", "pay", "benefits", "remote", "hybrid", "location", "why", "who", "which"];
    const hasQuestion = questionIndicators.some(indicator => lowerText.includes(indicator));
    
    if (lowerText.includes("not interested") || lowerText.includes("no thanks") || lowerText.includes("pass") || lowerText.includes("decline")) {
      classification = "not_interested";
      suggestedReply = "Thank you for your time. We'll keep your profile on file for future opportunities that might be a better fit.";
    } else if (hasQuestion) {
      // Mark as question requiring HR review
      classification = "question";
      requiresHRReview = true;
      
      // Generate AI suggested reply based on question type
      if (lowerText.includes("salary") || lowerText.includes("compensation") || lowerText.includes("pay") || lowerText.includes("package")) {
        aiSuggestedReply = "Great question! The compensation range for this role is competitive and includes base salary, equity, and benefits. Specifically, we're looking at $X-Y base plus equity. Would you like to discuss further on a call?";
      } else if (lowerText.includes("remote") || lowerText.includes("hybrid") || lowerText.includes("office")) {
        aiSuggestedReply = "This role offers flexible work arrangements. We currently operate on a hybrid model with X days in office per week, though we're open to discussing what works best for you. Would you like more details?";
      } else if (lowerText.includes("team") || lowerText.includes("who")) {
        aiSuggestedReply = "Great question about the team! You'd be working with a talented group of X engineers/professionals. The team culture is collaborative and focused on Y. Happy to share more details on a call.";
      } else {
        aiSuggestedReply = "Thanks for your question! I'd be happy to provide more details on this. [HR: Please customize this response based on the specific question asked.] Would you be available for a quick call to discuss?";
      }
      suggestedReply = aiSuggestedReply;
    } else if (lowerText.includes("yes") || lowerText.includes("interested") || lowerText.includes("available") || lowerText.includes("sure")) {
      classification = "interested";
      suggestedReply = "Fantastic! Let's schedule a call to discuss further. Would any of these times work for you?";
    } else if (lowerText.includes("clarif") || lowerText.includes("more info")) {
      classification = "needs_clarification";
      suggestedReply = "Of course! Let me provide more details: ";
    }
    
    const message: Message = {
      id: generateId("msg"),
      candidateId,
      direction: "incoming",
      content: replyText,
      timestamp: new Date().toISOString(),
      status: "delivered",
      classification,
      suggestedReply,
      requiresHRReview,
      aiSuggestedReply,
      hrApproved: false,
    };
    
    // Add to candidate
    const candidateIndex = candidates.findIndex((c) => c.id === candidateId);
    if (candidateIndex !== -1) {
      candidates[candidateIndex].messages.push(message);
      candidates[candidateIndex].lastMessageAt = message.timestamp;
      if (!requiresHRReview) {
        candidates[candidateIndex].status = classification === "interested" ? "interested" : 
                                            classification === "not_interested" ? "not_interested" : "needs_clarification";
      }
      candidates[candidateIndex].updatedAt = new Date().toISOString();
    }
    
    return { success: true, data: message };
  },
  
  // Approve and send HR-reviewed message
  approveAndSend: async (candidateId: string, messageId: string, approvedContent: string): Promise<ApiResponse<Message>> => {
    await delay(500);
    maybeThrowError();
    
    const candidateIndex = candidates.findIndex((c) => c.id === candidateId);
    if (candidateIndex === -1) {
      return { success: false, error: "Candidate not found" };
    }
    
    // Mark original incoming message as approved
    const msgIndex = candidates[candidateIndex].messages.findIndex((m) => m.id === messageId);
    if (msgIndex !== -1) {
      candidates[candidateIndex].messages[msgIndex].hrApproved = true;
      candidates[candidateIndex].messages[msgIndex].hrApprovedAt = new Date().toISOString();
    }
    
    // Create outgoing approved message
    const outgoingMessage: Message = {
      id: generateId("msg"),
      candidateId,
      direction: "outgoing",
      content: approvedContent,
      timestamp: new Date().toISOString(),
      status: "sent",
      generatedBy: "ai",
    };
    
    candidates[candidateIndex].messages.push(outgoingMessage);
    candidates[candidateIndex].lastMessageAt = outgoingMessage.timestamp;
    candidates[candidateIndex].updatedAt = new Date().toISOString();
    
    return { success: true, data: outgoingMessage };
  },
};

// ==================== Jobs ====================

export const mockJobsApi = {
  getAll: async (): Promise<Job[]> => {
    await delay(300);
    return [...jobs].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  },
  
  getById: async (id: string): Promise<ApiResponse<Job>> => {
    await delay(200);
    const job = jobs.find((j) => j.id === id);
    if (!job) {
      return { success: false, error: "Job not found" };
    }
    return { success: true, data: job };
  },
};

// ==================== Export & Sync ====================
// TODO: Replace with real export and Google Sheets integration
// Expected: POST /api/google-sheets/sync
// Body: { sheetId: string, data: Candidate[] }
// Response: { success: boolean, syncedAt: string }

export const mockExportApi = {
  exportExcel: async (candidateIds?: string[]): Promise<Blob> => {
    await delay(1000);
    maybeThrowError();
    
    const toExport = candidateIds 
      ? candidates.filter((c) => candidateIds.includes(c.id))
      : candidates;
    
    // Create simple CSV (mock XLSX)
    const headers = ["Name", "Email", "Phone", "Experience", "Skills", "Company", "Location", "Status"];
    const rows = toExport.map((c) => [
      c.name,
      c.email,
      c.phone || "",
      c.yearsExperience?.toString() || "",
      c.skills.join("; "),
      c.currentCompany || "",
      c.location || "",
      c.status,
    ]);
    
    const csv = [headers.join(","), ...rows.map((r) => r.map((c) => `"${c}"`).join(","))].join("\n");
    return new Blob([csv], { type: "text/csv" });
  },
  
  syncGoogleSheets: async (): Promise<ApiResponse<{ syncedAt: string; rowCount: number }>> => {
    await delay(1500);
    
    // 20% chance of error for testing
    if (Math.random() < 0.2) {
      return { success: false, error: "Failed to connect to Google Sheets. Please check your credentials." };
    }
    
    return {
      success: true,
      data: {
        syncedAt: new Date().toISOString(),
        rowCount: candidates.length,
      },
    };
  },
};

// ==================== Dashboard ====================

export const mockDashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    await delay(400);
    
    return {
      totalCandidates: candidates.length,
      resumesProcessed: candidates.reduce((acc, c) => acc + c.resumes.length, 0),
      messagesSent: candidates.reduce((acc, c) => acc + c.messages.filter((m) => m.direction === "outgoing").length, 0),
      repliesReceived: candidates.reduce((acc, c) => acc + c.messages.filter((m) => m.direction === "incoming").length, 0),
      pendingJobs: jobs.filter((j) => j.status === "queued" || j.status === "processing").length,
      interestedCandidates: candidates.filter((c) => c.status === "interested").length,
    };
  },
  
  getRecentActivity: async (): Promise<ActivityItem[]> => {
    await delay(300);
    
    const activities: ActivityItem[] = [];
    
    // Generate activities from candidates
    candidates.forEach((c) => {
      activities.push({
        id: `act_${c.id}_created`,
        type: "resume_uploaded",
        description: `Resume uploaded for ${c.name}`,
        timestamp: c.createdAt,
        candidateId: c.id,
        candidateName: c.name,
      });
      
      c.messages.forEach((m) => {
        activities.push({
          id: `act_${m.id}`,
          type: m.direction === "outgoing" ? "message_sent" : "reply_received",
          description: m.direction === "outgoing" 
            ? `Message sent to ${c.name}`
            : `Reply received from ${c.name}`,
          timestamp: m.timestamp,
          candidateId: c.id,
          candidateName: c.name,
        });
      });
    });
    
    return activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).slice(0, 10);
  },
};

// ==================== Settings ====================

export const mockSettingsApi = {
  get: async (): Promise<AppSettings> => {
    await delay(200);
    return { ...settings };
  },
  
  update: async (updates: Partial<AppSettings>): Promise<AppSettings> => {
    await delay(300);
    settings = { ...settings, ...updates };
    return settings;
  },
};

// Export config for testing
export const mockApiConfig = CONFIG;
