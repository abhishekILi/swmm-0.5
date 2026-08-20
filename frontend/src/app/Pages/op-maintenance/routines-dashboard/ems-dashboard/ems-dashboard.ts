import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { MasterCard } from '../../../refit-maintenance/master-card/master-card';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { InputField } from '../../../../shared/components/input-field/input-field';
import { SelectInput, DropdownOption } from '../../../../shared/components/select-input/select-input';
import { ModalComponent } from '../../../../shared/components/modal/modal.component';
import { BarChart, BarDatum } from '../../../../shared/components/bar-chart/bar-chart';
import { KpiCard } from '../../../../shared/components/kpi-card/kpi-card';
import { Call } from '../../../../services/network/call';
import { NotificationService } from '../../../../Core/services/notification/notification.service';
import {
  EmsEquipmentLocation,
  EquipmentHistoryItem,
  MonthlyRunningHoursRow,
  SectionRhsiBarchartResponse,
} from './ems-dashboard.model';

interface DashboardTile {
  label: string;
  count: number;
  icon: string;
  iconColor: string;
  iconBg: string;
  route: string;
}

type EquipmentModalTab = 'status' | 'monthly' | 'cumulative';

interface SectionChart {
  id: number;
  name: string;
  bars: BarDatum[];
}

const TILE_META: { key: string; label: string; icon: string; iconColor: string; iconBg: string; route: string }[] = [
  { key: 'count', label: 'MAINTOPS', icon: 'clipboard-list', iconColor: '#4AA8FF', iconBg: 'rgba(74,168,255,0.16)', route: 'unique-maintop-routines' },
  { key: 'rh_due_count', label: "R/H Based Routines due in 1K Hours'", icon: 'clock', iconColor: '#F59E0B', iconBg: 'rgba(245,158,11,0.16)', route: 'r-h-based-routines' },
  { key: 'cal_due_count', label: 'Calendar Based Routines due in next 06 months', icon: 'calendar', iconColor: '#a855f7', iconBg: 'rgba(168,85,247,0.16)', route: 'calendar-based-routing' },
  { key: 'fuss_due_count', label: 'FUSS Trigger List', icon: 'flag', iconColor: '#ec4899', iconBg: 'rgba(236,72,153,0.16)', route: 'FUSS-triger-list' },
  { key: 'aber_due_count', label: 'Equipment due for ABER', icon: 'triangle-alert', iconColor: '#F82C36', iconBg: 'rgba(248,44,54,0.16)', route: 'equipment-due-for-ABER' },
];

const LOCATION_OPTIONS: DropdownOption[] = [
  { label: 'AT HARBOUR', value: 'AT HARBOUR' },
  { label: 'AT SEA', value: 'AT SEA' },
  { label: 'AT ANCHORAGE', value: 'AT ANCHORAGE' },
];

@Component({
  selector: 'app-ems-dashboard',
  standalone: true,
  imports: [CommonModule, SelectInput, ReactiveFormsModule, MasterCard, IconComponent, InputField,
     ModalComponent, BarChart, KpiCard],
  templateUrl: './ems-dashboard.html',
  styleUrl: './ems-dashboard.css',
})
export class EmsDashboard implements OnInit {
  private readonly router = inject(Router);
  private readonly call = inject(Call);
  private readonly toast = inject(NotificationService);
  private readonly fb = inject(FormBuilder);
  private readonly cdr = inject(ChangeDetectorRef);

  tiles: DashboardTile[] = TILE_META.map((t) => ({ label: t.label, icon: t.icon, iconColor: t.iconColor, iconBg: t.iconBg, route: t.route, count: 0 }));
  sections: SectionChart[] = [];
  loading = true;

  readonly locationOptions = LOCATION_OPTIONS;

  selectedSection: SectionChart | null = null;
  selectedBar: BarDatum | null = null;
  activeTab: EquipmentModalTab = 'status';

  get isEquipmentActive(): boolean {
    return this.selectedBar?.color === 'green';
  }

  // Tab 1 — Equipment ON / OFF
  statusForm: FormGroup;

  // Tab 2 — Monthly Book Closing Assistant
  monthlyRowForm: FormGroup;
  monthlyRows: MonthlyRunningHoursRow[] = [];
  monthlyTotalHours: string | null = null;
  recentHistory: EquipmentHistoryItem[] = [];
  loadingHistory = false;

  // Tab 3 — Cumulative Entry
  cumulativeForm: FormGroup;

