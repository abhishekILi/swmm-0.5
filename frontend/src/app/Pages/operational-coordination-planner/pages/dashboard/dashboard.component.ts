import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { LineChart, LineSeries } from '../../../../shared/components/line-chart/line-chart';
import { IconComponent, IconVariant } from '../../../../shared/components/icon/icon.component';
import { KpiCard } from '../../../../shared/components/kpi-card/kpi-card';

import { PlannerApiService } from '../../services/planner-api.service';
import { PlannerDashboardDto, PlannerNotificationDto } from '../../models/planner-api.models';
import { EQUIPMENT_SECTIONS, EquipmentSection } from '../../constants/data';

// "Total" KPIs on this dashboard are all-time counts (matching the legacy
// Home_new dashboard, which never date-scopes them) - not tied to whatever
// week the Ship Activity Calendar happens to have loaded.
const ALL_TIME_QUERY = { start_date: '2000-01-01', end_date: '2099-12-31' };

const NOTIFICATION_ICON: Record<PlannerNotificationDto['kind'], string> = {
  info: 'wrench',
  alert: 'file-text',
  warn: 'triangle-alert',
};

const NOTIFICATION_VARIANT: Record<PlannerNotificationDto['kind'], IconVariant> = {
  info: 'accent',
  alert: 'danger',
  warn: 'warning',
};

type AlertTabKey = 'all' | PlannerNotificationDto['kind'];

const ALERT_TABS: { key: AlertTabKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'info', label: 'DARTs' },
  { key: 'alert', label: 'Certificates' },
  { key: 'warn', label: 'Routines' },
];

@Component({
  selector: 'app-oc-planner-dashboard',
  standalone: true,
  imports: [LineChart, IconComponent, KpiCard],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class OcPlannerDashboardComponent implements OnInit {
  private readonly plannerApi = inject(PlannerApiService);
  private readonly router = inject(Router);

  protected readonly equipmentSections = EQUIPMENT_SECTIONS;
  protected readonly alertTabs = ALERT_TABS;

  protected readonly dartTrendLabels = signal<string[]>([]);
  protected readonly dartTrendSeries = signal<LineSeries[]>([]);
  protected readonly dashboardData = signal<PlannerDashboardDto | null>(null);
  protected readonly activeAlertTab = signal<AlertTabKey>('all');

  ngOnInit(): void {
    this.plannerApi.getDashboard(ALL_TIME_QUERY).subscribe({
      next: (data) => this.dashboardData.set(data),
      error: (error) => console.error('Failed to load planner dashboard', error),
    });

    this.plannerApi.getDartTrend().subscribe((trend) => {
      this.dartTrendLabels.set(trend.labels);
      this.dartTrendSeries.set(
        trend.series.map((s) => ({ label: s.label, color: s.color, values: s.values })),
      );
    });
  }

  protected readonly summary = computed(() => this.dashboardData()?.summary ?? null);

  protected readonly categoryCount = computed(() => {
    const counts = new Map<string, number>(
      (this.summary()?.category_cards ?? []).map((c) => [c.key, c.count]),
    );
    return (key: string) => counts.get(key) ?? 0;
  });

  protected readonly notifications = computed(() => this.dashboardData()?.notifications ?? []);

  protected readonly filteredNotifications = computed(() => {
    const tab = this.activeAlertTab();
    const all = this.notifications();
    return tab === 'all' ? all : all.filter((n) => n.kind === tab);
  });

  protected setAlertTab(tab: AlertTabKey): void {
    this.activeAlertTab.set(tab);
  }

  protected notificationIcon(kind: PlannerNotificationDto['kind']): string {
    return NOTIFICATION_ICON[kind] ?? 'circle-alert';
  }

  protected notificationVariant(kind: PlannerNotificationDto['kind']): IconVariant {
    return NOTIFICATION_VARIANT[kind] ?? 'accent';
  }

  protected equipmentTotal(section: EquipmentSection): number {
    return section.operational + section.nonOperational;
  }

  /**
   * Two-tone semicircle arc (operational then non-operational) drawn over a
   * 120x66 viewBox, centred at (60,60) with radius 50 - sweeping from the
   * left point (180deg) over the top to the right point (0deg).
   */
  protected equipmentArcPath(section: EquipmentSection): { operational: string; nonOperational: string } {
    const total = this.equipmentTotal(section);
    const ratio = total ? section.operational / total : 0;
    const cx = 60;
    const cy = 60;
    const r = 50;
    const point = (angleDeg: number) => {
      const rad = (angleDeg * Math.PI) / 180;
      return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
    };
    const start = point(180);
    const mid = point(180 - ratio * 180);
    const end = point(0);
    const arc = (from: { x: number; y: number }, to: { x: number; y: number }) =>
      `M ${from.x} ${from.y} A ${r} ${r} 0 0 1 ${to.x} ${to.y}`;
    return {
      operational: arc(start, mid),
      nonOperational: arc(mid, end),
    };
  }

  protected goToCalendar(): void {
    void this.router.navigateByUrl('/afterAuth/activity/calendar');
  }

  protected goToSearchRoutines(): void {
    void this.router.navigateByUrl('/afterAuth/op-maintenance/routine/search-routines');
  }

  protected goToSearchSpare(): void {
    void this.router.navigateByUrl('/afterAuth/inventory/ship-inventory-obs/search');
  }

  protected goToOpenDarts(): void {
    void this.router.navigateByUrl('/afterAuth/op-maintenance/open-darts');
  }

  protected goToPlannedRoutines(): void {
    void this.router.navigateByUrl('/afterAuth/op-maintenance/routine/planned-routines');
  }

  protected goToIssuedSpares(): void {
    void this.router.navigateByUrl('/afterAuth/inventory/ship-inventory-obs/history');
  }

  protected goToDueForReceipt(): void {
    void this.router.navigateByUrl('/afterAuth/inventory/ship-inventory-obs/Internal-transactions/due-for-receive');
  }

  protected goToPtsSurveyPending(): void {
    void this.router.navigateByUrl('/afterAuth/inventory/ship-inventory-obs/Internal-transactions/PTS-Survey-Pending');
  }

  protected goToEquipmentStatus(section: EquipmentSection): void {
    void this.router.navigate(['/afterAuth/activity/dashboard/equipment-status'], {
      queryParams: { section: section.label },
    });
  }
}
