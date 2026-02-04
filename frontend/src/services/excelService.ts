/**
 * Excel Export Service
 * Handles downloading of exported data
 */

export interface ExportOptions {
  format: "xlsx" | "csv";
  includeMessages?: boolean;
}

export async function exportAndDownload(data: any, options: ExportOptions): Promise<void> {
  try {
    // Convert data to Blob based on format
    let blob: Blob;
    let filename: string;
    
    if (options.format === "csv") {
      const csvContent = convertToCSV(data);
      blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      filename = `candidates_${new Date().toISOString().split('T')[0]}.csv`;
    } else {
      // For XLSX, we would use a library like xlsx
      // This is a simplified version - in production, you'd use the actual XLSX library
      const jsonStr = JSON.stringify(data, null, 2);
      blob = new Blob([jsonStr], { type: "application/json" });
      filename = `candidates_${new Date().toISOString().split('T')[0]}.json`;
    }
    
    // Create download link
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Export failed:", error);
    throw new Error("Failed to export data");
  }
}

function convertToCSV(data: any[]): string {
  if (!data.length) return "";
  
  // Extract headers from first object
  const headers = Object.keys(data[0]);
  
  // Create CSV content
  const csvRows = [
    headers.join(","),
    ...data.map(row => 
      headers.map(header => {
        const value = row[header];
        // Escape quotes and wrap in quotes if contains comma or quotes
        const escaped = ('' + value).replace(/"/g, '""');
        return escaped.includes(',') || escaped.includes('"') || escaped.includes('\n') 
          ? `"${escaped}"` 
          : escaped;
      }).join(',')
    )
  ];
  
  return csvRows.join('\n');
}