  constructor() {
    this.statusForm = this.fb.group({
      started_at_location: ['AT ANCHORAGE', Validators.required],
      start_timedate: [''],
      stop_timedate: [''],
    });

    this.monthlyRowForm = this.fb.group({
      location: ['', Validators.required],
      start_timedate: ['', Validators.required],
      stop_timedate: ['', Validators.required],
    });

    this.cumulativeForm = this.fb.group({
      rhsi: ['', Validators.required],
      rhsi_updated_until: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loadDashboard();
  }

  private toSectionBars(chart: SectionRhsiBarchartResponse): BarDatum[] {
    return chart.labels.map((label, idx) => ({
      label,
      value: chart.values[idx],
      color: chart.colors[idx],
      id: chart.equipment_ids[idx],
    }));
  }

  private loadDashboard(): void {
    this.loading = true;

    this.call.getEmsThumbnail().subscribe({
      next: (res) => {
        const data = res.data;
        this.tiles = TILE_META.map((t) => ({
          label: t.label,
          icon: t.icon,
          iconColor: t.iconColor,
          iconBg: t.iconBg,
          route: t.route,
          count: (data as unknown as Record<string, number>)[t.key] ?? 0,
        }));
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Failed to load EMS thumbnail counts', err),
    });

    this.call.getEmsSections().subscribe({
      next: (res) => {
        const sectionIds = Object.entries(res.section_name || {}).map(([name, id]) => ({ name, id }));

        if (!sectionIds.length) {
          this.loading = false;
          this.cdr.detectChanges();
          return;
        }

        forkJoin(
          sectionIds.map((s) => this.call.getSectionRhsiBarchart(s.id)),
        ).subscribe({
          next: (results) => {
            this.sections = results.map((chart, i) => ({
              id: sectionIds[i].id,
              name: chart.section || sectionIds[i].name,
              bars: this.toSectionBars(chart),
            }));
            this.loading = false;
            this.cdr.detectChanges();
          },
          error: (err) => {
            console.error('Failed to load section RHSI charts', err);
            this.loading = false;
            this.cdr.detectChanges();
          },
        });
      },
      error: (err) => {
        console.error('Failed to load EMS sections', err);
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private refreshSection(sectionId: number): void {
    this.call.getSectionRhsiBarchart(sectionId).subscribe({
      next: (chart) => {
        const section = this.sections.find((s) => s.id === sectionId);
        if (!section) return;

        section.bars = this.toSectionBars(chart);
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Failed to refresh section chart', err),
    });
  }

  goTo(route: string): void {
    this.router.navigate(['/afterAuth/op-maintenance/routine', route]);
  }

  onBarClick(section: SectionChart, bar: BarDatum): void {
    this.selectedSection = section;
    this.selectedBar = bar;
    this.activeTab = 'status';

    const isActive = bar.color === 'green';

    this.statusForm.reset({
      started_at_location: 'AT ANCHORAGE',
      start_timedate: '',
      stop_timedate: '',
    });

    this.monthlyRowForm.reset({ location: '', start_timedate: '', stop_timedate: '' });
    this.monthlyRows = [];
    this.monthlyTotalHours = null;

    this.cumulativeForm.reset({ rhsi: '', rhsi_updated_until: '' });
    if (isActive) {
      this.cumulativeForm.get('rhsi')?.disable();
    } else {
      this.cumulativeForm.get('rhsi')?.enable();
    }

    this.loadHistory(bar.id);
  }

  private loadHistory(equipmentId: string | number | undefined): void {
    if (equipmentId === undefined) {
      this.recentHistory = [];
      return;
    }

    this.loadingHistory = true;
    this.call.getEmsEquipmentHistory(Number(equipmentId)).subscribe({
      next: (res) => {
        this.recentHistory = res.history ?? [];
        this.loadingHistory = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.recentHistory = [];
        this.loadingHistory = false;
        this.cdr.detectChanges();
      },
    });
  }

  setTab(tab: EquipmentModalTab): void {
    this.activeTab = tab;
  }

  closeEquipmentModal(): void {
    this.selectedSection = null;
    this.selectedBar = null;
    this.monthlyRows = [];
    this.monthlyTotalHours = null;
    this.recentHistory = [];
  }

  // ---- Tab 1: Equipment ON / OFF ----

  saveStatusChange(): void {
    if (this.statusForm.invalid || !this.selectedBar) {
      this.statusForm.markAllAsTouched();
      return;
    }

    const equipmentId = this.selectedBar.id;
    if (equipmentId === undefined) {
      return;
    }

    const isActive = this.isEquipmentActive;
    const newState = isActive ? 'INACTIVE' : 'ACTIVE';
    const value = this.statusForm.value;

    if (isActive && !value.stop_timedate) {
      this.toast.error('EQ Stop Time is required to switch this equipment OFF.');
      return;
    }
    if (!isActive && !value.start_timedate) {
      this.toast.error('EQ Start Time is required to switch this equipment ON.');
      return;
    }

    const sectionId = this.selectedSection?.id;

    this.call
      .updateEmsEquipmentState({
        equipment_id: Number(equipmentId),
        state: newState,
        started_at_location: value.started_at_location as EmsEquipmentLocation,
        start_timedate: isActive ? null : value.start_timedate,
        stop_timedate: isActive ? value.stop_timedate : null,
      })
      .subscribe({
        next: (res) => {
          this.toast.success(res?.message ?? 'Equipment status updated successfully.');
          this.closeEquipmentModal();
          if (sectionId !== undefined) {
            this.refreshSection(sectionId);
          }
        },
        error: (err: { error?: { message?: string } }) => {
          this.toast.error(err?.error?.message ?? 'Failed to update equipment status.');
        },
      });
  }

  // ---- Tab 2: Monthly Book Closing Assistant ----

  addMonthlyRow(): void {
    if (this.monthlyRowForm.invalid) {
      this.monthlyRowForm.markAllAsTouched();
      return;
    }

    const value = this.monthlyRowForm.value;
    this.monthlyRows = [
      ...this.monthlyRows,
      {
        start: value.start_timedate,
        stop: value.stop_timedate,
        location: value.location as EmsEquipmentLocation,
      },
    ];
    this.monthlyRowForm.reset({ location: '', start_timedate: '', stop_timedate: '' });
    this.monthlyTotalHours = null;
  }

  removeMonthlyRow(index: number): void {
    this.monthlyRows = this.monthlyRows.filter((_, i) => i !== index);
    this.monthlyTotalHours = null;
  }

  rowRunningHours(row: MonthlyRunningHoursRow): string {
    const start = new Date(row.start).getTime();
    const stop = new Date(row.stop).getTime();
    if (Number.isNaN(start) || Number.isNaN(stop) || stop <= start) {
      return '--:--';
    }
    const totalMinutes = Math.round((stop - start) / 60000);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${hours}:${String(minutes).padStart(2, '0')}`;
  }

  calculateRhsi(): void {
    let totalMinutes = 0;
    for (const row of this.monthlyRows) {
      const start = new Date(row.start).getTime();
      const stop = new Date(row.stop).getTime();
      if (!Number.isNaN(start) && !Number.isNaN(stop) && stop > start) {
        totalMinutes += Math.round((stop - start) / 60000);
      }
    }
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    this.monthlyTotalHours = `${hours}:${String(minutes).padStart(2, '0')}`;
  }

  saveMonthlyEntries(): void {
    if (!this.selectedBar || !this.monthlyRows.length) {
      this.toast.error('Add at least one row before saving.');
      return;
    }

    const equipmentId = this.selectedBar.id;
    if (equipmentId === undefined) {
      return;
    }

    const sectionId = this.selectedSection?.id;

    this.call
      .saveEmsMonthlyRunningHours({
        equipment_id: Number(equipmentId),
        rows: this.monthlyRows,
      })
      .subscribe({
        next: (res) => {
          this.toast.success(res?.message ?? 'Running hour log saved successfully.');
          this.closeEquipmentModal();
          if (sectionId !== undefined) {
            this.refreshSection(sectionId);
          }
        },
        error: (err: { error?: { message?: string } }) => {
          this.toast.error(err?.error?.message ?? 'Failed to save running hour log.');
        },
      });
  }

  // ---- Tab 3: Cumulative Entry ----

  saveCumulativeHours(): void {
    if (this.cumulativeForm.invalid || !this.selectedBar) {
      this.cumulativeForm.markAllAsTouched();
      return;
    }

    if (this.isEquipmentActive) {
      this.toast.error('Equipment must be OFF to enter cumulative hours.');
      return;
    }

    const equipmentId = this.selectedBar.id;
    if (equipmentId === undefined) {
      return;
    }

    const sectionId = this.selectedSection?.id;

    this.call
      .updateEmsTotalRunningHours({
        equipment: Number(equipmentId),
        rhsi: Number(this.cumulativeForm.value.rhsi),
        rhsi_updated_until: this.cumulativeForm.value.rhsi_updated_until,
      })
      .subscribe({
        next: (res) => {
          this.toast.success(res?.message ?? 'Cumulative running hours updated successfully.');
          this.closeEquipmentModal();
          if (sectionId !== undefined) {
            this.refreshSection(sectionId);
          }
        },
        error: (err: { error?: { message?: string } }) => {
          this.toast.error(err?.error?.message ?? 'Failed to update cumulative running hours.');
        },
      });
  }
}
