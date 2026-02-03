import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ToastProvider } from "@/contexts/ToastContext";
import { JobsProvider } from "@/contexts/JobsContext";
import { ApiProvider } from "@/contexts/ApiContext";
import { ToastContainer } from "@/components/ui/ToastContainer";
import { AppLayout } from "@/components/layout/AppLayout";
import LoginPage from "@/pages/LoginPage";
import Dashboard from "@/pages/Dashboard";
import CandidatesList from "@/pages/CandidatesList";
import CandidateDetail from "@/pages/CandidateDetail";
import UploadPage from "@/pages/UploadPage";
import Settings from "@/pages/Settings";
import AdminJobs from "@/pages/AdminJobs";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient();

function ProtectedRoutes() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div className="flex items-center justify-center h-screen">Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return (
    <JobsProvider>
      <ApiProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/candidates" element={<CandidatesList />} />
            <Route path="/candidates/:id" element={<CandidateDetail />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/jobs" element={<AdminJobs />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ApiProvider>
    </JobsProvider>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <ToastProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <ToastContainer />
          <BrowserRouter>
            <AuthProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/*" element={<ProtectedRoutes />} />
              </Routes>
            </AuthProvider>
          </BrowserRouter>
        </TooltipProvider>
      </ToastProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
