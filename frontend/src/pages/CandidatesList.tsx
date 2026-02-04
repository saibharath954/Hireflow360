/**
 * Candidates List Page
 * Main table with search, filters, and candidate overview
 */

import { useEffect, useState, useMemo, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Search,
  Filter,
  Download,
  RefreshCw,
  ChevronDown,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { TagList } from "@/components/ui/TagList";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BadgeConfidence } from "@/components/ui/BadgeConfidence";
import { Avatar } from "@/components/ui/Avatar";
import { useApi } from "@/hooks/useApi";
import { useDebounce } from "@/hooks/useDebounce";
import { useToastContext } from "@/contexts/ToastContext";
import { exportAndDownload } from "@/services/excelService";
import type { Candidate, CandidateFilters, PaginatedResponse } from "@/types";
import type { CandidateStatus } from "@/styles/design-tokens";

const statusOptions: { value: CandidateStatus; label: string }[] = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "interested", label: "Interested" },
  { value: "not_interested", label: "Not Interested" },
  { value: "needs_clarification", label: "Needs Clarification" },
];

export default function CandidatesList() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 50,
    total: 0,
    hasMore: false,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<CandidateStatus[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [isExporting, setIsExporting] = useState(false);

  const navigate = useNavigate();
  const { getCandidates } = useApi();
  const toast = useToastContext();
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Get unique skills from all candidates
  const allSkills = useMemo(() => {
    const skills = new Set<string>();
    candidates.forEach((c) => c.skills.forEach((s) => skills.add(s)));
    return Array.from(skills).sort();
  }, [candidates]);

  // Build filters
  const filters: CandidateFilters = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      status: selectedStatuses.length > 0 ? selectedStatuses : undefined,
      skills: selectedSkills.length > 0 ? selectedSkills : undefined,
    }),
    [debouncedSearch, selectedStatuses, selectedSkills]
  );

  const loadCandidates = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getCandidates(filters, pagination.page, pagination.pageSize);
      if (data) {
        setCandidates(data.items);
        setPagination({
          page: data.page,
          pageSize: data.pageSize,
          total: data.total,
          hasMore: data.hasMore,
        });
      }
    } catch (error) {
      console.error("Failed to load candidates:", error);
      toast.error("Error", "Failed to load candidates");
    } finally {
      setIsLoading(false);
    }
  }, [getCandidates, filters, pagination.page, pagination.pageSize, toast]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await exportAndDownload(candidates, { format: "csv" });
      toast.success("Export complete", "Candidates exported to CSV");
    } catch {
      toast.error("Export failed", "Could not export candidates");
    }
    setIsExporting(false);
  };

  const toggleStatus = (status: CandidateStatus) => {
    setSelectedStatuses((prev) =>
      prev.includes(status)
        ? prev.filter((s) => s !== status)
        : [...prev, status]
    );
  };

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill)
        ? prev.filter((s) => s !== skill)
        : [...prev, skill]
    );
  };

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedStatuses([]);
    setSelectedSkills([]);
  };

  const hasFilters = searchQuery || selectedStatuses.length > 0 || selectedSkills.length > 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Candidates</h1>
          <p className="text-muted-foreground">
            {pagination.total} candidate{pagination.total !== 1 ? "s" : ""} in pipeline
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadCandidates} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={isExporting}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search by name, email, skills, company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Status filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              <Filter className="h-4 w-4 mr-2" />
              Status
              {selectedStatuses.length > 0 && (
                <span className="ml-2 bg-primary text-primary-foreground text-xs px-1.5 rounded">
                  {selectedStatuses.length}
                </span>
              )}
              <ChevronDown className="h-4 w-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel>Filter by status</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {statusOptions.map((option) => (
              <DropdownMenuCheckboxItem
                key={option.value}
                checked={selectedStatuses.includes(option.value)}
                onCheckedChange={() => toggleStatus(option.value)}
              >
                {option.label}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Skills filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              Skills
              {selectedSkills.length > 0 && (
                <span className="ml-2 bg-primary text-primary-foreground text-xs px-1.5 rounded">
                  {selectedSkills.length}
                </span>
              )}
              <ChevronDown className="h-4 w-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48 max-h-64 overflow-y-auto">
            <DropdownMenuLabel>Filter by skills</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {allSkills.slice(0, 20).map((skill) => (
              <DropdownMenuCheckboxItem
                key={skill}
                checked={selectedSkills.includes(skill)}
                onCheckedChange={() => toggleSkill(skill)}
              >
                {skill}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {hasFilters && (
          <Button variant="ghost" onClick={clearFilters}>
            Clear filters
          </Button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" text="Loading candidates..." />
        </div>
      ) : candidates.length === 0 ? (
        <EmptyState
          type="candidates"
          title="No candidates found"
          description={
            hasFilters
              ? "Try adjusting your filters or search query"
              : "Upload resumes to start building your pipeline"
          }
          action={
            hasFilters ? (
              <Button variant="outline" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : (
              <Button asChild>
                <Link to="/upload">Upload Resume</Link>
              </Button>
            )
          }
        />
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[250px]">Candidate</TableHead>
                <TableHead>Experience</TableHead>
                <TableHead className="hidden md:table-cell">Skills</TableHead>
                <TableHead className="hidden lg:table-cell">Company</TableHead>
                <TableHead className="hidden lg:table-cell">Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden md:table-cell">Confidence</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {candidates.map((candidate) => (
                <TableRow
                  key={candidate.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => navigate(`/candidates/${candidate.id}`)}
                >
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar name={candidate.name} size="sm" />
                      <div className="min-w-0">
                        <p className="font-medium truncate">{candidate.name}</p>
                        <p className="text-sm text-muted-foreground truncate">
                          {candidate.email}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {candidate.yearsExperience !== undefined
                      ? `${candidate.yearsExperience} years`
                      : "—"}
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    <TagList tags={candidate.skills} limit={3} />
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    {candidate.currentCompany || "—"}
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    {candidate.location || "—"}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={candidate.status} />
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    <BadgeConfidence confidence={candidate.overallConfidence} size="sm" />
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" asChild>
                      <Link
                        to={`/candidates/${candidate.id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}