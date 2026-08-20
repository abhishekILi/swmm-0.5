import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { ColDef } from 'ag-grid-community';

import { DataGrid } from '../../../../shared/components/data-grid/data-grid';
import { SmpAmpEampNomenclatureComponent } from './smp-amp-eamp-nomenclature/smp-amp-eamp-nomenclature.component';
import { OnInit } from '@angular/core';
import { Call } from '../../../../services/network/call';
import { AmendNomenclatureModalComponent } from './smp-amp-eamp-nomenclature/amend-nomenclature-modal/amend-nomenclature-modal.component';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import {
  MaintenancePeriodApiItem,
  MaintenanceRow,
  RefitAndOperationalOccasionResponse,
} from './maintenance-period.model';

@Component({
  selector: 'app-masters',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    DataGrid,
    SmpAmpEampNomenclatureComponent,
    AmendNomenclatureModalComponent,
    IconComponent
  ],
  templateUrl: './masters.component.html',
  styleUrls: ['./masters.component.scss']
})
export class MastersComponent implements OnInit {
  private call = inject(Call);

  activeTab = 'refit';
  private _searchText = '';
  private readonly searchChanged = new Subject<string>();


  get searchText(): string {
    return this._searchText;
  }

  set searchText(value: string) {
    this._searchText = value;
    this.searchChanged.next(value);
  }

  showAmendModal = false;

  selectedRow: MaintenanceRow | null = null;
  rowData = signal<MaintenanceRow[]>([]);
  plannedStartDate = '';
  plannedEndDate = '';

  loading = false;

  ngOnInit(): void {
    void this.loadRefitData();

    // The backend does the filtering (see `search` query param on
    // refit_and_operational_occation/) — debounce keystrokes rather than
    // filtering the already-fetched rows client-side.
    this.searchChanged.pipe(debounceTime(300), distinctUntilChanged()).subscribe((search) => {
      void this.loadRefitData(search);
    });
  }

  async loadRefitData(search?: string): Promise<void> {
    this.loading = true;

    try {
      const raw: unknown = await firstValueFrom(this.call.getRefitAndOperationalOccation(search));
      const res = raw as RefitAndOperationalOccasionResponse;
      console.log('res refit data' , res)

      const toRow = (item: MaintenancePeriodApiItem): MaintenanceRow => ({
        id: item.id,
        type: item.type,
        name: item.name,
        maintenancePeriod: item.maintenance_period,
        actualStartDate: item.actual_start_date,
        actualEndDate: item.actual_end_date
      });

      // Create Refit Nomenclature only ever shows refit_periods.
      const rows = (res.refit_periods ?? []).map(toRow);

      console.log('Grid rows:', rows);

      // Update signal
      this.rowData.set(rows);
    } catch (err) {
      console.error('Failed to load data', err);
    } finally {
      this.loading = false;
    }
  }

  columnDefs: ColDef[] = [
  {
    field: 'type',
    headerName: 'Type',
    flex: 2,
    maxWidth: 100
  },
  {
    field: 'name',
    headerName: 'Nomenclature Name',
    flex: 2,
    minWidth: 300
  },
  {
    field: 'maintenancePeriod',
    headerName: 'Maintenance Period'
  },
  {
    field: 'actualStartDate',
    headerName: 'Actual Start Date'
  },
  {
    field: 'actualEndDate',
    headerName: 'Actual End Date'
  },
   {
  field: 'id',
  headerName: 'Actions',
  flex: 1,
  minWidth: 150,
  sortable: false,
  filter: false,
  cellRenderer: () => {
    return `
      <button
        type="button"
        class="amend-action-btn glass-card px-3 py-1 rounded bg-blue-600 text-white">
        Amend
      </button>
    `;
  },
  onCellClicked: (params) => {
    if (params.data) {
      this.openAmendModal(params.data as MaintenanceRow);
    }
  }
}
  ];

  setTab(tab: 'refit' | 'smp'): void {
    this.activeTab = tab;
  }

  exportPdf(): void {
    console.log("")

  }

  exportExcel(): void {
    console.log("")

  }

  print(): void {
    window.print();
  }

  openAmendModal(row: MaintenanceRow): void {

    this.selectedRow = row;

    this.plannedStartDate = row.actualStartDate || '';
    this.plannedEndDate = row.actualEndDate || '';

    this.showAmendModal = true;
  }

  closeAmendModal(): void {
    this.showAmendModal = false;
    this.selectedRow = null;
  }

  saveChanges(): void {
    this.showAmendModal = false;
    this.selectedRow = null;
    void this.loadRefitData(this.searchText);
  }
  closeModal(): void {
    this.showAmendModal = false;
  }
}
