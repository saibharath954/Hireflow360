/**
 * Excel Export Service (Mock)
 * 
 * TODO: Replace with real Excel generation library (e.g., exceljs, xlsx)
 * Current implementation generates CSV for demo purposes
 */

import type { Candidate } from "@/types";

export interface ExportOptions {
  format: "xlsx" | "csv";
  includeMessages?: boolean;
  fields?: string[];
}

/**
 * Export candidates to Excel/CSV file
 * 
 * TODO: Implement real Excel export using exceljs
 * npm install exceljs
 * 
 * Example implementation:
 * import ExcelJS from 'exceljs';
 * const workbook = new ExcelJS.Workbook();
 * const worksheet = workbook.addWorksheet('Candidates');
 * worksheet.columns = [...]
 * worksheet.addRows(data);
 * return workbook.xlsx.writeBuffer();
 */
export const exportCandidatesToExcel = async (
  candidates: Candidate[],
  options: ExportOptions = { format: "csv" }
): Promise<Blob> => {
  const headers = [
    "Name",
    "Email",
    "Phone",
    "Years Experience",
    "Skills",
    "Current Company",
    "Education",
    "Location",
    "Status",
    "Overall Confidence",
    "Last Message",
    "Created At",
  ];

  const rows = candidates.map((c) => [
    c.name,
    c.email,
    c.phone || "",
    c.yearsExperience?.toString() || "",
    c.skills.join("; "),
    c.currentCompany || "",
    c.education || "",
    c.location || "",
    c.status,
    `${c.overallConfidence}%`,
    c.lastMessageAt || "",
    c.createdAt,
  ]);

  if (options.includeMessages) {
    headers.push("Messages");
    rows.forEach((row, index) => {
      const candidate = candidates[index];
      const messagesText = candidate.messages
        .map((m) => `[${m.direction}] ${m.content}`)
        .join(" | ");
      row.push(messagesText);
    });
  }

  // Generate CSV
  const escapeCSV = (value: string): string => {
    if (value.includes(",") || value.includes('"') || value.includes("\n")) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  };

  const csvContent = [
    headers.join(","),
    ...rows.map((row) => row.map(escapeCSV).join(",")),
  ].join("\n");

  // For actual XLSX, we would use a library
  if (options.format === "xlsx") {
    // TODO: Implement real XLSX export
    console.warn("XLSX export not implemented, falling back to CSV");
  }

  return new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
};

/**
 * Trigger file download in browser
 */
export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Export and download candidates
 */
export const exportAndDownload = async (
  candidates: Candidate[],
  options: ExportOptions = { format: "csv" }
): Promise<void> => {
  const blob = await exportCandidatesToExcel(candidates, options);
  const extension = options.format === "xlsx" ? "xlsx" : "csv";
  const filename = `candidates_export_${new Date().toISOString().split("T")[0]}.${extension}`;
  downloadBlob(blob, filename);
};
