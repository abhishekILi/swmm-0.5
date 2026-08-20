import {
  Component,
  ChangeDetectionStrategy,
  signal,
  computed,
  inject,
  OnInit,
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";

// Shared Components
import {
  ExportToolbar,
  ExportKind,
} from "../../../../shared/components/export-toolbar/export-toolbar";
import { PanelCard } from "../../../../shared/components/panel-card/panel-card";
import { DatePickerComponent } from "../../../../shared/components/date-picker/picker";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { ColDef, ICellRendererParams } from "ag-grid-community";
import {
  CommonApiService,
  HotworkTrackingItem,
} from "../../../../Core/services/common/commonApiService";

export interface HotworkRecord {
  sNo: number;
  hotworkCode: string;
  parentCode: string;
  dateOfHotwork: string;
  departmentSection: string;
  descriptionOfHotwork: string;
  locationAdjacent: string;
  hotworkType: string;
  currentStatus: "Active" | "Pending" | "Paused" | "Completed";
  safeToWeldCert: "Issued" | "Pending" | "N/A";
}

function parseDateRange(rawDateRange: unknown): {
  startDateStr: string;
  endDateStr: string;
} {
  if (typeof rawDateRange === "string") {
    if (rawDateRange.includes("-")) {
      const parts = rawDateRange.split("-").map((s) => s.trim());
      return {
        startDateStr: parts[0] || "",
        endDateStr: parts[1] || parts[0] || "",
      };
    }
    const trimmed = rawDateRange.trim();
    return { startDateStr: trimmed, endDateStr: trimmed };
  }
  if (rawDateRange && typeof rawDateRange === "object") {
    const dr = rawDateRange as { start?: string; end?: string };
    return {
      startDateStr: dr.start || "",
      endDateStr: dr.end || dr.start || "",
    };
  }
  return { startDateStr: "", endDateStr: "" };
}

function isDateWithinRange(
  dateOfHotwork: string,
  startDateStr: string,
  endDateStr: string,
): boolean {
  if (!startDateStr || !dateOfHotwork || dateOfHotwork === "-") return true;

  const itemDate = new Date(dateOfHotwork).getTime();
  const start = new Date(startDateStr).getTime();
  const end = new Date(endDateStr).getTime();

  if (Number.isNaN(itemDate) || Number.isNaN(start)) return true;
  if (itemDate < start) return false;
  if (!Number.isNaN(end) && itemDate > end) return false;

  return true;
}

function matchesSearch(r: HotworkRecord, search: string): boolean {
  if (!search) return true;
  return (
    r.sNo.toString().includes(search) ||
    r.hotworkCode.toLowerCase().includes(search) ||
    r.parentCode.toLowerCase().includes(search) ||
    r.dateOfHotwork.toLowerCase().includes(search) ||
    r.departmentSection.toLowerCase().includes(search) ||
    r.descriptionOfHotwork.toLowerCase().includes(search) ||
    r.locationAdjacent.toLowerCase().includes(search) ||
    r.hotworkType.toLowerCase().includes(search) ||
    r.currentStatus.toLowerCase().includes(search)
  );
}

import { DetailDrawer } from "../../../../shared/components/detail-drawer/detail-drawer";

@Component({
  selector: "app-hotwork-history",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ExportToolbar,
    PanelCard,
    DatePickerComponent,
    DataGrid,
    DetailDrawer,
  ],
  templateUrl: "./hotwork-history.component.html",
  styleUrl: "./hotwork-history.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HotworkHistoryComponent implements OnInit {
  private readonly commonApiService = inject(CommonApiService);

  readonly selectedRecord = signal<HotworkRecord | null>(null);

  onRowClicked(row: unknown): void {
    if (row && typeof row === "object") {
      this.selectedRecord.set(row as HotworkRecord);
    }
  }

  closeDrawer(): void {
    this.selectedRecord.set(null);
  }

  // Master Hotwork Records (Populated dynamically from API)
  readonly hotworkRecords = signal<HotworkRecord[]>([]);

  ngOnInit(): void {
    this.commonApiService.getHotworkTrackingList().subscribe({
      next: (res) => {
        if (res && Array.isArray(res)) {
          const mapped: HotworkRecord[] = res.map(
            (item: HotworkTrackingItem, index: number) => {
              let locAdj = item.location_of_hotwork || "-";
              if (item.all_adjacent_compartments) {
                locAdj += ` (${item.all_adjacent_compartments})`;
              }

              return {
                sNo: index + 1,
                hotworkCode:
                  item.previous_hotwork_code ||
                  item.dl_number ||
                  `HW-2026-00${item.id}`,
                parentCode: item.dl_number || item.previous_hotwork_code || "-",
                dateOfHotwork: item.date_of_hotwork || "-",
                departmentSection: item.departmental_officer || "ENGINEERING",
                descriptionOfHotwork:
                  item.remarks || item.type_of_hotwork || "-",
                locationAdjacent: locAdj,
                hotworkType: item.type_of_hotwork || "Welding",
                currentStatus: item.night_work ? "Active" : "Completed",
                safeToWeldCert: item.sentries_required ? "Issued" : "Pending",
              };
            },
          );
          this.hotworkRecords.set(mapped);
        } else {
          this.hotworkRecords.set([]);
        }
      },
      error: (err) => {
        console.warn("API GET /api/v1/hotwork/tracking/ error:", err);
        this.hotworkRecords.set([]);
      },
    });
  }

  // AG-Grid DataGrid Column Definitions for History Table
  readonly historyColumnDefs: ColDef[] = [
    { headerName: "Sr No", field: "sNo", width: 90, minWidth: 80 },
    {
      headerName: "Hotwork Code",
      field: "hotworkCode",
      flex: 1.2,
      minWidth: 130,
    },
    { headerName: "Parent Code", field: "parentCode", flex: 1, minWidth: 110 },
    {
      headerName: "Date of Hotwork",
      field: "dateOfHotwork",
      flex: 1.2,
      minWidth: 130,
    },
    {
      headerName: "Department/Section",
      field: "departmentSection",
      flex: 1.3,
      minWidth: 140,
    },
    {
      headerName: "Description of Hotwork",
      field: "descriptionOfHotwork",
      flex: 2,
      minWidth: 180,
    },
    {
      headerName: "Location/Adjacent Compartments",
      field: "locationAdjacent",
      flex: 2,
      minWidth: 180,
    },
    {
      headerName: "Hotwork Type",
      field: "hotworkType",
      flex: 1.1,
      minWidth: 110,
    },
    {
      headerName: "Current Status",
      field: "currentStatus",
      flex: 1.1,
      minWidth: 110,
      cellRenderer: (params: ICellRendererParams) => {
        const status =
          typeof params.value === "string" ? params.value : "Pending";
        let statusStyle =
          "background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3);";
        if (status === "Active") {
          statusStyle =
            "background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3);";
        } else if (status === "Completed") {
          statusStyle =
            "background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3);";
        }
        return `<span style="padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; ${statusStyle}">${status}</span>`;
      },
    },
    {
      headerName: "Safe To Weld Cert",
      field: "safeToWeldCert",
      flex: 1.2,
      minWidth: 130,
      cellRenderer: (params: ICellRendererParams) => {
        const cert = typeof params.value === "string" ? params.value : "N/A";
        return `<span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: rgba(6,78,59,0.6); color: #34d399; border: 1px solid rgba(6,95,70,0.6);">${cert}</span>`;
      },
    },
  ];

  // Filters
  readonly historyHotworkCode = signal<string>("ALL");
  readonly historyDateRange = signal<string | null>("");
  readonly historyGlobalSearch = signal<string>("");
  readonly historyPageSize = signal<number>(10);

  readonly filteredHistoryRecords = computed(() => {
    const list = this.hotworkRecords();
    const selCode = this.historyHotworkCode();
    const search = this.historyGlobalSearch().toLowerCase().trim();
    const { startDateStr, endDateStr } = parseDateRange(
      this.historyDateRange(),
    );

    return list.filter(
      (r) =>
        (selCode === "ALL" || r.hotworkCode === selCode) &&
        isDateWithinRange(r.dateOfHotwork, startDateStr, endDateStr) &&
        matchesSearch(r, search),
    );
  });

  onExport(kind: ExportKind): void {
    if (kind === "pdf") {
      window.print();
    } else if (kind === "excel") {
      this.downloadCSV();
    } else if (kind === "print") {
      window.print();
    }
  }

  downloadCSV(): void {
    const headers = [
      "Sr No",
      "Hotwork Code",
      "Parent Code",
      "Date of Hotwork",
      "Department/Section",
      "Description of Hotwork",
      "Location/Adjacent Compartments",
      "Hotwork Type",
      "Current Status",
    ];
    const rows = this.filteredHistoryRecords().map((r) => [
      r.sNo,
      `"${r.hotworkCode}"`,
      `"${r.parentCode}"`,
      `"${r.dateOfHotwork}"`,
      `"${r.departmentSection}"`,
      `"${r.descriptionOfHotwork}"`,
      `"${r.locationAdjacent}"`,
      `"${r.hotworkType}"`,
      `"${r.currentStatus}"`,
    ]);
    const csvContent = [
      headers.join(","),
      ...rows.map((e) => e.join(",")),
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `HotworkHistory_${new Date().toISOString().slice(0, 10)}.csv`,
    );
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  copyData(): void {
    const headers = [
      "Sr No",
      "Hotwork Code",
      "Parent Code",
      "Date of Hotwork",
      "Department/Section",
      "Description of Hotwork",
      "Location/Adjacent Compartments",
      "Hotwork Type",
      "Current Status",
    ];
    const rows = this.filteredHistoryRecords().map((r) =>
      [
        r.sNo,
        r.hotworkCode,
        r.parentCode,
        r.dateOfHotwork,
        r.departmentSection,
        r.descriptionOfHotwork,
        r.locationAdjacent,
        r.hotworkType,
        r.currentStatus,
      ].join("\t"),
    );
    const text = [headers.join("\t"), ...rows].join("\n");
    navigator.clipboard.writeText(text);
  }
}
