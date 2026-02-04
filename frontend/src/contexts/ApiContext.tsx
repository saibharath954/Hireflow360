/**
 * Updated API Context
 * Manages API settings and configuration
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { AppSettings } from "@/types";
import { api } from "@/services/api";

interface ApiContextType {
  settings: AppSettings;
  isLoading: boolean;
  updateSettings: (updates: Partial<AppSettings>) => Promise<void>;
  refreshSettings: () => Promise<void>;
  isMockMode: boolean;
}

const defaultSettings: AppSettings = {
  mode: "mock",
  theme: "light",
  defaultIntentTemplates: [],
};

const ApiContext = createContext<ApiContextType | undefined>(undefined);

export function ApiProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // Load settings on mount
  useEffect(() => {
    if (!isInitialized) {
      refreshSettings();
      setIsInitialized(true);
    }
  }, [isInitialized]);

  const refreshSettings = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.settings.get();
      if (response.success && response.data) {
        setSettings(response.data);
      } else {
        console.error("Failed to fetch settings:", response.error);
        // Use defaults if API fails
        setSettings(defaultSettings);
      }
    } catch (error) {
      console.error("Error fetching settings:", error);
      setSettings(defaultSettings);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateSettings = useCallback(async (updates: Partial<AppSettings>) => {
    setIsLoading(true);
    try {
      const response = await api.settings.update(updates);
      if (response.success && response.data) {
        setSettings(response.data);
      } else {
        throw new Error(response.error || "Failed to update settings");
      }
    } catch (error) {
      console.error("Error updating settings:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <ApiContext.Provider
      value={{
        settings,
        isLoading,
        updateSettings,
        refreshSettings,
        isMockMode: settings.mode === "mock",
      }}
    >
      {children}
    </ApiContext.Provider>
  );
}

export function useApiContext() {
  const context = useContext(ApiContext);
  if (context === undefined) {
    throw new Error("useApiContext must be used within an ApiProvider");
  }
  return context;
}