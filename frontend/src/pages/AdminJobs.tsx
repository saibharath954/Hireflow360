/**
 * Admin Jobs Page - Background job status
 */
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useApi } from "@/hooks/useApi";
import type { Job } from "@/types";

const statusColors: Record<string, string> = {
  queued: "bg-muted text-muted-foreground",
  processing: "bg-warning/10 text-warning",
  completed: "bg-success/10 text-success",
  failed: "bg-destructive/10 text-destructive",
};

export default function AdminJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { getJobs } = useApi();

  useEffect(() => {
    const load = async () => { setJobs(await getJobs()); setIsLoading(false); };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [getJobs]);

  if (isLoading) return <div className="flex justify-center h-64"><LoadingSpinner size="lg" /></div>;

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold">Background Jobs</h1><p className="text-muted-foreground">{jobs.length} jobs</p></div>
      <Card>
        <CardHeader><CardTitle>Job Queue</CardTitle></CardHeader>
        <CardContent>
          {jobs.length === 0 ? <p className="text-center text-muted-foreground py-8">No jobs</p> : (
            <Table>
              <TableHeader><TableRow><TableHead>Type</TableHead><TableHead>Status</TableHead><TableHead>Created</TableHead><TableHead>Completed</TableHead></TableRow></TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell className="font-medium capitalize">{job.type.replace(/_/g, " ")}</TableCell>
                    <TableCell><Badge className={statusColors[job.status]}>{job.status}</Badge></TableCell>
                    <TableCell className="text-sm text-muted-foreground">{new Date(job.createdAt).toLocaleString()}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{job.completedAt ? new Date(job.completedAt).toLocaleString() : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
