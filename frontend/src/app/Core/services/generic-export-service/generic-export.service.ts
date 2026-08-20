import { Injectable } from "@angular/core";
import { firstValueFrom, Observable } from "rxjs";

export type ExportJobStatus = "pending" | "running" | "success" | "failed";

export interface ExportJobLike {
  id: string;
  status: ExportJobStatus;
  error_message?: string | null;
}

export interface ExportJobRunner<TJob extends ExportJobLike> {
  request: () => Observable<TJob>;
  getStatus: (jobId: string) => Observable<TJob>;
  download: (jobId: string) => Observable<Blob>;
}

export interface PrintColumn {
  header: string;
  field: string;
  format?: (value: unknown) => string;
}

export interface PreviewWindowOptions {
  download?: { blob: Blob; filename: string };
  print?: boolean;
}

const POLL_INTERVAL_MS = 2000;
const POLL_MAX_ATTEMPTS = 30;

@Injectable({ providedIn: "root" })
export class ReportExportService {
  async exportFile<TJob extends ExportJobLike>(
    runner: ExportJobRunner<TJob>,
  ): Promise<Blob> {
    let job = await firstValueFrom(runner.request());
    let attempt = 0;
    while (this.isPending(job.status) && attempt < POLL_MAX_ATTEMPTS) {
      await this.delay(POLL_INTERVAL_MS);
      job = await firstValueFrom(runner.getStatus(job.id));
      attempt++;
    }
    if (this.isPending(job.status)) {
      throw new Error(
        "Export is taking longer than expected. Please try again shortly.",
      );
    }
    if (job.status !== "success") {
      throw new Error(job.error_message || "Export failed.");
    }
    return firstValueFrom(runner.download(job.id));
  }

  downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  /** Opens a loading skeleton then a printable preview window in one call — the common case for
   * an <app-export-toolbar> "print"/"pdf" click on a page that has no server-side report job. */
  printRows(title: string, columns: PrintColumn[], rows: Record<string, unknown>[]): void {
    const win = this.openLoadingWindow(title, columns.length, rows.length);
    if (!win) return;
    this.renderPreviewWindow(win, title, columns, rows, { print: true });
  }

  /** Client-side CSV export for pages with no dedicated backend export endpoint — same
   * `PrintColumn[]` shape used for print, so one column list drives both. */
  downloadCsv(columns: PrintColumn[], rows: Record<string, unknown>[], filename: string): void {
    const csvCell = (value: string) => `"${value.replace(/"/g, '""')}"`;
    const header = columns.map((c) => csvCell(c.header)).join(",");
    const body = rows
      .map((row) => columns.map((c) => csvCell(this.formatExportCell(c, row))).join(","))
      .join("\n");
    this.downloadBlob(new Blob([header + "\n" + body], { type: "text/csv;charset=utf-8;" }), filename);
  }

  /** Copies rows as tab-separated text — pastes cleanly into Excel/Sheets. */
  async copyRows(columns: PrintColumn[], rows: Record<string, unknown>[]): Promise<void> {
    const header = columns.map((c) => c.header).join("\t");
    const body = rows
      .map((row) => columns.map((c) => this.formatExportCell(c, row)).join("\t"))
      .join("\n");
    await navigator.clipboard.writeText(header + "\n" + body);
  }

  private formatExportCell(column: PrintColumn, row: Record<string, unknown>): string {
    const raw = row[column.field];
    if (column.format) return column.format(raw);
    if (raw === null || raw === undefined) return "";
    return raw instanceof Date ? raw.toLocaleString() : String(raw as string | number | boolean);
  }

  openLoadingWindow(
    title: string,
    columnCount = 6,
    rowCount = 6,
  ): Window | null {
    const win = window.open("", "_blank");
    if (!win) {
      console.warn("Unable to open the preview window (popup blocked?).");
      return null;
    }
    win.document.documentElement.innerHTML =
      "<head><title>" +
      this.escapeHtml(title) +
      "</title><style>" +
      this.loadingSkeletonCss() +
      "</style></head><body>" +
      this.loadingSkeletonHtml(Math.max(1, columnCount), Math.max(1, rowCount)) +
      "</body>";
    return win;
  }
  private loadingSkeletonHtml(columnCount: number, rowCount: number): string {
    const widths = [92, 68, 84, 60, 76, 55];
    const cell = (pct: number) =>
      '<div class="skel-cell"><span class="skel-bar" style="width:' + pct + '%"></span></div>';
    const row = (cls: string, offset: number) =>
      '<div class="skel-row ' +
      cls +
      '">' +
      Array.from({ length: columnCount }, (_, i) => cell(widths[(i + offset) % widths.length])).join("") +
      "</div>";

    const headRow = row("skel-row--head", 0);
    const bodyRows = Array.from({ length: rowCount }, (_, r) => row("", r + 1)).join("");

    return (
      '<div class="skel-header">' +
      '<div class="skel-title"></div>' +
      '<div class="skel-toolbar"><span class="skel-toolbar-btn"></span></div>' +
      "</div>" +
      '<div class="skel-wrap">' +
      '<div class="skel-table">' +
      headRow +
      bodyRows +
      "</div>" +
      "</div>"
    );
  }

