/**
 * Settings Page - Mode toggle, theme, export options
 */
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useTheme } from "@/contexts/ThemeContext";
import { useApiContext } from "@/contexts/ApiContext";
import { useToastContext } from "@/contexts/ToastContext";
import { mockExportApi } from "@/services/mockApi";
import { Download, RefreshCw } from "lucide-react";
import { useState } from "react";

export default function Settings() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { settings, updateSettings } = useApiContext();
  const toast = useToastContext();
  const [isSyncing, setIsSyncing] = useState(false);

  const handleModeToggle = async () => {
    await updateSettings({ mode: settings.mode === "mock" ? "automation" : "mock" });
    toast.info("Mode changed", `Now using ${settings.mode === "mock" ? "automation" : "mock"} mode`);
  };

  const handleSync = async () => {
    setIsSyncing(true);
    const result = await mockExportApi.syncGoogleSheets();
    if (result.success) {
      toast.success("Sync complete", `${result.data?.rowCount} rows synced`);
    } else {
      toast.error("Sync failed", result.error);
    }
    setIsSyncing(false);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-bold">Settings</h1></div>
      <Card>
        <CardHeader><CardTitle>Operation Mode</CardTitle><CardDescription>Mock mode simulates all actions. Automation mode would use real integrations.</CardDescription></CardHeader>
        <CardContent className="flex items-center justify-between">
          <Label htmlFor="mode">Automation Mode</Label>
          <Switch id="mode" checked={settings.mode === "automation"} onCheckedChange={handleModeToggle} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Appearance</CardTitle></CardHeader>
        <CardContent className="flex items-center justify-between">
          <Label htmlFor="theme">Dark Mode</Label>
          <Switch id="theme" checked={resolvedTheme === "dark"} onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Integrations</CardTitle><CardDescription>Connect external services</CardDescription></CardHeader>
        <CardContent className="space-y-3">
          <Button variant="outline" className="w-full" onClick={handleSync} disabled={isSyncing}>
            {isSyncing ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
            Sync to Google Sheets
          </Button>
          <p className="text-xs text-muted-foreground">TODO: Configure Google Sheets integration in production</p>
        </CardContent>
      </Card>
    </div>
  );
}
