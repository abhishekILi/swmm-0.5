import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { BarChart, StackedBarSeries } from "../../../../shared/components/bar-chart/bar-chart";
import { DonutChart, DonutSegment } from "../../../../shared/components/donut-chart/donut-chart";
import { IconComponent } from "../../../../shared/components/icon/icon.component";
import { KpiCard } from "../../../../shared/components/kpi-card/kpi-card";
import { HelpGuidance } from "../../../inventory/shared/components/help-guidance/help-guidance";
import { DropdownOption, SelectInput } from "../../../../shared/components/select-input/select-input";
import { CrewApiService } from "../../services/crew-api.service";
import { CrewPersonnel, LeaveApplication } from "../../models/crew.model";

type ForecastTab = "dashboard" | "forecast" | "history";
type CategoryFilter = "all" | "officer" | "sailor";

const CATEGORY_OPTIONS: DropdownOption[] = [
  { label: "Officer & Sailor", value: "all" },
  { label: "Officer", value: "officer" },
  { label: "Sailor", value: "sailor" },
];

const FORECAST_TYPE_OPTIONS: DropdownOption[] = [
  { label: "Leave & TY Duty", value: "" },
  { label: "On Leave", value: "On Leave" },
  { label: "TY Duty", value: "Ty Duty" },
];

const OFFICER_RANKS = ["cdr", "lt cdr", "capt", "captain", "commodore", "cdre", "lt", "lieutenant", "sub lt"];
const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