  private loadingSkeletonCss(): string {
    return (
      "body{font-family:Arial,sans-serif;padding:24px;color:#111;margin:0;background:#fff;}" +
      ".skel-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px;}" +
      ".skel-toolbar{display:flex;flex-shrink:0;gap:10px;}" +
      ".skel-toolbar-btn{width:88px;height:32px;border-radius:8px;background:#e3e3e3;}" +
      ".skel-title{height:18px;width:240px;border-radius:4px;background:#e3e3e3;}" +
      ".skel-wrap{position:relative;overflow:hidden;}" +
      ".skel-wrap:after{content:\"\";position:absolute;top:0;left:0;width:100%;height:100%;" +
      "background:linear-gradient(110deg,rgba(255,255,255,0) 0%,rgba(255,255,255,0) 40%," +
      "rgba(255,255,255,0.7) 50%,rgba(255,255,255,0) 60%,rgba(255,255,255,0) 100%);" +
      "animation:skel-shimmer 1.2s linear infinite;}" +
      ".skel-table{border:1px solid #ccc;border-collapse:collapse;}" +
      ".skel-row{display:flex;}" +
      ".skel-row--head{background:#f2f2f2;}" +
      ".skel-cell{flex:1;min-width:0;box-sizing:border-box;padding:6px 10px;border:1px solid #e2e2e2;}" +
      ".skel-bar{display:block;height:10px;border-radius:3px;background:#cacaca;}" +
      ".skel-row--head .skel-bar{background:#b7b7b7;}" +
      "@keyframes skel-shimmer{0%{transform:translateX(-100%);}100%{transform:translateX(100%);}}"
    );
  }

  renderPreviewWindow(
    win: Window,
    title: string,
    columns: PrintColumn[],
    rows: Record<string, unknown>[],
    options: PreviewWindowOptions,
  ): void {
    if (win.closed) return;

    const headerCells = columns
      .map((c) => "<th>" + this.escapeHtml(c.header) + "</th>")
      .join("");
    const bodyRows = rows
      .map((row) => {
        const cells = columns
          .map((c) => {
            const raw = row[c.field];
            let value = "";
            if (c.format) {
              value = c.format(raw);
            } else if (raw !== null && raw !== undefined) {
              if (raw instanceof Date) {
                value = raw.toLocaleString();
              } else if (typeof raw === "object") {
                value = JSON.stringify(raw);
              } else {
                value = String(raw as string | number | boolean);
              }
            }
            return "<td>" + this.escapeHtml(value) + "</td>";
          })
          .join("");
        return "<tr>" + cells + "</tr>";
      })
      .join("");

    const toolbarButtons =
      (options.download
        ? '<button id="app-preview-download" type="button" class="app-preview-btn">Download</button>'
        : "") +
      (options.print
        ? '<button id="app-preview-print" type="button" class="app-preview-btn">Print</button>'
        : "");

    win.document.documentElement.innerHTML =
      "<head><title>" +
      this.escapeHtml(title) +
      "</title><style>" +
      "body{font-family:Arial,sans-serif;padding:24px;color:#111;}" +
      ".app-preview-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px;}" +
      ".app-preview-toolbar{display:flex;flex-shrink:0;gap:10px;}" +
      ".app-preview-btn{padding:9px 18px;border-radius:8px;border:1px solid #1d96e9;background:#1d96e9;color:#fff;font-size:13px;font-family:inherit;cursor:pointer;}" +
      "h1{font-size:18px;margin:0;}" +
      "table{width:100%;border-collapse:collapse;}" +
      "th,td{border:1px solid #ccc;padding:6px 10px;font-size:12px;text-align:left;}" +
      "th{background:#f2f2f2;}" +
      "@media print{.app-preview-toolbar{display:none;}}" +
      "</style></head><body>" +
      '<div class="app-preview-header">' +
      "<h1>" +
      this.escapeHtml(title) +
      "</h1>" +
      '<div class="app-preview-toolbar">' +
      toolbarButtons +
      "</div>" +
      "</div>" +
      "<table><thead><tr>" +
      headerCells +
      "</tr></thead><tbody>" +
      bodyRows +
      "</tbody></table>" +
      "</body>";

    if (options.download) {
      const { blob, filename } = options.download;
      const url = URL.createObjectURL(blob);
      win.document.getElementById("app-preview-download")?.addEventListener("click", () => {
        const anchor = win.document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        anchor.click();
      });
      win.addEventListener("unload", () => URL.revokeObjectURL(url), { once: true });
    }

    if (options.print) {
      win.document.getElementById("app-preview-print")?.addEventListener("click", () => win.print());
      win.setTimeout(() => win.print(), 0);
    }
  }

  showPreviewError(win: Window, message: string): void {
    if (win.closed) return;
    win.document.documentElement.innerHTML =
      "<body style=\"font-family:Arial,sans-serif;padding:24px;color:#b00020;\">" +
      this.escapeHtml(message) +
      "</body>";
  }

  private isPending(status: ExportJobStatus): boolean {
    return status === "pending" || status === "running";
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private escapeHtml(value: string): string {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }
}
