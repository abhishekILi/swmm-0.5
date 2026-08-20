import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { CellCallbackParams, ColDef } from 'ag-grid-community';
import { Subject, debounceTime } from 'rxjs';

import { DataGrid } from '../../../../../shared/components/data-grid/data-grid';
import { SelectInput } from '../../../../../shared/components/select-input/select-input';
import { Call } from '../../../../../services/network/call';

export interface EquipmentRunningRow {
  month: string;
  equipmentNomenclature: string;
  startLocation: string;
  hoursRun: number;
  startTime: string;
  stopTime: string;
  entryCreatedOn: string;
  createdBy: string;
}

interface EquipmentRunningApiItem {
  month: string;
  equipment_nomenclature: string;
  start_location: string;
  hours_run: number;
  start_time: string;
  stop_time: string;
  entry_created_on: string;
  created_by: string;
}

interface EquipmentRunningApiResponse {
  result?: EquipmentRunningApiItem[];
  months?: string[];
  equipments?: string[];
}

@Component({
  selector: 'app-search-equipment-running-history',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    DataGrid,
    SelectInput,
  ],
  templateUrl: './search-equipment-running-history.html',
  styleUrl: './search-equipment-running-history.scss',
})
export class SearchEquipmentRunningHistory implements OnInit {
  private call = inject(Call);

  /* ------------------------------------------------------------------ */
  /*  Filter state                                                         */
  /* ------------------------------------------------------------------ */
  selectedMonth = 'All';
  selectedEquipment = 'All';
  searchText = '';

  monthOptions = [
    { label: 'All', value: 'All' }
  ];

  equipmentOptions = [
    { label: 'All', value: 'All' }
  ];

  private readonly filtersChanged = new Subject<void>();

  /* ------------------------------------------------------------------ */
  /*  Column definitions                                                   */
  /* ------------------------------------------------------------------ */
  columnDefs: ColDef[] = [
    {
      headerName: 'Month',
      field: 'month',
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
      headerName: 'Start Location',
      field: 'startLocation',
      flex: 1.5,
      minWidth: 180
    },
    {
      headerName: 'Hours Run',
      field: 'hoursRun',
      flex: 1,
      minWidth: 120,
      valueFormatter: (params: CellCallbackParams) => `${params['value']} hrs`
    },
    {
      headerName: 'Start Time',
      field: 'startTime',
      flex: 1.8,
      minWidth: 220
    },
    {
      headerName: 'Stop Time',
      field: 'stopTime',
      flex: 1.8,
      minWidth: 220
    },
    {
      headerName: 'Entry Created On',
      field: 'entryCreatedOn',
      flex: 1.8,
      minWidth: 220
    },
    {
      headerName: 'Created By',
      field: 'createdBy',
      flex: 1.2,
      minWidth: 150
    }
  ];

  filteredRows = signal<EquipmentRunningRow[]>([]);

  loadEquipmentRunningHistory(): void {

    this.call
      .getEquipmentRunningHistory({
        equipment: this.selectedEquipment,
        month: this.selectedMonth,
        search: this.searchText.trim(),
      })
      .subscribe({
        next: (raw: unknown) => {
          const res = raw as EquipmentRunningApiResponse;

          this.filteredRows.set(
            (res.result || []).map((item: EquipmentRunningApiItem) => ({
              month: item.month,
              equipmentNomenclature: item.equipment_nomenclature,
              startLocation: item.start_location,
              hoursRun: item.hours_run,
              startTime: item.start_time,
              stopTime: item.stop_time,
              entryCreatedOn: item.entry_created_on,
              createdBy: item.created_by
            }))
          );

          this.monthOptions = [
            { label: 'All', value: 'All' },
            ...(res.months || []).map((month: string) => ({
              label: month,
              value: month
            }))
          ];

          this.equipmentOptions = [
            { label: 'All', value: 'All' },
            ...(res.equipments || []).map((equipment: string) => ({
              label: equipment,
              value: equipment
            }))
          ];
        },

        error: (err: HttpErrorResponse) => {
          console.error('Equipment Running History API Error', err);
          this.filteredRows.set([]);
        }
      });

  }

  ngOnInit(): void {
    this.loadEquipmentRunningHistory();

    // Backend does the filtering — debounce so typing/dropdown changes don't
    // fire a request per keystroke/click.
    this.filtersChanged
      .pipe(debounceTime(300))
      .subscribe(() => this.loadEquipmentRunningHistory());
  }

  onFilterChange(): void {
    this.filtersChanged.next();
  }

  onSearchChange(): void {
    this.filtersChanged.next();
  }

  clearFilters(): void {
    this.selectedMonth = 'All';
    this.selectedEquipment = 'All';
    this.searchText = '';
    this.loadEquipmentRunningHistory();
  }
}
