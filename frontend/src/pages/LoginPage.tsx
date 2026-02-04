import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Lock, 
  Loader2, 
  Eye, 
  EyeOff, 
  Shield, 
  Mail, 
  CheckSquare, 
  Square 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle, 
  CardFooter 
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, login } = useAuth();
  
  // Form State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  
  // UI State
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Load remembered email on mount
  useEffect(() => {
    const rememberedEmail = localStorage.getItem("hr_remembered_email");
    if (rememberedEmail) {
      setEmail(rememberedEmail);
      setRememberMe(true);
    }
  }, []);

  const validateForm = (): boolean => {
    const newErrors: { email?: string; password?: string } = {};
    let isValid = true;

    // Email validation
    if (!email.trim()) {
      newErrors.email = "Email is required";
      isValid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = "Please enter a valid email address";
      isValid = false;
    }

    // Password validation
    if (!password) {
      newErrors.password = "Password is required";
      isValid = false;
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
      isValid = false;
    }

    setFieldErrors(newErrors);
    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    
    try {
      const result = await login(email, password);
      
      if (result.success) {
        // Handle Remember Me logic
        if (rememberMe) {
          localStorage.setItem("hr_remembered_email", email);
        } else {
          localStorage.removeItem("hr_remembered_email");
        }
        
        // Navigation is handled by the useEffect watching 'isAuthenticated'
        // But we can force it here for immediate feedback if needed
        navigate("/dashboard"); 
      } else {
        setError(result.error || "Invalid credentials. Please try again.");
        setPassword(""); // Clear password on failure
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50/50">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-sm text-gray-500 mt-4">Initializing secure session...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 to-gray-100 p-4">
      <div className="w-full max-w-[400px]">
        
        {/* Brand Header */}
        <div className="text-center mb-8 space-y-2">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-blue-600 shadow-lg shadow-blue-600/20 mb-2">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            HireFlow 360
          </h1>
          <p className="text-sm text-gray-500">
            Enterprise Recruitment Platform
          </p>
        </div>

        {/* Login Card */}
        <Card className="border-gray-200 shadow-xl shadow-gray-200/40">
          <CardHeader className="space-y-1 pb-6">
            <CardTitle className="text-xl font-semibold text-center">Welcome Back</CardTitle>
            <CardDescription className="text-center">
              Sign in to your account to continue
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-6 animate-in fade-in-50 slide-in-from-top-1">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-5">
              
              {/* Email Field */}
              <div className="space-y-2">
                <Label htmlFor="email" className={fieldErrors.email ? "text-red-500" : ""}>
                  Email Address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (fieldErrors.email) setFieldErrors({ ...fieldErrors, email: undefined });
                    }}
                    disabled={isSubmitting}
                    className={`pl-9 h-11 transition-all ${fieldErrors.email ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                    autoComplete="email"
                  />
                </div>
                {fieldErrors.email && (
                  <p className="text-xs text-red-500 mt-1 font-medium">{fieldErrors.email}</p>
                )}
              </div>
              
              {/* Password Field */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className={fieldErrors.password ? "text-red-500" : ""}>
                    Password
                  </Label>
                  <button
                    type="button"
                    onClick={() => navigate("/forgot-password")}
                    className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline tabindex-0"
                    disabled={isSubmitting}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (fieldErrors.password) setFieldErrors({ ...fieldErrors, password: undefined });
                    }}
                    disabled={isSubmitting}
                    className={`pl-9 pr-10 h-11 transition-all ${fieldErrors.password ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={isSubmitting}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" aria-label="Hide password" />
                    ) : (
                      <Eye className="h-4 w-4" aria-label="Show password" />
                    )}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p className="text-xs text-red-500 mt-1 font-medium">{fieldErrors.password}</p>
                )}
              </div>

              {/* Remember Me Checkbox */}
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={rememberMe}
                  onClick={() => setRememberMe(!rememberMe)}
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-900 focus:outline-none"
                  disabled={isSubmitting}
                >
                  {rememberMe ? (
                    <CheckSquare className="h-4 w-4 text-blue-600" />
                  ) : (
                    <Square className="h-4 w-4 text-gray-400" />
                  )}
                  <span className="select-none">Remember me on this device</span>
                </button>
              </div>
              
              <Button
                type="submit"
                className="w-full h-11 text-base font-medium shadow-blue-600/20 hover:shadow-blue-600/40 transition-all duration-200"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  "Sign In"
                )}
              </Button>
            </form>
          </CardContent>
          
          {/* Security Footer */}
          <CardFooter className="border-t border-gray-50 bg-gray-50/50 p-4">
            <div className="w-full flex items-center justify-center space-x-2 text-xs text-gray-500">
              <Lock className="h-3 w-3" />
              <span>256-bit encrypted connection</span>
            </div>
          </CardFooter>
        </Card>
        
        {/* App Footer */}
        <div className="mt-8 text-center space-y-2">
          <p className="text-xs text-gray-400">
            &copy; {new Date().getFullYear()} HireFlow 360. All rights reserved.
          </p>
          {import.meta.env.MODE === 'development' && (
             <div className="text-[10px] text-amber-600/80 bg-amber-50 inline-block px-2 py-1 rounded-full border border-amber-100">
               Dev Mode • API: {import.meta.env.VITE_API_BASE_URL}
             </div>
          )}
        </div>
      </div>
    </div>
  );
}