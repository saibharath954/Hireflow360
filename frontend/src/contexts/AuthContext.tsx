/**
 * Authentication Context
 * Provides mock authentication for the HR platform
 * 
 * TODO: Replace mockAuth with real authentication API
 * Expected integration points:
 * - POST /api/auth/login
 * - POST /api/auth/logout
 * - GET /api/auth/me
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { User, Organization, UserRole } from "@/types";
import { mockAuth } from "@/services/mockApi";

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_KEY = "hr-platform-auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const { user: storedUser } = JSON.parse(stored);
        // Migrate old role format to new format
        if (storedUser.role && !["ADMIN", "RECRUITER"].includes(storedUser.role)) {
          storedUser.role = storedUser.role === "admin" ? "ADMIN" : "RECRUITER";
        }
        setUser(storedUser);
        setOrganization({
          id: storedUser.organizationId,
          name: storedUser.organizationName,
        });
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await mockAuth.login(email, password);
      
      if (response.success && response.data) {
        const { user: loggedInUser, token } = response.data;
        setUser(loggedInUser as User);
        setOrganization({
          id: loggedInUser.organizationId,
          name: loggedInUser.organizationName,
        });
        
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: loggedInUser, token }));
        return { success: true };
      }
      
      return { success: false, error: response.error || "Login failed" };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Login failed" };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await mockAuth.logout();
    } finally {
      setUser(null);
      setOrganization(null);
      localStorage.removeItem(STORAGE_KEY);
      setIsLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        organization,
        isLoading,
        isAuthenticated: !!user,
        isAdmin: user?.role === "ADMIN",
        login,
        logout,
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
