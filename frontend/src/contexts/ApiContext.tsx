/**
 * API Context
 * Provides centralized API access and settings management
 */

import React, { createContext, useContext, useState, useCallback } from "react";
import type { AppSettings } from "@/types";
import { mockSettingsApi } from "@/services/mockApi";

interface ApiContextType {
  settings: AppSettings;
  isLoading: boolean;
  updateSettings: (updates: Partial<AppSettings>) => Promise<void>;
  refreshSettings: () => Promise<void>;
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

  const refreshSettings = useCallback(async () => {
    setIsLoading(true);
    try {
      const fetched = await mockSettingsApi.get();
      setSettings(fetched);
    } catch (error) {
      console.error("Failed to fetch settings:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateSettings = useCallback(async (updates: Partial<AppSettings>) => {
    setIsLoading(true);
    try {
      const updated = await mockSettingsApi.update(updates);
      setSettings(updated);
    } catch (error) {
      console.error("Failed to update settings:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <ApiContext.Provider
      value={{ settings, isLoading, updateSettings, refreshSettings }}
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
