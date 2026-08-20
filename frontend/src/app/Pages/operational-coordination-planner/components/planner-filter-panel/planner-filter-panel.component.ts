import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { IconComponent } from '../planner-icon/planner-icon.component';
import { Category } from '../../constants/data';
import { PlannerStore } from '../../store/planner.store';

const CATEGORY_ICON: Record<string, string> = {
  defect: 'wrench',
  routine: 'clock',
  planned_routine: 'doc',
  trial: 'plane2',
  audit: 'book',
  others: 'box',
};

/**
 * Persistent left-hand filter sidebar for the Ship Activity Calendar:
 * an "All Events" master checkbox, per-category checkboxes, and a legend
 * shortcut to the overdue-pending-DARTs modal.
 */
@Component({
  selector: 'app-filter-panel',
  standalone: true,
  imports: [IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './planner-filter-panel.component.scss',
  templateUrl: './planner-filter-panel.component.html',
})
export class FilterPanelComponent {
  protected readonly store = inject(PlannerStore);

  protected readonly categories = computed<{ id: Category; label: string; swatch: string; icon: string }[]>(() => {
    const rawCategories = this.store.choices()?.categories;
    const swatches: Record<string, string> = {
      defect: '#e65b5b',
      routine: '#fb923c',
      planned_routine: '#7c3aed',
      trial: '#2dd4bf',
      audit: '#5b811d',
      others: '#94a3b8',
    };

    const fallbackCategories = [
      { value: 'defect', label: 'Defect' },
      { value: 'routine', label: 'Routine' },
      { value: 'planned_routine', label: 'Planned Routine' },
      { value: 'trial', label: 'Trial' },
      { value: 'audit', label: 'Audit' },
      { value: 'others', label: 'Others' },
    ];

    const list: unknown[] = Array.isArray(rawCategories) && rawCategories.length > 0
      ? rawCategories
      : fallbackCategories;

    return list.map((item: unknown) => {
      let val = '';
      let lbl = '';
      if (Array.isArray(item)) {
        val = String(item[0] ?? '');
        lbl = String(item[1] ?? item[0] ?? val);
      } else if (item && typeof item === 'object') {
        const obj = item as Record<string, unknown>;
        val = String(obj['value'] ?? obj['id'] ?? obj['key'] ?? obj['code'] ?? '');
        lbl = String(obj['label'] ?? obj['name'] ?? obj['display_name'] ?? obj['title'] ?? val);
      } else {
        val = String(item ?? '');
        lbl = val;
      }

      return {
        id: val as Category,
        label: lbl,
        swatch: swatches[val] ?? '#94a3b8',
        icon: CATEGORY_ICON[val] ?? 'doc',
      };
    });
  });

  protected readonly allChecked = computed(
    () => this.categories().length > 0 && this.categories().every((c) => this.store.catFilter().includes(c.id)),
  );

  protected readonly totalCount = computed(() => this.store.catFilter().length);

  protected isChecked(id: Category): boolean {
    return this.store.catFilter().includes(id);
  }

  protected toggleAll(): void {
    if (this.allChecked()) {
      this.store.catFilter.set([]);
    } else {
      this.store.catFilter.set(this.categories().map((c) => c.id));
    }
  }

  protected toggle(id: Category): void {
    this.store.toggleCategory(id);
  }

  protected openOverdueDarts(): void {
    this.store.openOverdueDartsModal();
  }
}
