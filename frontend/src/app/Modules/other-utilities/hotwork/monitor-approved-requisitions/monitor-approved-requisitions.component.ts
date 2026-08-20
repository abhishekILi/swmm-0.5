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
import { ColDef, ICellRendererParams, CellCallbackParams } from "ag-grid-community";

// Shared Components
import { ExportToolbar, ExportKind } from "../../../../shared/components/export-toolbar/export-toolbar";
import { PanelCard } from "../../../../shared/components/panel-card/panel-card";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { DetailDrawer } from "../../../../shared/components/detail-drawer/detail-drawer";
import { IconComponent } from "../../../../shared/components/icon/icon.component";
import {
  CommonApiService,
  HotworkItem,
} from "../../../../Core/services/common/commonApiService";

export type SafeToWeldCertStatus = "Issued" | "Pending" | "N/A";
export type StartPauseStatus = "Not Started" | "In Progress" | "Paused" | "Completed";

export interface ApprovedRequisitionRow {
  ser: number;
  hotworkCode: string;
  dateOfHotwork: string;
  typeOfHotwork: string;
  departmentSubDept: string;
  department: string;
  subDepartment: string;
  hotworkLocation: string;
  adjacentCompartment: string;
  hotworkSentryNames: string;
  hotworkDescription: string;
  safeToWeldCert: SafeToWeldCertStatus;
  startPauseStatus: StartPauseStatus;
  isCompleted: boolean;
  rawApiItem?: HotworkItem;
}

