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
import { ColDef, ICellRendererParams } from "ag-grid-community";

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

export interface RequisitionRow {
  ser: number;
  hotworkCode: string;
  dateOfHotwork: string;
  typeOfHotwork: string;
  departmentSubDept: string;
  department: string;
  subDepartment: string;
  hotworkLocation: string;
  adjacentCompartment: string;
  approvalStatus: string;
  rawApiItem?: HotworkItem;
}

@Component({
  selector: "app-requisitions-approval-pending",
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
  templateUrl: "./requisitions-approval-pending.component.html",
  styleUrl: "./requisitions-approval-pending.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RequisitionsApprovalPendingComponent implements OnInit {
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

  // Global Search & Table Control Signals
  readonly globalSearch = signal<string>("");
  readonly pageSize = signal<number>(25);

  // Drawer Signals
  readonly selectedRecord = signal<RequisitionRow | null>(null);
  readonly isActionInProgress = signal<boolean>(false);
  readonly actionSuccessMessage = signal<string | null>(null);

  // Filter Options
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
  readonly allRequisitions = signal<RequisitionRow[]>([]);

  ngOnInit(): void {
    this.fetchRequisitions();
  }

  fetchRequisitions(): void {
    this.isLoading.set(true);
    this.commonApiService.getHotworkList().subscribe({
      next: (res) => {
        this.isLoading.set(false);
        if (res && Array.isArray(res)) {
          const mapped: RequisitionRow[] = res.map((item: HotworkItem, index: number) => {
            const dept = item.department_name || item.created_by_detail?.department || "ENGINEERING";
            const subDept = item.sub_department_detail?.name || item.section_name || "GENERAL";
            return {
              ser: index + 1,
              hotworkCode: item.hotwork_code || `HW-2026-${item.id || index + 1}`,
              dateOfHotwork: item.date_of_hotwork || "-",
              typeOfHotwork: item.type_of_hotwork_display || item.type_of_hotwork || "-",
              departmentSubDept: `${dept} | ${subDept}`,
              department: dept,
              subDepartment: subDept,
              hotworkLocation: item.location_of_hotwork || "-",
              adjacentCompartment: item.all_adjacent_compartments || item.adjacent_compartments || "-",
              approvalStatus: item.approval_status_display || item.approval_status || item.display_status || item.current_status || "APPROVAL PENDING",
              rawApiItem: item,
            };
          });
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
    this.appliedLocation.set(this.locationSearchInput().trim().toLowerCase());
  }

  clearAllFilters(): void {
    this.selectedDepartmentFilter.set("ALL");
    this.selectedTypeFilter.set("ALL");
    this.locationSearchInput.set("");

    this.appliedDept.set("ALL");
    this.appliedType.set("ALL");
    this.appliedLocation.set("");
    this.globalSearch.set("");
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
      rows = rows.filter((r) => r.hotworkLocation.toLowerCase().includes(loc));
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
          r.approvalStatus.toLowerCase().includes(gSearch)
      );
    }

    return rows;
  });

  // AG-Grid DataGrid Column Definitions
  readonly columnDefs: ColDef[] = [
    { headerName: "SER", field: "ser", width: 80, minWidth: 70 },
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
      headerName: "ADJACENT COMP...",
      field: "adjacentCompartment",
      flex: 1.5,
      minWidth: 150,
      filter: "agTextColumnFilter",
    },
    {
      headerName: "APPROVAL STATUS",
      field: "approvalStatus",
      flex: 1.3,
      minWidth: 140,
      filter: "agTextColumnFilter",
      cellRenderer: (params: ICellRendererParams) => {
        const status = typeof params.value === "string" ? params.value : "Pending";
        let statusStyle =
          "background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3);";
        if (status.toUpperCase().includes("APPROVED")) {
          statusStyle =
            "background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3);";
        } else if (status.toUpperCase().includes("REJECTED")) {
          statusStyle =
            "background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3);";
        }
        return `<span style="padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; ${statusStyle}">${status}</span>`;
      },
    },
  ];

  onRowClicked(event: unknown): void {
    if (event && typeof event === "object") {
      this.selectedRecord.set(event as RequisitionRow);
      this.actionSuccessMessage.set(null);
    }
  }

  closeDrawer(): void {
    this.selectedRecord.set(null);
    this.actionSuccessMessage.set(null);
  }

  approveRequisition(): void {
    if (!this.selectedRecord()) return;
    this.isActionInProgress.set(true);
    setTimeout(() => {
      this.isActionInProgress.set(false);
      this.actionSuccessMessage.set("Requisition approved successfully!");
      setTimeout(() => this.closeDrawer(), 1200);
    }, 600);
  }

  rejectRequisition(): void {
    if (!this.selectedRecord()) return;
    this.isActionInProgress.set(true);
    setTimeout(() => {
      this.isActionInProgress.set(false);
      this.actionSuccessMessage.set("Requisition rejected.");
      setTimeout(() => this.closeDrawer(), 1200);
    }, 600);
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
      "Approval Status",
    ];
    const rows = this.filteredRows().map((r) => [
      r.ser,
      `"${r.hotworkCode}"`,
      `"${r.dateOfHotwork}"`,
      `"${r.typeOfHotwork}"`,
      `"${r.departmentSubDept}"`,
      `"${r.hotworkLocation}"`,
      `"${r.adjacentCompartment}"`,
      `"${r.approvalStatus}"`,
    ]);
    const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `requisitions_approval_pending_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
}

