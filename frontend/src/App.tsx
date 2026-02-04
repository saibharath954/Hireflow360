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
            <Route path="/dashboard" element={<Dashboard />} />
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

// import { Toaster } from "@/components/ui/toaster";
// import { Toaster as Sonner } from "@/components/ui/sonner";
// import { TooltipProvider } from "@/components/ui/tooltip";
// import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
// import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
// import { ThemeProvider } from "@/contexts/ThemeContext";
// import { AuthProvider, useAuth } from "@/contexts/AuthContext";
// import { ToastProvider } from "@/contexts/ToastContext";
// import { JobsProvider } from "@/contexts/JobsContext";
// import { ApiProvider } from "@/contexts/ApiContext";
// import { ToastContainer } from "@/components/ui/ToastContainer";
// import { AppLayout } from "@/components/layout/AppLayout";
// import LoginPage from "@/pages/LoginPage";
// import Dashboard from "@/pages/Dashboard";
// import CandidatesList from "@/pages/CandidatesList";
// import CandidateDetail from "@/pages/CandidateDetail";
// import UploadPage from "@/pages/UploadPage";
// import Settings from "@/pages/Settings";
// import AdminJobs from "@/pages/AdminJobs";
// import NotFound from "@/pages/NotFound";
// import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

// // Configure React Query with retry logic
// const queryClient = new QueryClient({
//   defaultOptions: {
//     queries: {
//       retry: 3, // Retry failed requests 3 times
//       retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
//       staleTime: 5 * 60 * 1000, // 5 minutes
//       gcTime: 10 * 60 * 1000, // 10 minutes (cache time)
//       refetchOnWindowFocus: false, // Don't refetch on window focus
//       refetchOnReconnect: true, // Refetch on reconnect
//     },
//     mutations: {
//       retry: 2, // Retry failed mutations 2 times
//     },
//   },
// });

// // Loading component for initial app load
// function AppLoading() {
//   return (
//     <div className="flex flex-col items-center justify-center min-h-screen bg-background">
//       <LoadingSpinner size="lg" />
//       <p className="mt-4 text-muted-foreground">Loading application...</p>
//     </div>
//   );
// }

// // Protected routes wrapper with proper error boundaries
// function ProtectedRoutes() {
//   const { isAuthenticated, isLoading, user } = useAuth();

//   if (isLoading) {
//     return <AppLoading />;
//   }

//   if (!isAuthenticated) {
//     return <Navigate to="/login" replace />;
//   }

//   // Check admin access for admin-only routes
//   const isAdmin = user?.role === "ADMIN";

//   return (
//     <JobsProvider>
//       <ApiProvider>
//         <Routes>
//           <Route element={<AppLayout />}>
//             <Route path="/" element={<Navigate to="/dashboard" replace />} />
//             <Route path="/dashboard" element={<Dashboard />} />
//             <Route path="/candidates" element={<CandidatesList />} />
//             <Route path="/candidates/:id" element={<CandidateDetail />} />
//             <Route path="/upload" element={<UploadPage />} />
//             <Route path="/settings" element={<Settings />} />
//             {/* Admin-only routes */}
//             {isAdmin && <Route path="/jobs" element={<AdminJobs />} />}
//             {/* Redirect non-admins trying to access admin routes */}
//             {!isAdmin && <Route path="/jobs" element={<Navigate to="/dashboard" replace />} />}
//           </Route>
//           <Route path="*" element={<NotFound />} />
//         </Routes>
//       </ApiProvider>
//     </JobsProvider>
//   );
// }

// // Error boundary for catching rendering errors
// class ErrorBoundary extends React.Component<
//   { children: React.ReactNode },
//   { hasError: boolean; error?: Error }
// > {
//   constructor(props: { children: React.ReactNode }) {
//     super(props);
//     this.state = { hasError: false };
//   }

//   static getDerivedStateFromError(error: Error) {
//     return { hasError: true, error };
//   }

//   componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
//     console.error("App Error:", error, errorInfo);
//   }

//   render() {
//     if (this.state.hasError) {
//       return (
//         <div className="flex flex-col items-center justify-center min-h-screen p-4">
//           <div className="max-w-md text-center">
//             <h1 className="text-2xl font-bold text-destructive mb-4">Something went wrong</h1>
//             <p className="text-muted-foreground mb-4">
//               An unexpected error occurred. Please try refreshing the page.
//             </p>
//             <button
//               onClick={() => window.location.reload()}
//               className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
//             >
//               Refresh Page
//             </button>
//             <details className="mt-4 text-left">
//               <summary className="cursor-pointer text-sm text-muted-foreground">
//                 Error Details
//               </summary>
//               <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-auto">
//                 {this.state.error?.toString()}
//               </pre>
//             </details>
//           </div>
//         </div>
//       );
//     }

//     return this.props.children;
//   }
// }

// const App = () => (
//   <ErrorBoundary>
//     <QueryClientProvider client={queryClient}>
//       <ThemeProvider>
//         <ToastProvider>
//           <TooltipProvider>
//             {/* Toaster components for notifications */}
//             <Toaster />
//             <Sonner />
//             <ToastContainer />
            
//             {/* Main app router */}
//             <BrowserRouter>
//               <AuthProvider>
//                 <Routes>
//                   {/* Public route */}
//                   <Route path="/login" element={<LoginPage />} />
                  
//                   {/* Protected routes */}
//                   <Route path="/*" element={<ProtectedRoutes />} />
                  
//                   {/* Fallback redirect */}
//                   <Route path="*" element={<Navigate to="/" replace />} />
//                 </Routes>
//               </AuthProvider>
//             </BrowserRouter>
//           </TooltipProvider>
//         </ToastProvider>
//       </ThemeProvider>
//     </QueryClientProvider>
//   </ErrorBoundary>
// );

// export default App;