@Component({
  selector: "app-monitor-approved-requisitions",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ExportToolbar,
    PanelCard,
    DataGrid,
    DetailDrawer,
    IconComponent,
  ],
  templateUrl: "./monitor-approved-requisitions.component.html",
  styleUrl: "./monitor-approved-requisitions.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonitorApprovedRequisitionsComponent implements OnInit {
  private readonly commonApiService = inject(CommonApiService);

  // Loading State
  readonly isLoading = signal<boolean>(false);

  // Top Filter Bar Signals
  readonly selectedDepartmentFilter = signal<string>("ALL");
  readonly selectedTypeFilter = signal<string>("ALL");
  readonly locationSearchInput = signal<string>("");

  // Applied Top Filters
  readonly appliedDept = signal<string>("ALL");
  readonly appliedType = signal<string>("ALL");
  readonly appliedLocation = signal<string>("");

  // Above Table Control Signals
  readonly scheduledTodayOnly = signal<boolean>(false);
  readonly globalSearch = signal<string>("");
  readonly pageSize = signal<number>(25);

  // Detail Drawer State
  readonly selectedRecord = signal<ApprovedRequisitionRow | null>(null);
  readonly actionSuccessMessage = signal<string | null>(null);
  readonly isActionInProgress = signal<boolean>(false);

  // Dropdown Options
  readonly departmentOptions: string[] = [
    "ALL",
    "ENGINEERING",
    "ELECTRICAL",
    "EXECUTIVE",
    "HULL & STRUCTURE",
    "WEAPONS & SENSORS",
    "LOGISTICS",
    "DAMAGE CONTROL",
  ];

  readonly typeOfHotworkOptions: string[] = [
    "ALL",
    "Gas Cutting",
    "Electric Arc Welding",
    "Grinding / Chipping",
    "Brazing / Soldering",
    "TIG / MIG Welding",
  ];

  // Master Data Signal (Strictly from API, no dummy fallback)
  readonly allRequisitions = signal<ApprovedRequisitionRow[]>([]);

  ngOnInit(): void {
    this.fetchRequisitions();
  }

  fetchRequisitions(): void {
    this.isLoading.set(true);
    this.commonApiService.getHotworkList().subscribe({
      next: (res) => {
        this.isLoading.set(false);
        if (res && Array.isArray(res)) {
          const mapped: ApprovedRequisitionRow[] = res.map(
            (item: HotworkItem, index: number) => {
              let safeToWeldCert: SafeToWeldCertStatus = "Pending";
              if (
                item.safe_cert === "Issued" ||
                item.safe_cert === "Pending" ||
                item.safe_cert === "N/A"
              ) {
                safeToWeldCert = item.safe_cert;
              }

              let startPauseStatus: StartPauseStatus = "Not Started";
              if (item.is_completed || item.current_status === "Completed") {
                startPauseStatus = "Completed";
              } else if (item.is_paused || item.current_status === "Paused") {
                startPauseStatus = "Paused";
              } else if (item.is_started || item.current_status === "In Progress") {
                startPauseStatus = "In Progress";
              }

              const dept = item.department_name || item.created_by_detail?.department || "Engineering";
              const subDept = item.sub_department_detail?.name || item.section_name || "";
              const deptSubDept =
                dept && subDept
                  ? `${dept} | ${subDept}`
                  : dept || subDept || "-";

              return {
                ser: index + 1,
                hotworkCode: item.hotwork_code || (item.id ? `HW-2026-${item.id}` : "-"),
                dateOfHotwork: item.date_of_hotwork || "-",
                typeOfHotwork: item.type_of_hotwork_display || item.type_of_hotwork || "-",
                departmentSubDept: deptSubDept,
                department: dept,
                subDepartment: subDept,
                hotworkLocation: item.location_of_hotwork || "-",
                adjacentCompartment: item.all_adjacent_compartments || item.adjacent_compartments || "-",
                hotworkSentryNames: item.sentry_names || "-",
                hotworkDescription: item.remarks || "-",
                safeToWeldCert,
                startPauseStatus,
                isCompleted: item.is_completed || item.current_status === "Completed",
                rawApiItem: item,
              };
            }
          );
          this.allRequisitions.set(mapped);
        } else {
          this.allRequisitions.set([]);
        }
      },
      error: (err) => {
        console.warn("API GET /api/v1/hotwork/ error:", err);
        this.isLoading.set(false);
        this.allRequisitions.set([]);
      },
    });
  }

  applyTopFilters(): void {
    this.appliedDept.set(this.selectedDepartmentFilter());
    this.appliedType.set(this.selectedTypeFilter());
    this.appliedLocation.set(this.locationSearchInput().trim());
  }

  clearAllFilters(): void {
    this.selectedDepartmentFilter.set("ALL");
    this.selectedTypeFilter.set("ALL");
    this.locationSearchInput.set("");
    this.appliedDept.set("ALL");
    this.appliedType.set("ALL");
    this.appliedLocation.set("");
    this.globalSearch.set("");
    this.scheduledTodayOnly.set(false);
  }

  // Computed Filtered List
  readonly filteredRows = computed(() => {
    let rows = this.allRequisitions();

    // Top Filter: Department
    const dept = this.appliedDept();
    if (dept !== "ALL") {
      rows = rows.filter(
        (r) =>
          r.department.toUpperCase() === dept.toUpperCase() ||
          r.departmentSubDept.toUpperCase().includes(dept.toUpperCase())
      );
    }

    // Top Filter: Type of Hotwork
    const hwType = this.appliedType();
    if (hwType !== "ALL") {
      rows = rows.filter(
        (r) => r.typeOfHotwork.toLowerCase() === hwType.toLowerCase()
      );
    }

    // Top Filter: Location
    const loc = this.appliedLocation();
    if (loc) {
      rows = rows.filter((r) => r.hotworkLocation.toLowerCase().includes(loc.toLowerCase()));
    }

    // Checkbox Filter: Scheduled for the Day
    if (this.scheduledTodayOnly()) {
      const todayStr = new Date().toISOString().slice(0, 10);
      const todayDisplay = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
      rows = rows.filter((r) => r.dateOfHotwork.includes(todayStr) || r.dateOfHotwork.includes(todayDisplay));
    }

    // Global Search Filter
    const gSearch = this.globalSearch().trim().toLowerCase();
    if (gSearch) {
      rows = rows.filter(
        (r) =>
          r.hotworkCode.toLowerCase().includes(gSearch) ||
          r.dateOfHotwork.toLowerCase().includes(gSearch) ||
          r.typeOfHotwork.toLowerCase().includes(gSearch) ||
          r.departmentSubDept.toLowerCase().includes(gSearch) ||
          r.hotworkLocation.toLowerCase().includes(gSearch) ||
          r.adjacentCompartment.toLowerCase().includes(gSearch) ||
          r.hotworkSentryNames.toLowerCase().includes(gSearch) ||
          r.hotworkDescription.toLowerCase().includes(gSearch)
      );
    }

    return rows;
  });

  // Action Helpers with API Integration
  toggleStartPause(row: ApprovedRequisitionRow, event?: Event): void {
    if (event) event.stopPropagation();
    const id = row.rawApiItem?.id || row.ser;
    const isRunning = row.startPauseStatus === "In Progress";

    if (isRunning) {
      // POST /api/v1/hotwork/{id}/pause/
      this.commonApiService
        .pauseHotwork(id, {
          current_status: "Paused",
          status: "Paused",
        })
        .subscribe({
          next: () => {
            this.updateRowStatus(row.hotworkCode, "Paused", false);
            this.actionSuccessMessage.set(`Hotwork ${row.hotworkCode} paused successfully.`);
          },
          error: (err) => {
            console.warn(`POST /api/v1/hotwork/${id}/pause/ error:`, err);
            this.updateRowStatus(row.hotworkCode, "Paused", false);
          },
        });
    } else {
      // POST /api/v1/hotwork/{id}/start/
      this.commonApiService
        .startHotwork(id, {
          current_status: "In Progress",
          status: "In Progress",
        })
        .subscribe({
          next: () => {
            this.updateRowStatus(row.hotworkCode, "In Progress", false);
            this.actionSuccessMessage.set(`Hotwork ${row.hotworkCode} started successfully.`);
          },
          error: (err) => {
            console.warn(`POST /api/v1/hotwork/${id}/start/ error:`, err);
            this.updateRowStatus(row.hotworkCode, "In Progress", false);
          },
        });
    }
  }

  markCompleted(row: ApprovedRequisitionRow, event?: Event): void {
    if (event) event.stopPropagation();
    const id = row.rawApiItem?.id || row.ser;

    // POST /api/v1/hotwork/{id}/complete/
    this.commonApiService
      .completeHotwork(id, {
        current_status: "Completed",
        status: "Completed",
      })
      .subscribe({
        next: () => {
          this.updateRowStatus(row.hotworkCode, "Completed", true);
          this.actionSuccessMessage.set(`Hotwork ${row.hotworkCode} marked as completed.`);
        },
        error: (err) => {
          console.warn(`POST /api/v1/hotwork/${id}/complete/ error:`, err);
          this.updateRowStatus(row.hotworkCode, "Completed", true);
        },
      });
  }

  private updateRowStatus(
    hotworkCode: string,
    status: StartPauseStatus,
    isCompleted: boolean
  ): void {
    const updated = this.allRequisitions().map((item) => {
      if (item.hotworkCode === hotworkCode) {
        return {
          ...item,
          startPauseStatus: status,
          isCompleted: isCompleted || item.isCompleted,
        };
      }
      return item;
    });
    this.allRequisitions.set(updated);
    if (this.selectedRecord()?.hotworkCode === hotworkCode) {
      this.selectedRecord.set(
        updated.find((r) => r.hotworkCode === hotworkCode) || null
      );
    }
  }

  // AG-Grid DataGrid Column Definitions matching standard application UI
  readonly columnDefs: ColDef[] = [
    { headerName: "SER", field: "ser", width: 70, minWidth: 60 },
    {
      headerName: "HOTWORK CODE",
      field: "hotworkCode",
      flex: 1.2,
      minWidth: 130,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "DATE OF HOTWORK",
      field: "dateOfHotwork",
      flex: 1.2,
      minWidth: 120,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "TYPE OF HOTWORK",
      field: "typeOfHotwork",
      flex: 1.3,
      minWidth: 140,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "DEPARTMENT | SUB-DEPARTMENT",
      field: "departmentSubDept",
      flex: 1.8,
      minWidth: 180,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "HOTWORK LOCATION",
      field: "hotworkLocation",
      flex: 1.5,
      minWidth: 160,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "ADJACENT COMPARTMENT",
      field: "adjacentCompartment",
      flex: 1.5,
      minWidth: 160,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "HOTWORK SENTRY NAMES",
      field: "hotworkSentryNames",
      flex: 1.5,
      minWidth: 160,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "HOTWORK DESCRIPTION",
      field: "hotworkDescription",
      flex: 2,
      minWidth: 180,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "SAFE TO WELD CERTIFICATE",
      field: "safeToWeldCert",
      flex: 1.5,
      minWidth: 160,
      filter: "agTextColumnFilter",
      cellRenderer: (params: ICellRendererParams) => {
        const cert = typeof params.value === "string" ? params.value : "Pending";
        const isIssued = cert.toUpperCase() === "ISSUED";
        const bg = isIssued ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)";
        const color = isIssued ? "#10b981" : "#f59e0b";
        const border = isIssued ? "rgba(16,185,129,0.3)" : "rgba(245,158,11,0.3)";
        return `<span style="padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background: ${bg}; color: ${color}; border: 1px solid ${border};">${cert}</span>`;
      },
    },
    {
      headerName: "START/ PAUSE HOTWORK",
      field: "startPauseStatus",
      flex: 1.6,
      minWidth: 170,
      onCellClicked: (params: CellCallbackParams) => {
        const data = params.data as ApprovedRequisitionRow | undefined;
        if (data && data.startPauseStatus !== "Completed") {
          this.toggleStartPause(data, params["event"] as Event);
        }
      },
      cellRenderer: (params: ICellRendererParams) => {
        const status = params.value as string;
        if (status === "Completed") {
          return `<span style="padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3);">Done</span>`;
        }
        const isRunning = status === "In Progress";
        let label = "Start";
        if (isRunning) {
          label = "Pause";
        } else if (status === "Paused") {
          label = "Resume";
        }
        const btnClass = isRunning
          ? "background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4);"
          : "background: rgba(14,165,233,0.2); color: #38bdf8; border: 1px solid rgba(14,165,233,0.4);";
        return `<button type="button" style="padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer; transition: all 0.2s; ${btnClass}">${label}</button>`;
      },
    },
    {
      headerName: "MARK AS COMPLETE",
      field: "isCompleted",
      flex: 1.5,
      minWidth: 150,
      onCellClicked: (params: CellCallbackParams) => {
        const data = params.data as ApprovedRequisitionRow | undefined;
        if (data && !data.isCompleted) {
          this.markCompleted(data, params["event"] as Event);
        }
      },
      cellRenderer: (params: ICellRendererParams) => {
        const row = params.data as ApprovedRequisitionRow | undefined;
        const isDone = params.value === true || row?.startPauseStatus === "Completed";
        if (isDone) {
          return `<span style="padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3);">Completed</span>`;
        }
        return `<button type="button" style="padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); cursor: pointer;">Complete</button>`;
      },
    },
  ];

  onRowClicked(event: unknown): void {
    if (event && typeof event === "object") {
      this.selectedRecord.set(event as ApprovedRequisitionRow);
      this.actionSuccessMessage.set(null);
    }
  }

  closeDrawer(): void {
    this.selectedRecord.set(null);
    this.actionSuccessMessage.set(null);
  }

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
      "Ser No",
      "Hotwork Code",
      "Date of Hotwork",
      "Type of Hotwork",
      "Department/Sub Dept",
      "Hotwork Location",
      "Adjacent Compartment",
      "Hotwork Sentry Names",
      "Hotwork Description",
      "Safe to Weld Certificate",
      "Start/Pause Status",
    ];
    const rows = this.filteredRows().map((r) => [
      r.ser,
      `"${r.hotworkCode}"`,
      `"${r.dateOfHotwork}"`,
      `"${r.typeOfHotwork}"`,
      `"${r.departmentSubDept}"`,
      `"${r.hotworkLocation}"`,
      `"${r.adjacentCompartment}"`,
      `"${r.hotworkSentryNames}"`,
      `"${r.hotworkDescription}"`,
      `"${r.safeToWeldCert}"`,
      `"${r.startPauseStatus}"`,
    ]);
    const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `monitor_approved_requisitions_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
}
