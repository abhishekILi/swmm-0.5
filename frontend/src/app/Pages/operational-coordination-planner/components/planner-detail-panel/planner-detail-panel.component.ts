import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { IconComponent } from '../planner-icon/planner-icon.component';
import { addDays } from '../../constants/data';
import { PlannerStore } from '../../store/planner.store';

const CAT_LABEL: Record<string, string> = {
  defect: 'Defect', routine: 'Routine',
  planned_routine: 'Planned Routine', trial: 'Trials / Inspection',
  audit: 'Audit', others: 'Others',
};
const DEPT_LABEL: Record<string, string> = {
  eng: 'Engineering', elec: 'Electrical', wpn: 'Weapon',
  ops: 'Operations', fmu: 'FMU Support', tri: 'Trials & Insp.',
  adm: 'Administrative',
};

const DOW = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
const WEEKDAY_SHORT = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

/**
 * Right-hand detail panel. Shows full info for the currently selected
 * activity, or an empty-state prompt when nothing is selected.
 */
@Component({
  selector: 'app-detail',
  standalone: true,
  imports: [IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './planner-detail-panel.component.scss',
  templateUrl: './planner-detail-panel.component.html',

})
export class DetailComponent {
  protected readonly store = inject(PlannerStore);
  protected readonly a = this.store.selectedActivity;

  // Only manually-created activities (backend id prefix "activity_") support
  // edit/delete - routines/planned-routines/trials/defects/events are
  // read-only records aggregated from other modules.
  protected readonly isManual = computed(() => (this.a()?.id ?? '').startsWith('activity_'));

  protected readonly catLabel = computed(() => CAT_LABEL[this.a()?.cat ?? ''] ?? '');
  protected readonly deptLabel = computed(() => DEPT_LABEL[this.a()?.lane ?? ''] ?? '');
  protected readonly selectedDayActivities = computed(() => this.store.selectedDateActivities());
  protected readonly selectedActivityIndex = computed(() => {
    const selected = this.a();
    if (!selected) {
      return -1;
    }

    return this.selectedDayActivities().findIndex((activity) => activity.id === selected.id);
  });
  protected readonly hasMultipleDayActivities = computed(
    () => this.selectedDayActivities().length > 1,
  );
  protected readonly selectedDayLabel = computed(() => {
    const selectedDate = this.store.selectedDate();

    if (!selectedDate) {
      return '';
    }

    const [year, month, day] = selectedDate.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    const dayIndex = (date.getDay() + 6) % 7;
    return `${DOW[dayIndex]} ${String(day).padStart(2, '0')} ${date.toLocaleString('en-US', { month: 'short' })}`;
  });

  protected readonly dayLabel = computed(() => {
    const a = this.a();
    if (!a) return '';
    const d = addDays(this.store.rangeStart(), a.day);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${WEEKDAY_SHORT[d.getDay()]} ${pad(d.getDate())} ${d.toLocaleString('en-US', { month: 'short' })}`;
  });

  protected readonly tagCls = computed(() => {
    const a = this.a();
    if (!a) return '';
    if (a.conflict || a.delayed) return 'delayed';
    if (a.prog > 0) return 'progress';
    return 'scheduled';
  });

  protected readonly statusLabel = computed(() => {
    const a = this.a();
    if (!a) return '';
    if (a.conflict) return 'Conflict detected';
    if (a.delayed) return 'Delayed';
    if (a.prog > 0) return `In Progress · ${a.prog}%`;
    return 'Scheduled';
  });

  protected readonly priorityColor = computed(() => {
    const p = this.a()?.priority;
    if (p === 'Critical' || p === 'High') return '#f87171';
    if (p === 'Low') return '#34d399';
    return '#fbbf24';
  });

  protected readonly progressColor = computed(() => {
    const a = this.a();
    if (!a) return 'linear-gradient(90deg,#10b981,#34d399)';
    if (a.conflict) return 'linear-gradient(90deg,#ef4444,#fca5a5)';
    if (a.delayed) return 'linear-gradient(90deg,#fbbf24,#fcd34d)';
    return 'linear-gradient(90deg,#10b981,#34d399)';
  });

  protected editSelected() {
    this.store.openEditActivity();
  }

  protected showPreviousActivity() {
    this.moveActivity(-1);
  }

  protected showNextActivity() {
    this.moveActivity(1);
  }

  protected closePanel() {
    this.store.clearSelection();
  }

  private moveActivity(delta: number) {
    const list = this.selectedDayActivities();
    if (list.length <= 1) {
      return;
    }

    const current = this.a();
    const currentIndex = Math.max(
      0,
      list.findIndex((activity) => activity.id === current?.id),
    );
    const nextIndex = (currentIndex + delta + list.length) % list.length;
    const next = list[nextIndex];

    this.store.selectActivityWithDate(next.id, this.store.selectedDate());
  }

  protected async deleteSelected() {
    const a = this.a();
    if (!a) {
      return;
    }

    const ok = window.confirm(`Delete activity "${a.title}"?`);
    if (!ok) {
      return;
    }

    await this.store.deleteActivity(a.id);
  }
}
