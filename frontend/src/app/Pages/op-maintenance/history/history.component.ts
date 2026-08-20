import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule
} from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { firstValueFrom } from 'rxjs';

import { SelectInput } from '../../../shared/components/select-input/select-input';
import { DataGrid } from '../../../shared/components/data-grid/data-grid';
import { IconComponent } from '../../../shared/components/icon/icon.component';

import { CellCallbackParams, ColDef } from 'ag-grid-community';
import { Call } from '../../../services/network/call';
import { Router } from '@angular/router';
import { NotificationService } from '../../../Core/services/notification/notification.service';

export interface DartHistoryRow {
  id: number | string;
  dartNo: string;
  cmmsSyncStatus: boolean;
  opraNo: string;
  raRaised: boolean;
  dlNo: string;
  dlRaised: boolean;
  equipmentName: string;
  equipmentNomenclature: string;
  defectDescription: string;
  subDepartment: string;
  department: string;
  symptomCode: string;
  severityCode: string;
  closureDate: string;
  repairAgency: string;
  diagnosisCode: string;
  daysDelayed: number | string;
  delayReason: string;
  lessonLearnt: string;
  dartOccasion: string;
  defectDate: string;
  shipRemarks: string;
  maintenanceType: string;
  refitType: string;
}

interface FilterOption {
  label: string;
  value: string;
}

interface DartHistoryFilters {
  dartOccasions?: string[];
  dartTypes?: string[];
  subDepartments?: string[];
  departments?: string[];
  dartMaintenancePeriod?: string[];
  equipments?: string[];
  equipment_nomenclatures?: string[];
}

export interface DartHistoryResponse {
  data?: DartHistoryRow[];
  filters?: DartHistoryFilters;
}

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    SelectInput,
    DataGrid,
    IconComponent
  ],
  templateUrl: './history.component.html',
  styleUrl: './history.component.scss'
})
export class HistoryComponent implements OnInit {
  private fb = inject(FormBuilder);
  private call = inject(Call);
  private router = inject(Router);
  private toastr = inject(NotificationService);

  pageSize = 10;
  tableSearch = '';

  form: FormGroup;

  errorMessage = '';


  rowData = signal<DartHistoryRow[]>([]);
  maintenancePeriodOptions = signal<FilterOption[]>([]);
  dartOccasionOptions = signal<FilterOption[]>([]);
  subDepartmentOptions = signal<FilterOption[]>([]);
  dartTypeOptions = signal<FilterOption[]>([]);
  equipmentOptions = signal<FilterOption[]>([]);
  nomenclatureOptions = signal<FilterOption[]>([]);
  departmentOptions = signal<FilterOption[]>([]);


  constructor() {

    this.form = this.fb.group({
      maintenancePeriod: [''],
      dartOccasion: [''],
      subDepartment: [''],
      dartType: [''],

      dateFrom: [''],
      dateTo: [''],

      equipment: [''],
      nomenclature: [''],

      department: ['']
    });
  }

