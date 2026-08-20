import { ChangeDetectionStrategy, Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { PlannerStore } from '../../store/planner.store';
import { ViewMode, formatRangeFromDate } from '../../constants/data';

import { FilterPanelComponent } from '../../components/planner-filter-panel/planner-filter-panel.component';
import { ControlsComponent } from '../../components/planner-controls/planner-controls.component';
import { CalendarComponent } from '../../components/planner-calendar/planner-calendar.component';
import { DetailComponent } from '../../components/planner-detail-panel/planner-detail-panel.component';
import { ActivityDetailsModalComponent } from '../../components/planner-activity-details-modal/planner-activity-details-modal.component';
import { NewActivityModalComponent } from '../../components/planner-new-activity-modal/planner-new-activity-modal.component';
import { NotifFlyoutComponent } from '../../components/planner-notification-flyout/planner-notification-flyout.component';
import { MailFlyoutComponent } from '../../components/planner-mail-flyout/planner-mail-flyout.component';
import { OverdueDartsModalComponent } from '../../components/planner-overdue-darts-modal/planner-overdue-darts-modal.component';
import { Input } from '@angular/core';

@Component({
  selector: 'app-operational-coordination-planner',
  standalone: true,
  imports: [
    FilterPanelComponent,
    ControlsComponent,
    CalendarComponent,
    DetailComponent,
    ActivityDetailsModalComponent,
    NewActivityModalComponent,
    NotifFlyoutComponent,
    MailFlyoutComponent,
    OverdueDartsModalComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './planner.component.html',
  styleUrls: ['./planner.component.scss'],
})
export class OperationalCoordinationPlannerComponent implements OnInit {
  protected readonly store = inject(PlannerStore);
  private readonly route = inject(ActivatedRoute);
  @Input() compact = false;
  protected readonly rangeLabel = computed(() =>
    formatRangeFromDate(this.store.rangeStart())
  );

  ngOnInit() {
    const initialView = this.route.snapshot.data['initialView'] as ViewMode | undefined;
    if (initialView) {
      this.store.view.set(initialView);
      if (initialView === 'Year') {
        this.store.ensureYearLoaded();
      }
    }
    void this.store.init();
  }
}
