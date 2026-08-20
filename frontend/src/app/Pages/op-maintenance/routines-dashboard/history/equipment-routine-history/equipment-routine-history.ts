import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ColDef, ICellRendererParams } from 'ag-grid-community';
import { Subject, debounceTime } from 'rxjs';

import { SelectInput } from '../../../../../shared/components/select-input/select-input';
import { DataGrid } from '../../../../../shared/components/data-grid/data-grid';
import { Call } from '../../../../../services/network/call';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';

const STATUS_BADGE_CLASS: Record<string, string> = {
  ACTIVE: 'badge badge-active',
  INACTIVE: 'badge badge-inactive',
  OVERDUE: 'badge badge-pending',
};

export interface EquipmentRoutineRow {
  pk: number;
  subDept: string;
  equipmentNomenclature: string;
  routineName: string;
  status: string;
  previousRoutineCompletionDate: string;
  totalSubRoutines: number;
}

interface RoutineHistoryApiItem {
  pk: number;
  sub_dept: string;
  equipment_nomenclature: string;
  routine_name: string;
  status?: string;
  prev_completion_date?: string;
  total_sub_subroutines?: number;
}

export interface RoutineHistoryApiResponse {
  result?: RoutineHistoryApiItem[];
  departments?: string[];
  equipments?: string[];
  routine_types?: string[];
}

export interface RoutineHistoryFilters {
  subDept?: string;
  equipment?: string;
  routineName?: string;
  search?: string;
}

export interface RoutineHistoryTimelineItem {
  dart_no: string;
  routine_no: string;
  routine_description: string;
  next_due_date: string;
  prev_completion_date: string;
  rhsi: number | string;
  rhsi_updated_upto: string;
  routine_completed_at_rh: number | string;
  routine_due_at_rh: number | string;
  id: number;
  routine_pk: number;
}

export interface RoutineHistoryTimelineResponse {
  data?: RoutineHistoryTimelineItem[];
  routine_nos?: string[];
}

@Component({
  selector: 'app-equipment-routine-history',
  standalone: true,
  imports: [CommonModule, FormsModule, SelectInput, DataGrid, IconComponent],
  templateUrl: './equipment-routine-history.html',
  styleUrl: './equipment-routine-history.scss',
})
export class EquipmentRoutineHistoryComponent implements OnInit {
  private call = inject(Call);

  private readonly filtersChanged = new Subject<void>();

  /* ------------------------------------------------------------------ */
  /*  Lifecycle                                                            */
  /* ------------------------------------------------------------------ */
  ngOnInit(): void {
    this.loadRoutineHistory();

    // Backend does the filtering — debounce so typing/dropdown changes don't
    // fire a request per keystroke/click.
    this.filtersChanged
      .pipe(debounceTime(300))
      .subscribe(() => this.loadRoutineHistory());
  }
  /* ------------------------------------------------------------------ */
  /*  Filter state                                                         */
  /* ------------------------------------------------------------------ */
  selectedSubDept     = 'All';
  selectedEquipment   = 'All';
  selectedRoutineName = 'All';
  searchText          = '';

  subDeptOptions: { label: string; value: string }[] = [
    { label: 'All', value: 'All' }
  ];

  equipmentOptions: { label: string; value: string }[] = [
    { label: 'All', value: 'All' }
  ];

  routineNameOptions: { label: string; value: string }[] = [
    { label: 'All', value: 'All' }
  ];
  /* ------------------------------------------------------------------ */
  /*  Column definitions                                                   */
  /* ------------------------------------------------------------------ */
  columnDefs: ColDef[] = [
    {
      headerName: 'Sub Dept',
      field: 'subDept',
      flex: 1.5,
      minWidth: 180
    },
    {
      headerName: 'Equipment Nomenclature',
      field: 'equipmentNomenclature',
      flex: 2,
      minWidth: 250
    },
    {
      headerName: 'Routine Name',
      field: 'routineName',
      flex: 2.5,
      minWidth: 320
    },
    {
  headerName: 'Status',
    field: 'status',
    flex: 1,
    minWidth: 120,
    cellRenderer: (params: ICellRendererParams) => {
      const status = params.value ?? '';
      const cls = STATUS_BADGE_CLASS[status] ?? 'badge badge-pending';
      return `<span class="${cls}">${status}</span>`;
    }
    },
    {
      headerName: 'Previous Routine Completion Date',
      field: 'previousRoutineCompletionDate',
      flex: 1.5,
      minWidth: 220
    },
    {
      headerName: 'Total Sub-Routines',
      field: 'totalSubRoutines',
      flex: 1,
      minWidth: 180
    }
  ];

