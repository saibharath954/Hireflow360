/**
 * Candidate Detail Page
 * Shows parsed fields, messaging composer, and conversation
 */

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Send, Eye, EyeOff, RefreshCw, MessageSquare, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { BadgeConfidence } from "@/components/ui/BadgeConfidence";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TagList } from "@/components/ui/TagList";
import { MessageBubble } from "@/components/ui/MessageBubble";
import { Avatar } from "@/components/ui/Avatar";
import { ConversationChecklist, deriveConversationState, getPendingFields } from "@/components/ConversationChecklist";
import { HRReviewPanel } from "@/components/HRReviewPanel";
import { ReprocessResumeButton } from "@/components/ReprocessResumeButton";
import { useApi } from "@/hooks/useApi";
import { useToastContext } from "@/contexts/ToastContext";
import { useApiContext } from "@/contexts/ApiContext";
import type { Candidate, CandidateFieldKey, Message } from "@/types";
import { sampleIntentTemplates } from "@/data/sampleCandidates";

export default function CandidateDetail() {
  const { id } = useParams<{ id: string }>();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showRawExtraction, setShowRawExtraction] = useState(false);
  const [intent, setIntent] = useState("");
  const [preview, setPreview] = useState("");
  const [previewAskedFields, setPreviewAskedFields] = useState<CandidateFieldKey[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [mockReply, setMockReply] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);

  const { getCandidate, generateMessagePreview, sendMessage, simulateReply, approveAndSendMessage, reprocessResume, getConversation } = useApi();
  const { settings } = useApiContext();
  const toast = useToastContext();

  // Derive conversation state from candidate data
  const conversationState = useMemo(() => {
    if (!candidate) return null;
    return deriveConversationState(candidate);
  }, [candidate]);

  // Get pending fields (not answered, not asked)
  const pendingFields = useMemo(() => {
    if (!conversationState) return [];
    return getPendingFields(conversationState);
  }, [conversationState]);

  // Check if all required fields are collected
  const allFieldsCollected = pendingFields.length === 0;

  // Find messages requiring HR review
  const pendingHRReviews = useMemo(() => {
    if (!messages) return [];
    return messages.filter(
      (msg) => msg.direction === "incoming" && msg.requiresHRReview && !msg.hrApproved
    );
  }, [messages]);

  const loadCandidate = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const [candidateData, conversationData] = await Promise.all([
        getCandidate(id),
        getConversation(id, 50)
      ]);
      
      if (candidateData) {
        setCandidate(candidateData);
      }
      
      if (conversationData) {
        setMessages(conversationData);
      }
    } catch (error) {
      console.error("Failed to load candidate:", error);
      toast.error("Error", "Failed to load candidate data");
    } finally {
      setIsLoading(false);
    }
  }, [id, getCandidate, getConversation, toast]);

  useEffect(() => {
    loadCandidate();
  }, [loadCandidate]);

  const handleGeneratePreview = async () => {
    if (!id || !intent.trim()) return;
    setIsGenerating(true);
    try {
      // Pass pending fields to the message generator
      const result = await generateMessagePreview(intent, id, pendingFields);
      if (result) {
        setPreview(result.content);
        setPreviewAskedFields(result.askedFields || []);
      }
    } catch (error) {
      console.error("Failed to generate preview:", error);
      toast.error("Error", "Failed to generate message preview");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSend = async () => {
    if (!id || !preview) return;
    setIsSending(true);
    try {
      const result = await sendMessage(id, preview, settings.mode, previewAskedFields);
      if (result) {
        toast.success("Message sent", `Message sent in ${settings.mode} mode`);
        setIntent("");
        setPreview("");
        setPreviewAskedFields([]);
        // Refresh conversation
        const updatedMessages = await getConversation(id, 50);
        if (updatedMessages) {
          setMessages(updatedMessages);
        }
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      toast.error("Error", "Failed to send message");
    } finally {
      setIsSending(false);
    }
  };

  const handleSimulateReply = async () => {
    if (!id || !mockReply.trim()) return;
    setIsSimulating(true);
    try {
      const result = await simulateReply(id, mockReply);
      if (result) {
        if (result.requiresHRReview) {
          toast.warning("HR Review Required", "This reply contains a question that needs your approval before responding.");
        } else {
          toast.success("Reply simulated", `Classified as: ${result.classification}`);
        }
        setMockReply("");
        // Refresh conversation
        const updatedMessages = await getConversation(id, 50);
        if (updatedMessages) {
          setMessages(updatedMessages);
        }
      }
    } catch (error) {
      console.error("Failed to simulate reply:", error);
      toast.error("Error", "Failed to simulate reply");
    } finally {
      setIsSimulating(false);
    }
  };

  const handleApproveAndSend = async (messageId: string, content: string) => {
    if (!id) return;
    setIsApproving(true);
    try {
      const result = await approveAndSendMessage(messageId, content);
      if (result) {
        toast.success("Message approved and sent", "Your response has been sent to the candidate.");
        // Refresh conversation
        const updatedMessages = await getConversation(id, 50);
        if (updatedMessages) {
          setMessages(updatedMessages);
        }
      }
    } catch (error) {
      console.error("Failed to approve message:", error);
      toast.error("Error", "Failed to approve and send message");
    } finally {
      setIsApproving(false);
    }
  };

  const handleReprocessResume = async (resumeId: string) => {
    setIsReprocessing(true);
    try {
      const result = await reprocessResume(resumeId);
      if (result) {
        toast.success("Resume reprocessed", "The resume has been reprocessed and fields updated.");
        // Reload candidate data
        const candidateData = await getCandidate(id!);
        if (candidateData) {
          setCandidate(candidateData);
        }
      }
    } catch (error) {
      console.error("Failed to reprocess resume:", error);
      toast.error("Error", "Failed to reprocess the resume. Please try again.");
    } finally {
      setIsReprocessing(false);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>;
  }

  if (!candidate) {
    return <ErrorState message="Candidate not found" onRetry={loadCandidate} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/candidates"><ArrowLeft className="h-5 w-5" /></Link>
        </Button>
        <Avatar name={candidate.name} size="lg" />
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{candidate.name}</h1>
          <p className="text-muted-foreground">{candidate.email}</p>
        </div>
        <StatusBadge status={candidate.status} />
        {/* Reprocess button - only visible to admins */}
        {candidate.resumes.length > 0 && (
          <ReprocessResumeButton
            resumeId={candidate.resumes[0].id}
            onReprocess={handleReprocessResume}
            isReprocessing={isReprocessing}
          />
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Parsed Fields */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Parsed Information</CardTitle>
                <CardDescription>Extracted from resume</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowRawExtraction(!showRawExtraction)}>
                {showRawExtraction ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
                {showRawExtraction ? "Hide" : "Show"} Raw
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {candidate.parsedFields && candidate.parsedFields.length > 0 ? (
                candidate.parsedFields.map((field) => (
                  <div key={field.name} className="flex items-start justify-between py-2 border-b last:border-0">
                    <div className="flex-1">
                      <p className="text-sm font-medium capitalize">{field.name.replace(/_/g, " ")}</p>
                      <p className="text-sm text-foreground">
                        {Array.isArray(field.value) ? <TagList tags={field.value} limit={10} /> : String(field.value || "—")}
                      </p>
                      {showRawExtraction && field.rawExtraction && (
                        <p className="text-xs text-muted-foreground mt-1 italic">"{field.rawExtraction}"</p>
                      )}
                    </div>
                    <BadgeConfidence confidence={field.confidence} size="sm" />
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground text-center py-4">No parsed fields available</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Middle: Conversation Checklist */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Information Checklist</CardTitle>
              <CardDescription>Track collected candidate information</CardDescription>
            </CardHeader>
            <CardContent>
              {conversationState ? (
                <ConversationChecklist conversationState={conversationState} />
              ) : (
                <p className="text-muted-foreground text-center py-4">No conversation data available</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Messaging */}
        <div className="space-y-4">
          {/* Pending HR Reviews */}
          {pendingHRReviews.length > 0 && (
            <Card className="border-warning/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Pending HR Reviews</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {pendingHRReviews.map((msg) => (
                  <HRReviewPanel
                    key={msg.id}
                    message={msg}
                    onApprove={handleApproveAndSend}
                    isApproving={isApproving}
                  />
                ))}
              </CardContent>
            </Card>
          )}

          {/* Message Composer */}
          <Card>
            <CardHeader>
              <CardTitle>Message Composer</CardTitle>
              <CardDescription>Generate personalized outreach</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {allFieldsCollected ? (
                <div className="flex items-start gap-3 p-4 bg-muted rounded-lg">
                  <Info className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">All information collected</p>
                    <p className="text-sm text-muted-foreground">
                      All required candidate information has already been gathered. No new questions needed.
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <div>
                    <Textarea 
                      placeholder="Enter your intent (e.g., 'Ask about availability for Backend role')" 
                      value={intent} 
                      onChange={(e) => setIntent(e.target.value)} 
                      rows={2} 
                    />
                    <div className="flex flex-wrap gap-1 mt-2">
                      {sampleIntentTemplates.slice(0, 2).map((t, i) => (
                        <Button 
                          key={i} 
                          variant="outline" 
                          size="sm" 
                          className="text-xs h-auto py-1" 
                          onClick={() => setIntent(t)}
                        >
                          {t.slice(0, 40)}...
                        </Button>
                      ))}
                    </div>
                    {pendingFields.length > 0 && (
                      <p className="text-xs text-muted-foreground mt-2">
                        <span className="font-medium">Missing fields:</span>{" "}
                        {pendingFields.map(f => f.charAt(0).toUpperCase() + f.slice(1)).join(", ")}
                      </p>
                    )}
                  </div>
                  <Button 
                    onClick={handleGeneratePreview} 
                    disabled={!intent.trim() || isGenerating} 
                    className="w-full"
                  >
                    {isGenerating ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <MessageSquare className="h-4 w-4 mr-2" />}
                    Generate Preview
                  </Button>
                </>
              )}
              {preview && (
                <div className="p-3 bg-muted rounded-lg">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Preview</p>
                  <p className="text-sm">{preview}</p>
                  {previewAskedFields.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Will ask about: {previewAskedFields.map(f => f.charAt(0).toUpperCase() + f.slice(1)).join(", ")}
                    </p>
                  )}
                  <Button onClick={handleSend} disabled={isSending} className="w-full mt-3">
                    <Send className="h-4 w-4 mr-2" />{isSending ? "Sending..." : `Send (${settings.mode} mode)`}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Message History */}
          <Card>
            <CardHeader><CardTitle>Conversation</CardTitle></CardHeader>
            <CardContent>
              {messages.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">No messages yet</p>
              ) : (
                <div className="space-y-4 max-h-80 overflow-y-auto">
                  {messages.map((msg) => (
                    <MessageBubble 
                      key={msg.id} 
                      content={msg.content} 
                      direction={msg.direction} 
                      timestamp={msg.timestamp} 
                      status={msg.status} 
                      classification={msg.classification} 
                      suggestedReply={msg.direction === "incoming" && !msg.requiresHRReview ? msg.suggestedReply : undefined}
                      requiresHRReview={msg.requiresHRReview}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Mock Reply Tool */}
          <Card>
            <CardHeader><CardTitle>Simulate Reply</CardTitle><CardDescription>Test reply parsing</CardDescription></CardHeader>
            <CardContent className="space-y-3">
              <Textarea 
                placeholder="Enter a mock reply to test classification..." 
                value={mockReply} 
                onChange={(e) => setMockReply(e.target.value)} 
                rows={2} 
              />
              <Button onClick={handleSimulateReply} disabled={!mockReply.trim() || isSimulating} variant="secondary" className="w-full">
                {isSimulating ? "Simulating..." : "Simulate Incoming Reply"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}