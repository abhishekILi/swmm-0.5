import { Component, ChangeDetectionStrategy, signal, inject, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { RouterModule } from "@angular/router";
import { PanelCard } from "../../../../shared/components/panel-card/panel-card";
import { KpiCard } from "../../../../shared/components/kpi-card/kpi-card";
import { BarChart, StackedBarSeries } from "../../../../shared/components/bar-chart/bar-chart";
import { DonutChart, DonutSegment } from "../../../../shared/components/donut-chart/donut-chart";
import { ModalComponent } from "../../../../shared/components/modal/modal.component";
import { IconComponent } from "../../../../shared/components/icon/icon.component";
import { SrarService, SrarRecord, SrarReportDetail, SrarAnalyticsMonthlyTrendItem, SrarAnalyticsMonthlyTrendResponse, SrarAnalyticsYearlyStatusItem, SrarAnalyticsYearlyStatusResponse, SrarLifecycleDistributionItem } from "../../../../Core/services/srar/srar.service";

@Component({
  selector: "app-srar-dashboard",
  standalone: true,
  imports: [CommonModule, RouterModule, PanelCard, KpiCard, BarChart, DonutChart, ModalComponent, IconComponent],
  templateUrl: "./srar-dashboard.component.html",
  styleUrls: ["./srar-dashboard.component.css"],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SrarDashboardComponent implements OnInit {
  private readonly srarService = inject(SrarService);

  dashboardCards = signal([
    { title: "SRAR DETAIL FROM PAST 6 MONTHS", count: 12, subtext: "Recent Submissions", icon: "chart-pie", color: "#38BDF8", bg: "rgba(56, 189, 248, 0.15)" },
    { title: "SRAR APPLICATION STATUS", count: 8, subtext: "Verified & Active", icon: "clipboard-list", color: "#34D399", bg: "rgba(52, 211, 153, 0.15)" },
    { title: "EDIT SRAR DETAIL", count: 2, subtext: "Pending Drafts", icon: "pencil", color: "#FBBF24", bg: "rgba(251, 191, 36, 0.15)" },
    { title: "HISTORY LOGS", count: 24, subtext: "Archived Returns", icon: "clock", color: "#C084FC", bg: "rgba(192, 132, 252, 0.15)" },
  ]);

  monthlyCategories = signal<string[]>(["Mar 2026", "Apr 2026", "May 2026", "Jun 2026", "Jul 2026", "Aug 2026"]);
  monthlyStackedSeries = signal<StackedBarSeries[]>([
    { name: "Draft", color: "#F59E0B", data: [0, 0, 0, 0, 0, 1] },
    { name: "Submitted", color: "#38BDF8", data: [0, 0, 0, 0, 0, 0] }
  ]);

  yearlyStatusSegments = signal<DonutSegment[]>([
    { label: "Draft", value: 1, color: "#3B82F6" },
    { label: "Pending CO Review", value: 0, color: "#F59E0B" },
    { label: "CO Approved", value: 0, color: "#10B981" },
    { label: "CMMS Synced", value: 0, color: "#38BDF8" },
  ]);
  yearlyTotalRecords = signal<number>(1);
  yearlyApprovedPercentage = signal<string>("0%");

  recentReports = signal<SrarRecord[]>([]);

  // Modal State Management
  isModalOpen = signal<boolean>(false);
  modalTitle = signal<string>("");
  modalType = signal<"reportDetail" | "kpiList">("reportDetail");
  selectedReport = signal<SrarReportDetail | null>(null);
  filteredReports = signal<SrarRecord[]>([]);
  isLoadingDetail = signal<boolean>(false);

  ngOnInit(): void {
    this.loadDashboardData();
  }

  loadDashboardData(): void {
    // Fetch KPI analytics from SrarService
    this.srarService.getAnalyticsKpis().subscribe({
      next: (kpis) => {
        if (kpis) {
          const formatCount = (val: unknown, fallback: number): number => {
            if (val === undefined || val === null) return fallback;
            const num = Number(val);
            return isNaN(num) ? fallback : num;
          };

          const past6Months = kpis["past_6_months_count"];
          const activeStatus = kpis["active_status_count"];
          const editableSrar = kpis["editable_srar_count"] ?? kpis["pending_drafts_count"];
          const historyLogs = kpis["history_logs_count"];

          this.dashboardCards.set([
            { title: "SRAR DETAIL FROM PAST 6 MONTHS", count: formatCount(past6Months, 1), subtext: "Recent Submissions", icon: "chart-pie", color: "#38BDF8", bg: "rgba(56, 189, 248, 0.15)" },
            { title: "SRAR APPLICATION STATUS", count: formatCount(activeStatus, 0), subtext: "Verified & Active", icon: "clipboard-list", color: "#34D399", bg: "rgba(52, 211, 153, 0.15)" },
            { title: "EDIT SRAR DETAIL", count: formatCount(editableSrar, 1), subtext: "Pending Drafts", icon: "pencil", color: "#FBBF24", bg: "rgba(251, 191, 36, 0.15)" },
            { title: "HISTORY LOGS", count: formatCount(historyLogs, 1), subtext: "Archived Returns", icon: "clock", color: "#C084FC", bg: "rgba(192, 132, 252, 0.15)" },
          ]);

          if (kpis.application_status) {
            const appStatus = kpis.application_status;
            const draft = Number(appStatus.draft ?? 0);
            const pendingCo = Number(appStatus.pending_co_review ?? 0);
            const coApproved = Number(appStatus.co_approved ?? 0);
            const synced = Number(appStatus.synced ?? 0);
            const total = Number(appStatus.total ?? (draft + pendingCo + coApproved + synced));

            this.yearlyStatusSegments.set([
              { label: "Draft", value: draft, color: "#3B82F6" },
              { label: "Pending CO Review", value: pendingCo, color: "#F59E0B" },
              { label: "CO Approved", value: coApproved, color: "#10B981" },
              { label: "CMMS Synced", value: synced, color: "#38BDF8" },
            ]);

            this.yearlyTotalRecords.set(total);
            const approved = coApproved + synced;
            const pct = total > 0 ? Math.round((approved / total) * 100) : 0;
            this.yearlyApprovedPercentage.set(`${pct}%`);
          }
        }
      }
    });

    // Fetch Monthly Trend analytics
    this.srarService.getAnalyticsMonthlyTrend().subscribe({
      next: (res) => {
        let trendList: SrarAnalyticsMonthlyTrendItem[] = [];
        if (res && typeof res === "object" && "trend" in res && Array.isArray((res as SrarAnalyticsMonthlyTrendResponse).trend)) {
          trendList = (res as SrarAnalyticsMonthlyTrendResponse).trend;
        } else if (Array.isArray(res)) {
          trendList = res as SrarAnalyticsMonthlyTrendItem[];
        }

        if (trendList && trendList.length > 0) {
          const categories = trendList.map((item) => item.month || item.label || "");
          const draftData = trendList.map((item) => Number(item.draft ?? (item.value || 0)));
          const submittedData = trendList.map((item) => Number(item.submitted || 0));

          this.monthlyCategories.set(categories);
          this.monthlyStackedSeries.set([
            { name: "Draft", color: "#F59E0B", data: draftData },
            { name: "Submitted", color: "#38BDF8", data: submittedData }
          ]);
        }
      }
    });

    // Fetch Yearly Status distribution analytics
    this.srarService.getAnalyticsYearlyStatus().subscribe({
      next: (res) => {
        let distribution: SrarLifecycleDistributionItem[] = [];
        let totalRecords = 0;

        if (res && typeof res === "object" && "lifecycle_distribution" in res && Array.isArray((res as SrarAnalyticsYearlyStatusResponse).lifecycle_distribution)) {
          const resp = res as SrarAnalyticsYearlyStatusResponse;
          distribution = resp.lifecycle_distribution;
          totalRecords = resp.total_year_records ?? 0;
        } else if (Array.isArray(res)) {
          distribution = (res as SrarAnalyticsYearlyStatusItem[]).map((item) => ({
            status: item.status || item.label || "",
            count: Number(item.count ?? item.value ?? 0),
            percentage: Number(item.percentage ?? 0)
          }));
          totalRecords = distribution.reduce((sum, item) => sum + item.count, 0);
        }

        if (distribution && distribution.length > 0) {
          const statusColors: Record<string, string> = {
            "Draft": "#3B82F6",
            "Pending CO Review": "#F59E0B",
            "CO Approved": "#10B981",
            "CMMS Synced": "#38BDF8"
          };

          const segments: DonutSegment[] = distribution.map((item) => ({
            label: item.status,
            value: Number(item.count || 0),
            color: statusColors[item.status] || "#38BDF8"
          }));

          const approvedCount = distribution
            .filter((item) => item.status === "CO Approved" || item.status === "CMMS Synced")
            .reduce((sum, item) => sum + Number(item.count || 0), 0);

          const calcTotal = totalRecords || distribution.reduce((sum, item) => sum + Number(item.count || 0), 0);
          const pct = calcTotal > 0 ? Math.round((approvedCount / calcTotal) * 100) : 0;

          this.yearlyStatusSegments.set(segments);
          this.yearlyTotalRecords.set(calcTotal);
          this.yearlyApprovedPercentage.set(`${pct}%`);
        }
      }
    });

    // Fetch Recent SRAR Reports list
    // this.srarService.getDashboard().subscribe({
    //   next: (data: SrarRecord[]) => {
    //     if (data && Array.isArray(data)) {
    //       this.recentReports.set(data);
    //     }
    //   }
    // });
  }

  openKpiModal(cardTitle: string): void {
    this.modalTitle.set(cardTitle);
    this.modalType.set("kpiList");

    const all = this.recentReports();
    if (cardTitle.includes("EDIT")) {
      this.filteredReports.set(all.filter((r) => r.approvalStatus === "Draft" || r.approvalStatus === "In Review"));
    } else if (cardTitle.includes("STATUS")) {
      this.filteredReports.set(all.filter((r) => r.approvalStatus === "Approved" || r.approvalStatus === "In Review"));
    } else {
      this.filteredReports.set(all);
    }

    this.isModalOpen.set(true);
  }

  viewReportDetails(headerId?: string | number): void {
    const numericId = Number(headerId) || 101;
    this.modalTitle.set(`SRAR Report Details - ID #${numericId}`);
    this.modalType.set("reportDetail");
    this.isModalOpen.set(true);
    this.isLoadingDetail.set(true);
    this.selectedReport.set(null);

    this.srarService.getReportDetails(numericId).subscribe({
      next: (details) => {
        this.selectedReport.set(details as SrarReportDetail);
        this.isLoadingDetail.set(false);
      },
      error: () => {
        this.isLoadingDetail.set(false);
      }
    });
  }

  closeModal(): void {
    this.isModalOpen.set(false);
    this.selectedReport.set(null);
  }

  getStatusClass(status?: string): string {
    const val = status || "Draft";
    if (val.includes("Approved") || val === "Approved") {
      return "badge-success";
    }
    if (val.includes("Review") || val === "In Review") {
      return "badge-warning";
    }
    if (val === "Draft") {
      return "badge-secondary";
    }
    return "badge-info";
  }
}
