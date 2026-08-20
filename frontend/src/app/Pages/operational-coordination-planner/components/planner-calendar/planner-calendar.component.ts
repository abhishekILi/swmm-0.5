import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { IconComponent } from '../planner-icon/planner-icon.component';
import { ActivityCardComponent } from '../planner-activity-card/planner-activity-card.component';
import {
  Activity,
  Category,
  LANES,
  LANE_TIMES,
  addDays,
  startOfDay,
} from '../../constants/data';
import { PlannerStore } from '../../store/planner.store';

interface DayHead { dow: string; dom: string; month: string; today: boolean; }

const CAT_COLOR: Record<Category, string> = {
  defect: '#e65b5b', routine: '#fb923c', trial: '#2dd4bf',
  planned_routine: '#7c3aed', audit: '#5b811d', others: '#94a3b8',
};

const DOW_SHORT = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
const WEEKDAY_SHORT = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

/**
 * Calendar view router. Switches between Year, Month, Week, and Day
 * layouts based on `store.view()`.
 */
@Component({
  selector: 'app-calendar',
  standalone: true,
  imports: [IconComponent, ActivityCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './planner-calendar.component.scss',
  templateUrl: './planner-calendar.component.html',

})
export class CalendarComponent {
  protected readonly store = inject(PlannerStore);
  private readonly today = new Date();
  protected readonly lanes = LANES;
  protected readonly laneTimes = LANE_TIMES;
  protected readonly DOW_SHORT = DOW_SHORT;
  protected readonly WEEKDAY_SHORT = WEEKDAY_SHORT;

  protected readonly weekDays = computed<DayHead[]>(() => {
    const start = startOfDay(this.store.rangeStart());
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(start, i);
      return {
        dow: WEEKDAY_SHORT[d.getDay()],
        dom: String(d.getDate()).padStart(2, '0'),
        month: d.toLocaleString('en-US', { month: 'short' }),
        today: d.getFullYear() === this.today.getFullYear()
          && d.getMonth() === this.today.getMonth()
          && d.getDate() === this.today.getDate(),
      };
    });
  });

  protected readonly dayHead = computed<{ dow: string; dom: string; month: string; isToday: boolean }>(() => {
    const d = startOfDay(this.store.rangeStart());
    return {
      dow: WEEKDAY_SHORT[d.getDay()],
      dom: String(d.getDate()).padStart(2, '0'),
      month: d.toLocaleString('en-US', { month: 'short' }),
      isToday: d.getFullYear() === this.today.getFullYear()
        && d.getMonth() === this.today.getMonth()
        && d.getDate() === this.today.getDate(),
    };
  });

  /** Activities indexed by `${lane}:${day}` for O(1) per-cell lookup. */
  private readonly byCell = computed(() => {
    const map = new Map<string, Activity[]>();
    for (const a of this.store.filteredActivities()) {
      const k = `${a.lane}:${a.day}`;
      const arr = map.get(k);
      if (arr) arr.push(a); else map.set(k, [a]);
    }
    return map;
  });

  // --- Month view ---
  protected readonly monthCells = computed(() => {
    const start = startOfDay(this.store.rangeStart());
    const ref = new Date(start);
    const monthStart = new Date(ref.getFullYear(), ref.getMonth(), 1);
    const firstDow = (monthStart.getDay() + 6) % 7;
    const firstCell = new Date(monthStart);
    firstCell.setDate(monthStart.getDate() - firstDow);
    const today = this.today;
    const activities = this.store.filteredActivities();

    const byDate = new Map<string, Activity[]>();
    for (const a of activities) {
      if (a.date) {
        const arr = byDate.get(a.date);
        if (arr) arr.push(a); else byDate.set(a.date, [a]);
      }
    }

    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(firstCell); d.setDate(firstCell.getDate() + i);
      const isoDate = this.toIsoDate(d);
      const acts = byDate.get(isoDate) ?? [];
      return {
        d,
        inMonth: d.getMonth() === ref.getMonth(),
        isToday: d.getFullYear() === today.getFullYear()
          && d.getMonth() === today.getMonth()
          && d.getDate() === today.getDate(),
        acts,
      };
    });
  });

  // --- Year view ---
  protected readonly yearMonths = computed(() => {
    const year = this.store.yearRef();
    const today = this.today;

    const byDate = new Map<string, Activity[]>();
    for (const a of this.store.yearFilteredActivities()) {
      const arr = byDate.get(a.date);
      if (arr) arr.push(a); else byDate.set(a.date, [a]);
    }

    return Array.from({ length: 12 }, (_, monthIndex) => {
      const monthStart = new Date(year, monthIndex, 1);
      const firstCell = new Date(monthStart);
      firstCell.setDate(monthStart.getDate() - monthStart.getDay()); // Sun-first week

      const cells = Array.from({ length: 42 }, (_, i) => {
        const d = new Date(firstCell); d.setDate(firstCell.getDate() + i);
        return {
          d,
          inMonth: d.getMonth() === monthIndex,
          isToday: d.getFullYear() === today.getFullYear()
            && d.getMonth() === today.getMonth()
            && d.getDate() === today.getDate(),
          acts: byDate.get(this.toIsoDate(d)) ?? [],
        };
      });

      return {
        label: monthStart.toLocaleString('en-US', { month: 'long' }),
        cells,
      };
    });
  });

  onYearDayPick(day: Date) {
    this.store.setRangeStart(day);
    this.store.view.set('Month');
  }

  activitiesForCell(lane: string, day: number): Activity[] {
    return this.byCell().get(`${lane}:${day}`) ?? [];
  }

  hasConflict(activities: Activity[]): boolean {
    return activities.some((activity) => activity.conflict);
  }

  visibleActivities(activities: Activity[]): Activity[] {
    return this.hasConflict(activities) ? activities.slice(0, 3) : activities;
  }

  catColor(c: Category): string { return CAT_COLOR[c]; }

  onPick(e: Event, id: string) {
    e.stopPropagation();
    const activity = this.store.filteredActivities().find((item) => item.id === id);
    this.store.selectActivityWithDate(
      id,
      activity ? this.activityDateKey(activity) : null,
    );
  }

  openOverdueDarts(e: Event) {
    e.stopPropagation();
    this.store.openOverdueDartsModal();
  }

  onMonthDayPick(e: Event, day: Date) {
    e.stopPropagation();
    const key = this.toIsoDate(day);
    const activities = this.store.filteredActivities().filter(
      (activity) => this.store.getActivityDateKey(activity) === key,
    );
    this.store.selectDate(key, activities[0]?.id ?? null);
  }

  private activityDateKey(activity: Activity): string {
    const date = addDays(startOfDay(this.store.rangeStart()), activity.day);
    return this.toIsoDate(date);
  }

  private toIsoDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  protected dateKey(date: Date): string {
    return this.toIsoDate(date);
  }
}