  /* ------------------------------------------------------------------ */
  /*  Row data                                                             */
  /* ------------------------------------------------------------------ */
  filteredRows = signal<EquipmentRoutineRow[]>([]);

  loadRoutineHistory(): void {

    this.call
      .getRoutineHistory({
        subDept: this.selectedSubDept,
        equipment: this.selectedEquipment,
        routineName: this.selectedRoutineName,
        search: this.searchText.trim(),
      })
      .subscribe({
        next: (res: RoutineHistoryApiResponse) => {

          const rows = (res.result || []).map((item: RoutineHistoryApiItem) => ({
            pk: item.pk,
            subDept: item.sub_dept,
            equipmentNomenclature: item.equipment_nomenclature,
            routineName: item.routine_name,
            status: (item.status || '').toUpperCase(),
            previousRoutineCompletionDate:
              item.prev_completion_date ?? 'NA',
            totalSubRoutines:
              item.total_sub_subroutines ?? 0
          }));

          this.filteredRows.set(rows);

          this.subDeptOptions = [
            { label: 'All', value: 'All' },
            ...(res.departments || []).map((item: string) => ({
              label: item,
              value: item
            }))
          ];

          this.equipmentOptions = [
            { label: 'All', value: 'All' },
            ...(res.equipments || []).map((item: string) => ({
              label: item,
              value: item
            }))
          ];

          this.routineNameOptions = [
            { label: 'All', value: 'All' },
            ...(res.routine_types || []).map((item: string) => ({
              label: item,
              value: item
            }))
          ];
        },

        error: (err: HttpErrorResponse) => {
          console.error('Routine History API Error', err);
          this.filteredRows.set([]);
        }
      });
  }

  /* ------------------------------------------------------------------ */
  /*  Timeline detail panel                                                */
  /* ------------------------------------------------------------------ */
  timelinePanelOpen = signal(false);
  timelineLoading = signal(false);
  timelineTitle = signal('');
  timelineRows = signal<RoutineHistoryTimelineItem[]>([]);
  timelineRoutineNoOptions = signal<{ label: string; value: string }[]>([
    { label: 'All', value: 'All' }
  ]);
  timelineSelectedRoutineNo = 'All';
  private timelineEquipmentPk: number | null = null;

  onRowClicked(row: unknown): void {
    const typedRow = row as EquipmentRoutineRow | undefined;
    if (!typedRow?.pk) return;
    this.openTimeline(typedRow);
  }

  openTimeline(row: EquipmentRoutineRow): void {
    this.timelineTitle.set(row.equipmentNomenclature);
    this.timelineSelectedRoutineNo = 'All';
    this.timelineEquipmentPk = row.pk;
    this.timelinePanelOpen.set(true);
    this.loadTimelineData();
  }

  // `routine_no` is sent to the backend on every load so filtering happens
  // server-side once it's supported there; until then the endpoint just
  // ignores the param and returns the full set.
  loadTimelineData(): void {
    if (this.timelineEquipmentPk == null) return;

    this.timelineLoading.set(true);
    this.timelineRows.set([]);

    this.call.getRoutineHistoryTimelineData(this.timelineEquipmentPk, this.timelineSelectedRoutineNo).subscribe({
      next: (res: RoutineHistoryTimelineResponse) => {
        this.timelineRows.set(res.data || []);

        this.timelineRoutineNoOptions.set([
          { label: 'All', value: 'All' },
          ...(res.routine_nos || []).map((item: string) => ({
            label: item,
            value: item
          }))
        ]);

        this.timelineLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Routine History Timeline API Error', err);
        this.timelineRows.set([]);
        this.timelineLoading.set(false);
      }
    });
  }

  onTimelineRoutineNoChange(): void {
    this.loadTimelineData();
  }

  closeTimeline(): void {
    this.timelinePanelOpen.set(false);
  }

  /* ------------------------------------------------------------------ */
  /*  Event handlers                                                       */
  /* ------------------------------------------------------------------ */
  onFilterChange(): void {
    this.filtersChanged.next();
  }

  onSearchChange(): void {
    this.filtersChanged.next();
  }

  clearFilters(): void {
    this.selectedSubDept = 'All';
    this.selectedEquipment = 'All';
    this.selectedRoutineName = 'All';
    this.searchText = '';

    this.loadRoutineHistory();
  }
}