  ngOnInit(): void {





    void this.loadHistoryData();

    // Auto-filter as soon as any filter control changes — text/date fields are
    // debounced so typing doesn't fire a request per keystroke; dropdowns settle
    // on the same debounce since they change value once per click anyway.
    this.form.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
      )
      .subscribe(() => void this.search());
  }

  readonly columnDefs: ColDef[] = [
    {
      field: 'dartNo',
      headerName: 'DART No.',
      flex: 1,
      minWidth: 140
    },
    {
      field: 'cmmsSyncStatus',
      headerName: 'DART Closing - CMMS Sync Status',
      flex: 1.5,
      minWidth: 250,
      valueGetter: (params: CellCallbackParams) =>
        (params.data as DartHistoryRow | undefined)?.cmmsSyncStatus
          ? 'Synced'
          : 'Not Synced'
    },
    {
      field: 'opraNo',
      headerName: 'OPRA No.',
      flex: 1,
      minWidth: 140
    },
    {
      field: 'raRaised',
      headerName: 'RA Raised Status',
      flex: 1,
      minWidth: 160,
      valueGetter: (params: CellCallbackParams) =>
        (params.data as DartHistoryRow | undefined)?.raRaised
          ? 'Raised'
          : 'Not Raised'
    },
    {
      field: 'equipmentNomenclature',
      headerName: 'Equipment Nomenclature',
      flex: 2,
      minWidth: 250
    },
    {
      field: 'defectDescription',
      headerName: 'Defect Description',
      flex: 2,
      minWidth: 220
    },
    {
      field: 'id',
      headerName: 'Actions',
      flex: 1,
      minWidth: 120,
      sortable: false,
      filter: false,
      cellRenderer: () => `
      <button type="button" class="history-action-btn">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round">
          <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"></path>
          <circle cx="12" cy="12" r="3"></circle>
        </svg>
      </button>
    `,
      onCellClicked: (params: CellCallbackParams) => {
        this.goToView(params.data as DartHistoryRow | undefined);
      }
    }
  ];

  async search(): Promise<void> {
  const payload = {
    maintenancePeriod: this.form.value.maintenancePeriod || '',
    dartOccasion: this.form.value.dartOccasion || '',
    dartType: this.form.value.dartType || '',
    equipmentSearch: this.form.value.equipment || '',
    subDepartment: this.form.value.subDepartment || '',
    department: this.form.value.department || '',
    defectDateFrom: this.form.value.dateFrom || '',
    defectDateTo: this.form.value.dateTo || ''
  };

  try {
    const res: DartHistoryResponse = await firstValueFrom(this.call.getFilteredDartHistory(payload));

    this.errorMessage = '';

    const rows = res.data || [];

    this.rowData.set(rows)



    if (!this.rowData().length) {
      this.errorMessage = 'No records found';
    }
  } catch {
    this.errorMessage = 'Failed to load filtered records';
    this.rowData.set([])
  }
  }

  async loadHistoryData(): Promise<void> {
    try {
      const res: DartHistoryResponse = await firstValueFrom(this.call.getDartHistory());

      this.errorMessage = '';

      const rows = res.data || [];
      this.rowData.set(rows)

      this.dartOccasionOptions.set([
        ...(res.filters?.dartOccasions || []).map((item: string) => ({
          label: item,
          value: item
        }))
      ]);

      this.dartTypeOptions.set([
        ...(res.filters?.dartTypes || []).map((item: string) => ({
          label: item,
          value: item
        }))
      ]);

      this.subDepartmentOptions.set([
        { label: 'All', value: '' },
        ...(res.filters?.subDepartments || []).map((item: string) => ({
          label: item,
          value: item
        }))
      ]);

      this.departmentOptions.set([
        { label: 'All', value: '' },
        ...(res.filters?.departments || []).map((item: string) => ({
          label: item,
          value: item
        }))
      ]);

      this.maintenancePeriodOptions.set([
        ...(res.filters?.dartMaintenancePeriod || []).map((item: string) => ({
          label: item,
          value: item
        }))
      ]);

      this.equipmentOptions.set([
        { label: 'All', value: '' },
        ...(res.filters?.equipments || []).map((item: string) => ({
          label: item,
          value: item
        }))
      ]);
      this.nomenclatureOptions.set([
         { label: 'All', value: '' },
        ...(res.filters?.equipment_nomenclatures || []).map((item: string) => ({
          label: item,
          value: item
        }))
      ]);

    } catch {
      this.errorMessage = 'Failed to load DART History or Filters';
      this.rowData.set([])
    }
  }

  goToView(row: DartHistoryRow | undefined): void {
    this.router.navigate(
      ['/afterAuth/op-maintenance/history/view-action'],
      {
        state: {
          dartData: row
        }
      }
    );
  }

  syncWithCMMS(): void {
    this.toastr.success('Synced with CMMS.');
  }

  print(): void {
    window.print();
  }

  exportPlaceholder(format: string): void {
    this.toastr.info(`Export to ${format} is not wired up yet — this is a placeholder action.`);
  }

}
