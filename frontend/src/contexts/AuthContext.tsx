/**
 * Production Authentication Context
 * Integrated with existing API service
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "@/services/api";

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  organization_id?: string;
  permissions?: string[];
  created_at?: string;
  updated_at?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Token storage keys
const TOKEN_KEYS = {
  ACCESS_TOKEN: 'hr_access_token',
  REFRESH_TOKEN: 'hr_refresh_token',
  USER_DATA: 'hr_user_data',
  TOKEN_EXPIRY: 'hr_token_expiry'
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      try {
        const accessToken = localStorage.getItem(TOKEN_KEYS.ACCESS_TOKEN);
        const userData = localStorage.getItem(TOKEN_KEYS.USER_DATA);
        
        if (accessToken && userData) {
          // Validate token with backend
          const isValid = await validateToken(accessToken);
          
          if (isValid) {
            setUser(JSON.parse(userData));
          } else {
            // Try to refresh token
            const refreshed = await attemptTokenRefresh();
            if (!refreshed) {
              clearAuthData();
            }
          }
        }
      } catch (error) {
        console.error("Auth initialization error:", error);
        clearAuthData();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!user) return;

    const checkAndRefreshToken = async () => {
      const expiryTime = localStorage.getItem(TOKEN_KEYS.TOKEN_EXPIRY);
      if (!expiryTime) return;

      const expiry = parseInt(expiryTime);
      const now = Date.now();
      const fiveMinutes = 5 * 60 * 1000;

      // Refresh if token expires in less than 5 minutes
      if (expiry - now < fiveMinutes) {
        await attemptTokenRefresh();
      }
    };

    // Check every minute
    const interval = setInterval(checkAndRefreshToken, 60000);
    return () => clearInterval(interval);
  }, [user]);

  // Validate token with backend
  const validateToken = async (token: string): Promise<boolean> => {
    try {
      // Use your existing API service
      localStorage.setItem(TOKEN_KEYS.ACCESS_TOKEN, token);
      const response = await api.auth.refreshToken();
      return response.success;
    } catch (error) {
      return false;
    }
  };

  // Attempt to refresh token
  const attemptTokenRefresh = async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem(TOKEN_KEYS.REFRESH_TOKEN);
    if (!refreshToken) return false;

    try {
      const response = await api.auth.refreshToken();
      
      if (response.success && response.data) {
        // Store new tokens
        localStorage.setItem(TOKEN_KEYS.ACCESS_TOKEN, response.data.access_token);
        
        // Store expiry (default 1 hour if not provided)
        const expiresIn = 3600; // Default 1 hour
        const expiryTime = Date.now() + (expiresIn * 1000);
        localStorage.setItem(TOKEN_KEYS.TOKEN_EXPIRY, expiryTime.toString());
        
        // Fetch user profile
        const userResponse = await fetchUserProfile();
        
        if (userResponse.success && userResponse.data) {
          const userData = userResponse.data;
          localStorage.setItem(TOKEN_KEYS.USER_DATA, JSON.stringify(userData));
          setUser(userData);
        }
        
        return true;
      }
      
      return false;
    } catch (error) {
      console.error("Token refresh failed:", error);
      return false;
    }
  };

  // Fetch user profile using existing API
  const fetchUserProfile = async () => {
    const userData = localStorage.getItem(TOKEN_KEYS.USER_DATA);
    if (userData) {
      return { success: true, data: JSON.parse(userData) };
    }
    return { success: false, error: "No user data found" };
  };

  // Clear all auth data
  const clearAuthData = () => {
    Object.values(TOKEN_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
    setUser(null);
  };

  // Login function - using your existing API service
  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    
    try {
      const response = await api.auth.login(email, password);
      
      if (response.success && response.data) {
        // Extract data from response
        const { access_token, refresh_token, user } = response.data;
        
        // Store tokens
        localStorage.setItem(TOKEN_KEYS.ACCESS_TOKEN, access_token);
        localStorage.setItem(TOKEN_KEYS.REFRESH_TOKEN, refresh_token);
        
        // Calculate and store token expiry (default 1 hour)
        const expiresIn = response.data.expires_in || 3600;
        const expiryTime = Date.now() + (expiresIn * 1000);
        localStorage.setItem(TOKEN_KEYS.TOKEN_EXPIRY, expiryTime.toString());
        
        // Store user data
        localStorage.setItem(TOKEN_KEYS.USER_DATA, JSON.stringify(user));
        setUser(user);

        return { success: true };
      } else {
        return { 
          success: false, 
          error: response.error || "Login failed. Please check your credentials." 
        };
      }

    } catch (error: any) {
      console.error("Login error:", error);
      
      let errorMessage = "Network error. Please check your connection.";
      if (error.message?.includes("Failed to fetch")) {
        errorMessage = "Cannot connect to server. Please try again later.";
      }
      
      return { success: false, error: errorMessage };
      
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Logout function - using your existing API service
  const logout = useCallback(async () => {
    setIsLoading(true);
    
    try {
      await api.auth.logout();
    } catch (error) {
      console.warn("Logout API call failed:", error);
    } finally {
      // Always clear local data
      clearAuthData();
      setIsLoading(false);
      
      // Redirect to login page
      window.location.href = '/login';
    }
  }, []);

  // Refresh user data
  const refreshUserData = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await fetchUserProfile();
      if (response.success && response.data) {
        localStorage.setItem(TOKEN_KEYS.USER_DATA, JSON.stringify(response.data));
        setUser(response.data);
      }
    } catch (error) {
      console.error("Failed to refresh user data:", error);
    }
  }, [user]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isAdmin: user?.role === "ADMIN",
        login,
        logout,
        refreshUserData,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}