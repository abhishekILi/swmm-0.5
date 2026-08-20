import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { addDays } from '../../constants/data';
import { PlannerStore } from '../../store/planner.store';
import { IconComponent } from '../planner-icon/planner-icon.component';

const CAT_LABEL: Record<string, string> = {
  defect: 'Defect',
  routine: 'Routine',
  planned_routine: 'Planned Routine',
  trial: 'Trials / Inspection',
  audit: 'Audit',
  others: 'Others',
};

const NA = 'N/A';

/**
 * Compact "Details" popup shown when an activity is clicked - the quick-glance
 * equivalent of the mock (Equipment / Due Date / Routine / Section / Category /
 * Created By / Frequency / Last Completion / Maintop No). The Activity model
 * doesn't carry most of those fields yet (no backend support), so anything
 * missing renders as "N/A" rather than being invented.
 *
 * The expand button switches to the fuller read-only side panel
 * (`app-detail`) for activities that need the richer linked-info/coordination
 * view already built there.
 */
@Component({
  selector: 'app-activity-details-modal',
  standalone: true,
  imports: [IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './planner-activity-details-modal.component.scss',
  templateUrl: './planner-activity-details-modal.component.html',
})
export class ActivityDetailsModalComponent {
  protected readonly store = inject(PlannerStore);
  protected readonly a = this.store.selectedActivity;

  // Only manually-created activities (backend id prefix "activity_") support
  // reschedule/delete - routines/planned-routines/trials/defects/events are
  // read-only records aggregated from other modules (see planner-detail-panel).
  protected readonly isManual = computed(() => (this.a()?.id ?? '').startsWith('activity_'));

  protected readonly dueDate = computed(() => {
    const activity = this.a();
    if (!activity) return NA;
    const d = addDays(this.store.rangeStart(), activity.day);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  });

  protected readonly categoryLabel = computed(() => CAT_LABEL[this.a()?.cat ?? ''] ?? NA);
  protected readonly equipment = computed(() => this.a()?.equipment || NA);
  protected readonly section = computed(() => this.a()?.loc || NA);
  protected readonly routineName = computed(() => this.a()?.title || NA);
  protected readonly maintopNo = computed(() => this.a()?.ref || NA);

  protected close(): void {
    this.store.clearSelection();
  }

  protected expand(): void {
    this.store.openFullDetail();
  }

  protected reschedule(): void {
    this.store.openEditActivity();
  }

  protected async remove(): Promise<void> {
    const activity = this.a();
    if (!activity) {
      return;
    }

    const ok = window.confirm(`Delete activity "${activity.title}"?`);
    if (!ok) {
      return;
    }

    await this.store.deleteActivity(activity.id);
  }
}
