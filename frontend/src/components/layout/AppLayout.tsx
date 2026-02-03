/**
 * App Layout Component
 * Main application layout with sidebar navigation
 */

import { useState } from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Upload,
  Settings,
  Briefcase,
  Menu,
  X,
  Moon,
  Sun,
  LogOut,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { useJobsContext } from "@/contexts/JobsContext";
import { Avatar } from "@/components/ui/Avatar";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Candidates", href: "/candidates", icon: Users },
  { label: "Upload", href: "/upload", icon: Upload },
  { label: "Jobs", href: "/jobs", icon: Briefcase, adminOnly: true },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { pendingCount } = useJobsContext();

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  // Filter nav items based on user role
  const visibleNavItems = navItems.filter(
    (item) => !item.adminOnly || isAdmin
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Skip link for accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 h-full w-64 bg-sidebar border-r border-sidebar-border transform transition-transform duration-200 ease-in-out lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-sidebar-border">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                <Users className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="font-semibold text-foreground">HR Intake</span>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {visibleNavItems.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                  {item.label === "Jobs" && pendingCount > 0 && (
                    <span className="ml-auto bg-primary text-primary-foreground text-xs px-2 py-0.5 rounded-full">
                      {pendingCount}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* User section */}
          {user && (
            <div className="p-4 border-t border-sidebar-border">
              <div className="flex items-center gap-3 mb-3">
                <Avatar name={user.name} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-foreground truncate">
                      {user.name}
                    </p>
                    {isAdmin && (
                      <Badge variant="outline" className="text-xs h-5 px-1.5 bg-primary/10 text-primary border-primary/20">
                        <Shield className="h-3 w-3 mr-1" />
                        Admin
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">
                    {user.organizationName}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex-1"
                  onClick={toggleTheme}
                >
                  {resolvedTheme === "dark" ? (
                    <Sun className="h-4 w-4 mr-2" />
                  ) : (
                    <Moon className="h-4 w-4 mr-2" />
                  )}
                  {resolvedTheme === "dark" ? "Light" : "Dark"}
                </Button>
                <Button variant="ghost" size="sm" onClick={logout}>
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Header */}
        <header className="sticky top-0 z-30 flex items-center h-16 px-4 bg-background/95 backdrop-blur border-b border-border lg:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden mr-2"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex-1" />
        </header>

        {/* Page content */}
        <main id="main-content" className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