@Component({
  selector: "app-leave-forecast",
  standalone: true,
  imports: [FormsModule, BarChart, DonutChart, IconComponent, KpiCard, HelpGuidance, SelectInput],
  templateUrl: "./leave-forecast.html",
  styleUrl: "./leave-forecast.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LeaveForecast implements OnInit {
  private readonly api = inject(CrewApiService);

  readonly activeTab = signal<ForecastTab>("dashboard");
  readonly personnel = signal<CrewPersonnel[]>([]);
  readonly forecastEntries = signal<LeaveApplication[]>([]);
  readonly historyEntries = signal<LeaveApplication[]>([]);

  readonly forecastTypeFilter = signal<"" | "On Leave" | "Ty Duty">("");
  readonly historySearch = signal("");
  readonly deptFilter = signal("");
  readonly categoryFilter = signal<CategoryFilter>("all");

  readonly departments = computed(() => [...new Set(this.personnel().map((p) => p.department))].sort((a, b) => a.localeCompare(b)));
  readonly departmentOptions = computed<DropdownOption[]>(() => this.departments().map((d) => ({ label: d, value: d })));
  readonly categoryOptions = CATEGORY_OPTIONS;
  readonly forecastTypeOptions = FORECAST_TYPE_OPTIONS;

  private isOfficer(rank: string): boolean {
    return OFFICER_RANKS.some((r) => rank.toLowerCase().includes(r));
  }

  readonly filteredPersonnel = computed(() => {
    const dept = this.deptFilter();
    const cat = this.categoryFilter();
    return this.personnel().filter((p) => {
      if (dept && p.department !== dept) return false;
      if (cat === "officer" && !this.isOfficer(p.rank)) return false;
      if (cat === "sailor" && this.isOfficer(p.rank)) return false;
      return true;
    });
  });

  /** `forecastEntries()` scoped by the Department / Officer & Sailor filters — backs every
   * dashboard KPI card and the trend charts below. */
  readonly scopedForecast = computed(() => {
    const dept = this.deptFilter();
    const cat = this.categoryFilter();
    return this.forecastEntries().filter((a) => {
      if (dept && (a.department ?? "") !== dept) return false;
      if (cat === "officer" && !this.isOfficer(a.rank)) return false;
      if (cat === "sailor" && this.isOfficer(a.rank)) return false;
      return true;
    });
  });

  readonly totalPersonnel = computed(() => this.filteredPersonnel().length);
  readonly janJunCount = computed(
    () => this.scopedForecast().filter((a) => a.applicationStatus === "Approved" && +a.startDate.slice(5, 7) <= 6).length,
  );
  readonly julDecCount = computed(
    () => this.scopedForecast().filter((a) => a.applicationStatus === "Approved" && +a.startDate.slice(5, 7) > 6).length,
  );
  readonly pendingCount = computed(() => this.scopedForecast().filter((a) => a.applicationStatus === "Pending").length);
  readonly percentOnLeave = computed(() => {
    const total = this.totalPersonnel();
    if (!total) return 0;
    const approvedToday = this.scopedForecast().filter((a) => a.applicationStatus === "Approved").length;
    return Math.round((approvedToday / total) * 100);
  });

  readonly filteredForecast = computed(() => {
    const type = this.forecastTypeFilter();
    return this.scopedForecast().filter((a) => !type || a.leaveType === type);
  });

  readonly filteredHistory = computed(() => {
    const q = this.historySearch().trim().toLowerCase();
    return this.historyEntries().filter((a) => !q || a.name.toLowerCase().includes(q) || a.personalNumber.toLowerCase().includes(q));
  });

  // ── Monthly Trend & Distribution ────────────────────────────
  readonly monthLabels = MONTH_LABELS.map((m) => `${m}'${new Date().getFullYear().toString().slice(2)}`);

  readonly monthlyTrendSeries = computed<StackedBarSeries[]>(() => {
    const entries = this.scopedForecast();
    const onLeave = new Array(12).fill(0);
    const tyDuty = new Array(12).fill(0);
    for (const a of entries) {
      const month = +a.startDate.slice(5, 7) - 1;
      if (month < 0 || month > 11) continue;
      if (a.leaveType === "On Leave") onLeave[month]++;
      else tyDuty[month]++;
    }
    return [
      { name: "On Leave", color: "#dc3545", data: onLeave },
      { name: "Ty Duty", color: "#ffc107", data: tyDuty },
    ];
  });

  readonly typeBreakdownSegments = computed<DonutSegment[]>(() => {
    const entries = this.scopedForecast();
    return [
      { label: "On Leave", value: entries.filter((a) => a.leaveType === "On Leave").length, color: "#dc3545" },
      { label: "Ty Duty", value: entries.filter((a) => a.leaveType === "Ty Duty").length, color: "#ffc107" },
    ];
  });

  readonly deptWiseAbsence = computed(() => {
    const byDept = new Map<string, number>();
    for (const a of this.scopedForecast()) {
      const dept = a.department || "Unassigned";
      byDept.set(dept, (byDept.get(dept) ?? 0) + 1);
    }
    return [...byDept.entries()].map(([label, value]) => ({ label, value }));
  });

  ngOnInit(): void {
    void this.load();
  }

  selectTab(tab: ForecastTab): void {
    this.activeTab.set(tab);
  }

  onDeptChange(value: unknown): void {
    this.deptFilter.set(typeof value === "string" ? value : "");
  }

  onCategoryChange(value: unknown): void {
    this.categoryFilter.set((typeof value === "string" ? value : "all") as CategoryFilter);
  }

  onForecastTypeChange(value: unknown): void {
    this.forecastTypeFilter.set((value === "On Leave" || value === "Ty Duty" ? value : "") as "" | "On Leave" | "Ty Duty");
  }

  resetFilters(): void {
    this.deptFilter.set("");
    this.categoryFilter.set("all");
  }

  private async load(): Promise<void> {
    const [personnel, mine, pending, history] = await Promise.all([
      firstValueFrom(this.api.getPersonnel()),
      firstValueFrom(this.api.getMyApplications()),
      firstValueFrom(this.api.getPendingApplications()),
      firstValueFrom(this.api.getLeaveHistory()),
    ]);
    this.personnel.set(personnel);
    const byId = new Map<number, LeaveApplication>();
    [...mine, ...pending].forEach((a) => byId.set(a.id, a));
    this.forecastEntries.set([...byId.values()]);
    this.historyEntries.set(history);
  }

  async approve(id: number): Promise<void> {
    if (!confirm("Approve this application?")) return;
    await firstValueFrom(this.api.actionLeave(id, "Approved"));
    await this.load();
  }

  async reject(id: number): Promise<void> {
    const reason = prompt("Rejection reason (optional):") ?? "";
    await firstValueFrom(this.api.actionLeave(id, "Rejected", reason));
    await this.load();
  }

  exportHistoryCsv(): void {
    const headers = ["Name", "PNo", "Rank", "Department", "Type", "Start", "End", "Days", "Status", "Station"];
    const rows = this.filteredHistory().map((a) => [
      a.name,
      a.personalNumber,
      a.rank,
      a.department ?? "",
      a.leaveType,
      a.startDate,
      a.endDate,
      a.noOfDays,
      a.applicationStatus,
      a.station ?? "",
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.map((v) => `"${v}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "leave_history.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }
}
