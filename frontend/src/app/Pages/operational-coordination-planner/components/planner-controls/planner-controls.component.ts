import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  computed,
  inject,
  Input,
  signal,
} from '@angular/core';

import { IconComponent } from '../planner-icon/planner-icon.component';
import { ViewMode, formatRangeFromDate } from '../../constants/data';
import { PlannerStore } from '../../store/planner.store';
import { DatePopoverComponent } from '../planner-date-popover/planner-date-popover.component';

/**
 * Controls row above the calendar - view tabs, week navigation, date
 * popover, and "+ New Activity". Department/category filtering now lives in
 * the persistent left `app-filter-panel` sidebar instead of dropdowns here.
 *
 * The date popover closes on outside-click via a host-bound document listener.
 */
@Component({
  selector: 'app-controls',
  standalone: true,
  imports: [IconComponent, DatePopoverComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class.compact]': 'compact',
  },
  styleUrl: './planner-controls.component.scss',
  templateUrl: './planner-controls.component.html',
})
export class ControlsComponent {
  @Input() compact = false;

  protected readonly store = inject(PlannerStore);

  protected readonly dateOpen = signal(false);

  protected readonly rangeLabel = computed(() =>
    this.store.view() === 'Year'
      ? String(this.store.yearRef())
      : formatRangeFromDate(this.store.rangeStart())
  );

  protected readonly views: ViewMode[] = [
    'Year',
    'Month',
    'Week',
    'Day',
  ];

  protected selectView(v: ViewMode) {
    this.store.view.set(v);
    if (v === 'Year') {
      this.store.ensureYearLoaded();
    }
  }

  protected toggleDateOpen() {
    if (this.store.view() === 'Year') {
      return;
    }
    this.dateOpen.update(v => !v);
  }

  protected stepPrev() {
    if (this.store.view() === 'Year') {
      this.store.stepYear(-1);
    } else {
      this.store.stepWeek(-1);
    }
  }

  protected stepNext() {
    if (this.store.view() === 'Year') {
      this.store.stepYear(1);
    } else {
      this.store.stepWeek(1);
    }
  }

  protected goToday() {
    if (this.store.view() === 'Year') {
      this.store.yearRef.set(new Date().getFullYear());
      this.store.ensureYearLoaded();
    } else {
      this.store.goToday();
    }
  }

  protected openNew() {
    this.store.openCreateActivity();
  }

  @HostListener('document:mousedown', ['$event'])
  protected onDocClick(e: MouseEvent) {
    const target = e.target as HTMLElement;

    const inDatePopover =
      !!target.closest('app-date-popover');

    const isDateAnchor =
      !!target.closest('.range');

    if (!inDatePopover && !isDateAnchor) {
      this.dateOpen.set(false);
    }
  }
}
