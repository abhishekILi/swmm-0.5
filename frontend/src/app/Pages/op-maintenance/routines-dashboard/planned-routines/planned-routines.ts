import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ColDef, CellCallbackParams, RowData } from 'ag-grid-community';
import { debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { MasterCard } from '../../../refit-maintenance/master-card/master-card';
import { SelectInput } from '../../../../shared/components/select-input/select-input';
import { DataGrid } from '../../../../shared/components/data-grid/data-grid';

import { Call } from '../../../../services/network/call';
import { IconComponent } from '../../../../shared/components/icon/icon.component';

interface PlannedRoutineItem {
  pk: number;
  routine_name: string;
  section: string;
  equipment_name: string;
  maintop_no: string;
  last_routine_date: string;
  date: string;
  last_routine_running_hrs: number;
  next_due_running_hrs: number | string;
  total_running_hrs: number;
  running_hrs_updated_tilldate: number | string;
  running_hrs_available: number | string;
  valid_upto: string;
  total_routines: number;
  dyd_routines: number;
  remarks: string;
}

interface FilterOptionItem {
  id: number | string;
  name: string;
}

interface PlannedRoutinesFilterOptions {
  sub_departments?: FilterOptionItem[];
  equipments?: FilterOptionItem[];
  routine_types?: FilterOptionItem[];
}

interface SelectOption {
  label: string;
  value: number | string;
}

@Component({
  selector: 'app-planned-routines',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MasterCard, SelectInput, DataGrid, IconComponent],
  templateUrl: './planned-routines.html',
  styleUrl: './planned-routines.css',
})
export class PlannedRoutines implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(Call);
  private readonly router = inject(Router);

  searchForm!: FormGroup;

  readonly filteredRoutines = signal<PlannedRoutineItem[]>([]);
  readonly subDepartmentOptions = signal<SelectOption[]>([]);
  readonly equipmentOptions = signal<SelectOption[]>([]);
  readonly routineTypeOptions = signal<SelectOption[]>([]);

  columnDefs: ColDef[] = [];

  ngOnInit(): void {
    this.initializeForm();
    this.initializeColumns();
    this.getPlannedRoutines();
  }

  initializeForm(): void {
    this.searchForm = this.fb.group({
      subDept: [''],
      equipment: [''],
      routineType: [''],
      search: [''],
    });

    // Every field here — including free-text search — is sent straight to the
    // backend; there is no client-side filtering of the loaded rows.
    this.searchForm.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)))
      .subscribe(() => {
        this.getPlannedRoutines();
      });
  }

  initializeColumns(): void {
    this.columnDefs = [
      {
        headerName: 'Sub Dept',
        field: 'section',
        flex: 1,
      },
      {
        headerName: 'Equipment Nomenclature',
        field: 'equipment_name',
        flex: 2,
      },
      {
        headerName: 'Routine Name',
        field: 'routine_name',
        flex: 2,
      },
      {
        headerName: 'Previous Routine',
        field: 'last_routine_date',
        flex: 1,
        valueGetter: (params: CellCallbackParams) =>
          (params.data as PlannedRoutineItem)?.last_routine_date || 'NA',
      },
      {
        headerName: 'Next Due (R/H)',
        field: 'next_due_running_hrs',
        flex: 1,
        valueGetter: (params: CellCallbackParams) =>
          (params.data as PlannedRoutineItem)?.next_due_running_hrs ?? 'NA',
      },
      {
        headerName: 'Total Running Hrs',
        field: 'total_running_hrs',
        flex: 1,
      },
    ];
  }

  async getPlannedRoutines(): Promise<void> {
    const { subDept, equipment, routineType, search } = this.searchForm.value;

    try {
      const raw = await firstValueFrom(
        this.api.getPlanedRoutines({
          sectionId: subDept || undefined,
          equipmentNameId: equipment || undefined,
          routineCategory: routineType || undefined,
          search: (search || '').trim() || undefined,
        })
      );

      // Backend returns a bare array of routine rows — no result/filter_options wrapper.
      const rows = (Array.isArray(raw) ? raw : []) as PlannedRoutineItem[];
      const filterOptions: PlannedRoutinesFilterOptions | undefined = Array.isArray(raw)
        ? undefined
        : (raw as { filter_options?: PlannedRoutinesFilterOptions })?.filter_options;

      this.filteredRoutines.set(rows);

      this.subDepartmentOptions.set([
        { label: 'All', value: '' },
        ...(filterOptions?.sub_departments?.map((item: FilterOptionItem) => ({
          label: item.name,
          value: item.id,
        })) ?? []),
      ]);

      this.equipmentOptions.set([
        { label: 'All', value: '' },
        ...(filterOptions?.equipments?.map((item: FilterOptionItem) => ({
          label: item.name,
          value: item.id,
        })) ?? []),
      ]);

      this.routineTypeOptions.set([
        { label: 'All', value: '' },
        ...(filterOptions?.routine_types?.map((item: FilterOptionItem) => ({
          label: item.name,
          value: item.id,
        })) ?? []),
      ]);
    } catch (err: unknown) {
      console.error('Unable to fetch planned routines.', err);
      this.filteredRoutines.set([]);
    }
  }

  clearFilters(): void {
    this.searchForm.reset({
      subDept: '',
      equipment: '',
      routineType: '',
      search: '',
    });
  }

  onRowClicked(row: RowData): void {
    const pk = (row as unknown as PlannedRoutineItem)?.pk;
    if (!pk) return;

    this.router.navigate(
      ['/afterAuth/op-maintenance/routine/planned-routine-detail'],
      { state: { addRoutineId: pk } },
    );
  }
}
