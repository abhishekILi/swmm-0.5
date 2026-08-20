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
import { Router, ActivatedRoute } from "@angular/router";

// Shared Components from src/app/shared/components
import { KpiCard } from "../../../../shared/components/kpi-card/kpi-card";
import { PanelCard } from "../../../../shared/components/panel-card/panel-card";
import { DatePickerComponent } from "../../../../shared/components/date-picker/picker";
import {
  LineChart,
  LineSeries,
} from "../../../../shared/components/line-chart/line-chart";
import {
  BarChart,
  BarDatum,
} from "../../../../shared/components/bar-chart/bar-chart";
import {
  DonutChart,
  DonutSegment,
} from "../../../../shared/components/donut-chart/donut-chart";
import {
  CommonApiService,
  HotworkDashboardData,
  HotworkItem,
} from "../../../../Core/services/common/commonApiService";

@Component({
  selector: "app-hotwork-dashboard",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    KpiCard,
    PanelCard,
    DatePickerComponent,
    LineChart,
    BarChart,
    DonutChart,
  ],
  templateUrl: "./hotwork-dashboard.component.html",
  styleUrl: "./hotwork-dashboard.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HotworkDashboardComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly commonApiService = inject(CommonApiService);

  // KPI Counter Signals
  readonly scheduledToday = signal<number>(0);
  readonly inProgress = signal<number>(0);
  readonly awaitingApproval = signal<number>(0);
  readonly completed = signal<number>(0);
  readonly readyToStart = signal<number>(0);

  ngOnInit(): void {
    this.commonApiService.getHotworkDashboardData().subscribe({
      next: (res: HotworkDashboardData) => {
        const hasSummary =
          res?.summary &&
          (res.summary.scheduled_today ||
            res.summary.in_progress ||
            res.summary.awaiting_approval ||
            res.summary.completed ||
            res.summary.ready_to_start);

        if (hasSummary) {
          this.applyDashboardData(res);
        } else {
          this.loadFallbackFromList();
        }
      },
      error: () => {
        this.loadFallbackFromList();
      },
    });
  }

  private applyDashboardData(res: HotworkDashboardData): void {
    if (res.summary) {
      this.scheduledToday.set(res.summary.scheduled_today || 0);
      this.inProgress.set(res.summary.in_progress || 0);
      this.awaitingApproval.set(res.summary.awaiting_approval || 0);
      this.completed.set(res.summary.completed || 0);
      this.readyToStart.set(res.summary.ready_to_start || 0);
    }

    if (
      res.weekly_summary &&
      Array.isArray(res.weekly_summary) &&
      res.weekly_summary.length > 0
    ) {
      const labels = res.weekly_summary.map((item) => item.date);
      const initiatedVals = res.weekly_summary.map((item) => item.initiated);
      const readyVals = res.weekly_summary.map((item) => item.ready);
      const completedVals = res.weekly_summary.map((item) => item.completed);

      this.weeklyLabels.set(labels);
      this.weeklySeries.set([
        { label: "Initiated", color: "#f59e0b", values: initiatedVals },
        { label: "Ready", color: "#ef4444", values: readyVals },
        { label: "Completed", color: "#3b82f6", values: completedVals },
      ]);
    }

    if (res.present_progress) {
      const p = res.present_progress;
      this.progressSegments.set([
        { label: "Initiated", value: p.initiated || 0, color: "#f59e0b" },
        { label: "Ready", value: p.ready || 0, color: "#f97316" },
        { label: "Paused", value: p.paused || 0, color: "#ef4444" },
        { label: "Completed", value: p.completed || 0, color: "#3b82f6" },
      ]);

      this.historyBarData.set([
        {
          label: "Ready",
          value: p.ready || 0,
          color: "#38bdf8",
          primary: true,
        },
        {
          label: "In progress",
          value: res.summary?.in_progress || 0,
          color: "#3b82f6",
          primary: true,
        },
        {
          label: "Completed",
          value: p.completed || 0,
          color: "#a855f7",
          primary: true,
        },
      ]);
    }
  }

  private loadFallbackFromList(): void {
    this.commonApiService.getHotworkList().subscribe({
      next: (items: HotworkItem[]) => {
        if (items && Array.isArray(items)) {
          let scheduled = 0;
          let inProg = 0;
          let awaiting = 0;
          let comp = 0;
          let ready = 0;

          items.forEach((item) => {
            const status = (
              item.current_status ||
              item.approval_status ||
              ""
            ).toLowerCase();
            if (status.includes("progress") || status.includes("in_progress")) {
              inProg++;
            } else if (
              status.includes("awaiting") ||
              status.includes("pending")
            ) {
              awaiting++;
            } else if (status.includes("complete")) {
              comp++;
            } else if (status.includes("ready")) {
              ready++;
            } else {
              scheduled++;
            }
          });

          this.scheduledToday.set(scheduled || items.length);
          this.inProgress.set(inProg);
          this.awaitingApproval.set(awaiting);
          this.completed.set(comp);
          this.readyToStart.set(ready);

          this.progressSegments.set([
            { label: "Initiated", value: scheduled, color: "#f59e0b" },
            { label: "Ready", value: ready, color: "#f97316" },
            { label: "Paused", value: 0, color: "#ef4444" },
            { label: "Completed", value: comp, color: "#3b82f6" },
          ]);

          this.historyBarData.set([
            { label: "Ready", value: ready, color: "#38bdf8", primary: true },
            {
              label: "In progress",
              value: inProg,
              color: "#3b82f6",
              primary: true,
            },
            {
              label: "Completed",
              value: comp,
              color: "#a855f7",
              primary: true,
            },
          ]);
        }
      },
      error: (err) => {
        console.warn("Fallback list load failed", err);
      },
    });
  }

  // Total count for donut center label
  readonly totalHotwork = computed(() =>
    this.progressSegments().reduce((sum, s) => sum + s.value, 0),
  );

  // Weekly Summary Chart Configuration
  readonly weeklyLabels = signal<string[]>([
    "29 Jul 26",
    "30 Jul 26",
    "31 Jul 26",
    "01 Aug 26",
    "02 Aug 26",
    "03 Aug 26",
    "04 Aug 26",
    "05 Aug 26",
    "06 Aug 26",
    "07 Aug 26",
  ]);

  readonly weeklySeries = signal<LineSeries[]>([
    {
      label: "Initiated",
      color: "#f59e0b",
      values: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Ready",
      color: "#ef4444",
      values: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Completed",
      color: "#3b82f6",
      values: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
  ]);

  // Installation Trend Data
  readonly installationLabels = signal<string[]>([
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
  ]);
  readonly installationSeries = signal<LineSeries[]>([
    {
      label: "Trend",
      color: "#3b82f6", // bright blue
      values: [30, 50, 42, 60, 55, 70],
    },
  ]);

  // Present Hotwork Progress Segments
  readonly progressSegments = signal<DonutSegment[]>([
    { label: "Initiated", value: 0, color: "#f59e0b" },
    { label: "Ready", value: 0, color: "#f97316" },
    { label: "Paused", value: 0, color: "#ef4444" },
    { label: "Completed", value: 0, color: "#3b82f6" },
  ]);

  // History Bar Chart Data
  readonly historyDateRange = signal<string | null>("");
  readonly historyBarData = signal<BarDatum[]>([
    { label: "Ready", value: 0, color: "#38bdf8", primary: true },
    { label: "In progress", value: 0, color: "#3b82f6", primary: true },
    { label: "Completed", value: 0, color: "#a855f7", primary: true },
  ]);

  navigateToManageHotwork(): void {
    this.router.navigate(["../manage-hotwork"], { relativeTo: this.route });
  }
}
