/**
 * Dashboard Page
 * Summary counts and recent activity
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Users,
  FileText,
  MessageSquare,
  Mail,
  Briefcase,
  UserCheck,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useApi } from "@/hooks/useApi";
import type { DashboardStats, ActivityItem } from "@/types";

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  description?: string;
}

function StatCard({ title, value, icon: Icon, description }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-5 w-5 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{value}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

const activityIcons: Record<ActivityItem["type"], React.ComponentType<{ className?: string }>> = {
  resume_uploaded: FileText,
  resume_parsed: FileText,
  message_sent: Mail,
  reply_received: MessageSquare,
  candidate_updated: Users,
};

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { getDashboardStats, getRecentActivity } = useApi();

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const [statsData, activityData] = await Promise.all([
          getDashboardStats(),
          getRecentActivity(),
        ]);
        if (statsData) setStats(statsData);
        if (activityData) setActivity(activityData);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, [getDashboardStats, getRecentActivity]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="Loading dashboard..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your recruiting pipeline
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/upload">
              <FileText className="h-4 w-4 mr-2" />
              Upload Resume
            </Link>
          </Button>
          <Button asChild>
            <Link to="/candidates">
              <Users className="h-4 w-4 mr-2" />
              View Candidates
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <StatCard
            title="Total Candidates"
            value={stats.totalCandidates}
            icon={Users}
          />
          <StatCard
            title="Resumes Processed"
            value={stats.resumesProcessed}
            icon={FileText}
          />
          <StatCard
            title="Messages Sent"
            value={stats.messagesSent}
            icon={Mail}
          />
          <StatCard
            title="Replies Received"
            value={stats.repliesReceived}
            icon={MessageSquare}
          />
          <StatCard
            title="Pending Jobs"
            value={stats.pendingJobs}
            icon={Briefcase}
          />
          <StatCard
            title="Interested"
            value={stats.interestedCandidates}
            icon={UserCheck}
          />
        </div>
      )}

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest updates from your pipeline</CardDescription>
        </CardHeader>
        <CardContent>
          {activity.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No recent activity
            </p>
          ) : (
            <div className="space-y-4">
              {activity.map((item) => {
                const Icon = activityIcons[item.type];
                return (
                  <div
                    key={item.id}
                    className="flex items-start gap-3 pb-4 border-b border-border last:border-0 last:pb-0"
                  >
                    <div className="rounded-full bg-muted p-2 flex-shrink-0">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground">{item.description}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {new Date(item.timestamp).toLocaleString()}
                      </p>
                    </div>
                    {item.candidateId && (
                      <Button asChild variant="ghost" size="sm">
                        <Link to={`/candidates/${item.candidateId}`}>
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}