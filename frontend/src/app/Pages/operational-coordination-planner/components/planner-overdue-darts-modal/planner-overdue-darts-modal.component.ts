import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { ModalComponent } from '../../../../shared/components/modal/modal.component';

import { PlannerStore } from '../../store/planner.store';

/**
 * Lists open DARTs whose closing (rectification) date has already passed -
 * mirrors the legacy activity_planner app's "Overdue pending DARTs" legend
 * item + modal.
 */
@Component({
  selector: 'app-overdue-darts-modal',
  standalone: true,
  imports: [ModalComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './planner-overdue-darts-modal.component.html',
  styleUrl: './planner-overdue-darts-modal.component.scss',
})
export class OverdueDartsModalComponent {
  protected readonly store = inject(PlannerStore);

  protected close(): void {
    this.store.closeOverdueDartsModal();
  }
}
