import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router } from "@angular/router";
import { ColDef } from "ag-grid-community";
import { firstValueFrom } from "rxjs";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { IconComponent } from "../../../../shared/components/icon/icon.component";
import { KpiCard } from "../../../../shared/components/kpi-card/kpi-card";
import { HelpGuidance } from "../../../inventory/shared/components/help-guidance/help-guidance";
import { PrintColumn, ReportExportService } from "../../../../Core/services/generic-export-service/generic-export.service";
import { DropdownOption, SelectInput } from "../../../../shared/components/select-input/select-input";
import { CrewApiService } from "../../services/crew-api.service";
import { CrewDashboardCounts, CrewPersonnel, PersonnelStatus } from "../../models/crew.model";
import { PersonnelStatusTab } from "../../personnel-status/personnel-status.model";

const STATUS_FILTER_OPTIONS: { label: string; value: PersonnelStatus }[] = [
  { label: "Present", value: "Present" },
  { label: "On Leave", value: "On Leave" },
  { label: "Ty Duty", value: "Ty Duty" },
];

const PRINT_COLUMNS: PrintColumn[] = [
  { header: "Ser No.", field: "serNo" },
  { header: "Rank", field: "rank" },
  { header: "Name", field: "name" },
  { header: "Personnel Number", field: "pno" },
  { header: "Department", field: "department" },
  { header: "Designation", field: "designation" },
  { header: "Status", field: "status" },
];

interface CrewDashboardTile {
  title: string;
  count: number;
  icon: string;
  iconColor: string;
  iconBg: string;
  statusTab: PersonnelStatusTab;
}

const CREW_BASE = "/afterAuth/Ship_Crew_and_HR";

const OFFICER_RANKS = ["cdr", "lt cdr", "capt", "captain", "commodore", "cdre", "lt", "lieutenant", "sub lt"];

@Component({
  selector: "app-crew-dashboard",
  standalone: true,
  imports: [FormsModule, DataGrid, IconComponent, KpiCard, HelpGuidance, SelectInput],
  templateUrl: "./crew-dashboard.html",
  styleUrl: "./crew-dashboard.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CrewDashboard implements OnInit {
  private readonly api = inject(CrewApiService);
  private readonly router = inject(Router);
  private readonly exportService = inject(ReportExportService);

  readonly today = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });
  readonly personnel = signal<CrewPersonnel[]>([]);
  readonly tiles = signal<CrewDashboardTile[]>([]);
  readonly category = signal<"all" | "officer" | "sailor">("all");
  readonly deptFilter = signal("");
  readonly statusFilter = signal<"" | PersonnelStatus>("");
  readonly statusFilterOptions = STATUS_FILTER_OPTIONS;

  readonly departments = computed(() =>
    [...new Set(this.personnel().map((p) => p.department))].sort((a, b) => a.localeCompare(b)),
  );
  readonly departmentOptions = computed<DropdownOption[]>(() => this.departments().map((d) => ({ label: d, value: d })));

  readonly filteredRows = computed(() => {
    const cat = this.category();
    const dept = this.deptFilter();
    const status = this.statusFilter();
    return this.personnel().filter((p) => {
      const isOfficer = OFFICER_RANKS.some((r) => p.rank.toLowerCase().includes(r));
      if (cat === "officer" && !isOfficer) return false;
      if (cat === "sailor" && isOfficer) return false;
      if (dept && p.department !== dept) return false;
      if (status && p.status !== status) return false;
      return true;
    });
  });

  readonly columnDefs: ColDef[] = [
    { colId: "serNo", headerName: "Ser No.", valueGetter: (p) => Number(p.node?.["rowIndex"] ?? 0) + 1, width: 90 },
    { field: "rank", headerName: "Rank", width: 120 },
    {
      colId: "name",
      headerName: "Name",
      valueGetter: (p) => `${(p.data as CrewPersonnel).firstName} ${(p.data as CrewPersonnel).lastName}`,
      flex: 1,
    },
    { field: "pno", headerName: "Personnel Number", width: 160 },
    { field: "department", headerName: "Department", width: 150 },
    { field: "designation", headerName: "Designation", flex: 1 },
    { field: "status", headerName: "Status", width: 120 },
  ];

  ngOnInit(): void {
    void this.load();
  }

  private async load(): Promise<void> {
    const [counts, personnel] = await Promise.all([
      firstValueFrom(this.api.getDashboardCounts()),
      firstValueFrom(this.api.getPersonnel()),
    ]);
    this.personnel.set(personnel);
    this.tiles.set(this.buildTiles(counts));
  }

  private buildTiles(counts: CrewDashboardCounts): CrewDashboardTile[] {
    return [
      { title: "Total Strength", count: counts.total, icon: "users", iconColor: "#0095ff", iconBg: "rgba(0,149,255,0.12)", statusTab: "all" },
      {
        title: "Present",
        count: counts.present,
        icon: "circle-check-big",
        iconColor: "#28a745",
        iconBg: "rgba(40,167,69,0.12)",
        statusTab: "present",
      },
      {
        title: "On Leave",
        count: counts.onLeave,
        icon: "circle-x",
        iconColor: "#dc3545",
        iconBg: "rgba(220,53,69,0.12)",
        statusTab: "leave",
      },
      {
        title: "On Ty Duty",
        count: counts.tyDuty,
        icon: "clock",
        iconColor: "#d97706",
        iconBg: "rgba(217,119,6,0.12)",
        statusTab: "ty",
      },
    ];
  }

  /** Mirrors Django's KPI "View more" links to `crew/personnel_status/?tab=...`. */
  viewMore(statusTab: PersonnelStatusTab): void {
    void this.router.navigate([`${CREW_BASE}/personnel-status`], { queryParams: { tab: statusTab } });
  }

  setCategory(cat: "all" | "officer" | "sailor"): void {
    this.category.set(cat);
  }

  onDeptChange(value: unknown): void {
    this.deptFilter.set(typeof value === "string" ? value : "");
  }

  setStatusFilter(status: "" | PersonnelStatus): void {
    this.statusFilter.set(status);
  }

  clearFilters(): void {
    this.category.set("all");
    this.deptFilter.set("");
    this.statusFilter.set("");
  }

  private get exportRows(): Record<string, unknown>[] {
    return this.filteredRows().map((p, i) => ({
      serNo: i + 1,
      rank: p.rank,
      name: `${p.firstName} ${p.lastName}`,
      pno: p.pno,
      department: p.department,
      designation: p.designation ?? "",
      status: p.status,
    }));
  }

  downloadCsv(): void {
    this.exportService.downloadCsv(
      PRINT_COLUMNS,
      this.exportRows,
      `ship_crew_personnel_${new Date().toISOString().slice(0, 10)}.csv`,
    );
  }

  downloadPdf(): void {
    this.exportService.printRows(`Personnel Borne as on ${this.today}`, PRINT_COLUMNS, this.exportRows);
  }
}
