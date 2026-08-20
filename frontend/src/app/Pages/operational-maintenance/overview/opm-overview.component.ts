import { ChangeDetectionStrategy, Component, computed, HostListener, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { FormsModule } from "@angular/forms";
import { ColDef } from "ag-grid-community";

import { OPM_DART_REASONS } from "../actions/opm-actions-fields.config";
import { OpmDartReason } from "../actions/opm-actions.models";

import {
  BarChart,
  BarDatum,
  ChartLegend,
  CustomizeKpi,
  DataGrid,
  DetailDrawer,
  DropdownOption,
  GridStatusChipRenderer,
  KpiCard,
  LineChart,
  PanelCard,
  PillToggle,
} from "../../../shared/components";
import { IconComponent } from "../../../shared/components/icon/icon.component";
import { DonutChart } from "../../../shared/components/donut-chart/donut-chart";
import { SelectInput } from "../../../shared/components/select-input/select-input";
import { KpiPanelService } from "../../../Core/services/kpi-panel.service";

import { OpmActivityRow, OpmAlert, OpmDeptDatum, OpmOverviewKpi, OpmQuickAction } from "./opm-overview.model";
import {
  OPM_ACTIVITY,
  OPM_ALERTS,
  OPM_DEPT,
  OPM_DEPT_LOAD,
  OPM_DEPT_SUBS,
  OPM_OVERVIEW_KPIS,
  OPM_OVERVIEW_PANEL_ICONS,
  OPM_QUICK_ACTIONS,
  OPM_SEVERITY,
  OPM_SEVERITY_TOTAL,
  OPM_TREND_LABELS,
  OPM_TREND_LEGEND,
  OPM_TREND_SERIES,
  toBarData,
} from "./opm-overview.data";

function trendDirection(trend: string, fallback: boolean): boolean {
  const t = trend.trim();
  if (t.startsWith("-")) return false;
  if (t.startsWith("+")) return true;
  return fallback;
}

/**
 * Operational Maintenance — Overview tab. A dashboard composed entirely from
 * shared widgets (app-kpi-card, app-customize-kpi, app-panel-card,
 * app-bar-chart, app-line-chart, app-chart-legend, app-pill-toggle,
 * app-data-grid, app-detail-drawer). Data is dummy/in-memory only — no API.
 */
@Component({
  selector: "app-opm-overview",
  standalone: true,
  imports: [KpiCard, CustomizeKpi, DetailDrawer, PanelCard, ChartLegend, PillToggle, BarChart, LineChart, DataGrid, IconComponent, DonutChart, SelectInput, FormsModule],
  templateUrl: "./opm-overview.component.html",
  styleUrls: ["./opm-overview.component.css"],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OpmOverviewComponent {
  readonly kpiPanel = inject(KpiPanelService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly icons = OPM_OVERVIEW_PANEL_ICONS;

  // --- KPIs -----------------------------------------------------------------
  readonly allKpis = signal<OpmOverviewKpi[]>(OPM_OVERVIEW_KPIS);
  readonly visibleKpis = signal<OpmOverviewKpi[]>(OPM_OVERVIEW_KPIS.slice(0, 4));

  updateSelectedKpis(selected: OpmOverviewKpi[]): void {
    this.visibleKpis.set(selected.length ? selected : this.allKpis().slice(0, 4));
  }

  onPeriodChange(key: string, period: string): void {
    this.visibleKpis.update((kpis) =>
      kpis.map((k) => {
        if (k.key !== key) return k;
        return {
          ...k,
          selectedPeriod: period,
          displayValue: k.valueData[period] ?? k.displayValue,
          trendUp: trendDirection(k.trendData[period] ?? "", k.baseUp),
        };
      }),
    );
  }

  // --- Alerts + quick actions ----------------------------------------------
  readonly alerts = signal(OPM_ALERTS);

  // Alert detail drawer (opened on alert click; rows/action deep-link into a tab).
  readonly alertIconName = OPM_OVERVIEW_PANEL_ICONS.alerts;
  readonly activeAlert = signal<OpmAlert | null>(null);
  readonly alertDrawerOpen = signal(false);

  openAlert(alert: OpmAlert): void {
    this.activeAlert.set(alert);
    this.alertDrawerOpen.set(true);
  }

  closeAlert(): void {
    this.alertDrawerOpen.set(false);
  }

  /** Deep-link from an alert drawer (row click or footer action) to the relevant tab. */
  navFromAlert(alert: OpmAlert): void {
    this.closeAlert();
    const child = this.route.snapshot.paramMap.get("child") ?? "defect";
    const target: Record<OpmAlert["nav"], { tab: string; queryParams?: Record<string, string> }> = {
      actions: { tab: "actions" },
      approval: { tab: "actions", queryParams: { view: "approval" } },
      guarantee: { tab: "actions", queryParams: { view: "guarantee" } },
      reports: { tab: "reports" },
    };
    const { tab, queryParams } = target[alert.nav];
    this.router.navigate(["/afterAuth/op-maintenance", child, tab], { queryParams });
  }

  // "Add Defect / DART" is a dropdown (Reason → Add form); the rest are plain deep-link buttons.
  readonly quickActions: OpmQuickAction[] = OPM_QUICK_ACTIONS.filter((a) => a.label !== "Add Defect / DART");

  onQuickAction(action: OpmQuickAction): void {
    const child = this.route.snapshot.paramMap.get("child") ?? "defect";
    this.router.navigate(["/afterAuth/op-maintenance", child, action.tab], { queryParams: action.queryParams });
  }

  // --- "Add Defect / DART" dropdown (Reason → Add form) --------------------
  readonly qaReasons: OpmDartReason[] = OPM_DART_REASONS;
  readonly qaOpen = signal(false);

  toggleQaMenu(): void {
    this.qaOpen.update((v) => !v);
  }

  closeQaMenu(): void {
    this.qaOpen.set(false);
  }

  /** Deep-link into the Add Defect / DART form (actions tab) with the picked reason. */
  selectReason(reason: string): void {
    this.closeQaMenu();
    const child = this.route.snapshot.paramMap.get("child") ?? "defect";
    this.router.navigate(["/afterAuth/op-maintenance", child, "actions"], {
      queryParams: { view: "add", reason },
    });
  }

  @HostListener("document:click")
  onDocumentClick(): void {
    if (this.qaOpen()) this.closeQaMenu();
  }

  // --- Open DARTs by department (bar chart + drill-down) --------------------
  private readonly dept = signal<OpmDeptDatum[]>(OPM_DEPT);
  private readonly deptSubs: Record<string, OpmDeptDatum[]> = OPM_DEPT_SUBS;

  readonly distDeptOpts = computed<DropdownOption[]>(() =>
    ["All Departments", ...this.dept().map((d) => d.label)].map((label) => ({ label, value: label })),
  );
  readonly distDrill = signal<string | null>(null);
  readonly distDeptValue = computed(() => this.distDrill() ?? "All Departments");

  readonly distData = computed<BarDatum[]>(() => {
    const drill = this.distDrill();
    const source = drill ? this.deptSubs[drill] ?? this.dept() : this.dept();
    return toBarData(source);
  });

  readonly distTitle = computed(() => {
    const drill = this.distDrill();
    return drill ? `${drill} — Sub-Departments` : "Open DARTs by Department";
  });

  readonly distSubtitle = computed(() =>
    this.distDrill()
      ? "Active DARTs by sub-department · select All Departments to return"
      : "Active DARTs across each ship department · pick a department to drill down",
  );

  readonly distXAxis = computed(() => (this.distDrill() ? "Sub-Departments" : "Departments"));

  onDistDeptChange(value: string): void {
    this.distDrill.set(this.deptSubs[value] ? value : null);
  }

  // --- DART lifecycle trend (line chart) -----------------------------------
  readonly trendLabels = OPM_TREND_LABELS;
  readonly trendSeries = OPM_TREND_SERIES;
  readonly trendLegend = OPM_TREND_LEGEND;

  // --- Open DARTs by Operational Severity (donut) --------------------------
  readonly severity = OPM_SEVERITY;
  readonly severityTotal = OPM_SEVERITY_TOTAL;

  // --- DART Load by Department (horizontal bars) ---------------------------
  readonly deptLoad = (() => {
    const max = Math.max(1, ...OPM_DEPT_LOAD.map((d) => d.value));
    return OPM_DEPT_LOAD.map((d) => ({
      label: d.label,
      value: d.value,
      pct: Math.round((d.value / max) * 100),
      top: d.value === max,
    }));
  })();

  /** DART-load rows as horizontal-bar data (the top department is highlighted). */
  readonly deptLoadBars: BarDatum[] = this.deptLoad.map((d) => ({
    label: d.label,
    value: d.value,
    primary: d.top,
  }));

  // --- Recent activity (data grid + period pills) --------------------------
  readonly activityColDefs: ColDef[] = [
    { headerName: "Date", field: "date", flex: 0.8, minWidth: 100 },
    { headerName: "Equipment / Service", field: "equip", flex: 2, minWidth: 200 },
    {
      headerName: "Action",
      field: "action",
      flex: 0.9,
      minWidth: 120,
      cellRenderer: GridStatusChipRenderer,
      cellRendererParams: { toneMap: { Raised: "info", Closed: "success" } },
    },
    { headerName: "Department", field: "dept", flex: 1.4, minWidth: 160 },
    { headerName: "Reason", field: "ship", flex: 1.4, minWidth: 150 },
    {
      headerName: "Status",
      field: "status",
      flex: 0.9,
      minWidth: 120,
      cellRenderer: GridStatusChipRenderer,
      cellRendererParams: { toneMap: { Verified: "success", "In Progress": "warning" } },
    },
  ];

  readonly periodOpts = ["Today", "Week", "Month", "Quarter", "Year"];
  readonly actPeriod = signal("Month");
  private readonly periodDays: Record<string, number> = { Today: 1, Week: 7, Month: 30, Quarter: 90, Year: 365 };

  private readonly activity = signal<OpmActivityRow[]>(OPM_ACTIVITY);

  readonly activityRows = computed<OpmActivityRow[]>(() => {
    const limit = this.periodDays[this.actPeriod()] ?? 30;
    return this.activity().filter((r) => r.d <= limit);
  });

  readonly activityPage = signal(1);
  readonly activityPageSize = signal(10);

  readonly activityPageRows = computed<OpmActivityRow[]>(() => {
    const size = this.activityPageSize();
    const start = (this.activityPage() - 1) * size;
    return this.activityRows().slice(start, start + size);
  });

  setActPeriod(p: string): void {
    this.actPeriod.set(p);
    this.activityPage.set(1);
  }

  onActivityPageRequested(event: { page: number; pageSize: number }): void {
    this.activityPage.set(event.page);
    this.activityPageSize.set(event.pageSize);
  }

  // --- KPI detail drawer ----------------------------------------------------
  readonly drawerOpen = signal(false);
  readonly activeKpi = signal<OpmOverviewKpi | null>(null);

  openDetail(kpi: OpmOverviewKpi): void {
    this.activeKpi.set(kpi);
    this.drawerOpen.set(true);
  }

  closeDetail(): void {
    this.drawerOpen.set(false);
  }
}
