import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule
} from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { SelectInput } from '../../../../../shared/components/select-input/select-input';
import { DataGrid } from '../../../../../shared/components/data-grid/data-grid';

import { AmendNomenclatureModalComponent } from './amend-nomenclature-modal/amend-nomenclature-modal.component';

import { ColDef } from 'ag-grid-community';
import { Call } from '../../../../../services/network/call';
import { NotificationService } from '../../../../../Core/services/notification/notification.service';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { HttpErrorResponse } from '@angular/common/http';
import {
  MaintenancePeriodApiItem,
  MaintenanceRow,
  RefitAndOperationalOccasionResponse,
} from '../maintenance-period.model';

@Component({
  selector: 'app-smp-amp-eamp',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, SelectInput, DataGrid, AmendNomenclatureModalComponent, IconComponent],
  templateUrl: './smp-amp-eamp-nomenclature.component.html',
  styleUrl: './smp-amp-eamp-nomenclature.component.scss'
})
export class SmpAmpEampNomenclatureComponent implements OnInit {
  private fb = inject(FormBuilder);
  private call = inject(Call);
  private toastr = inject(NotificationService);
  rowData = signal<MaintenanceRow[]>([]);
  loading = false;
  maintenanceForm!: FormGroup;

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

  refitTypeOptions = [
    {
      label: 'SMP',
      value: 'SMP'
    },
    {
      label: 'AMP',
      value: 'AMP'
    },
    {
      label: 'EAMP',
      value: 'EAMP'
    }
  ];
  ngOnInit(): void {
    this.maintenanceForm = this.fb.group({
      type: [''],
      startDate: [''],
      endDate: ['']
    });
    void this.loadRefitData();

    // The backend does the filtering (see `search` query param on
    // refit_and_operational_occation/) — debounce keystrokes rather than
    // filtering the already-fetched rows client-side.
    this.searchChanged.pipe(debounceTime(300), distinctUntilChanged()).subscribe((search) => {
      void this.loadRefitData(search);
    });
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
      cellRenderer: () => `
        <button type="button" class="amend-action-btn">
          Amend
        </button>
      `,
      onCellClicked: (params) => {
        const target = (params['event'] as Event | undefined)?.target as HTMLElement | undefined;

        if (target?.closest('.amend-action-btn') && params.data) {
          this.openAmendModal(params.data as MaintenanceRow);
        }
      }
    }
  ];

  async loadRefitData(search?: string): Promise<void> {
    this.loading = true;

    try {
      const raw: unknown = await firstValueFrom(this.call.getRefitAndOperationalOccation(search));
      const res = raw as RefitAndOperationalOccasionResponse;

      console.log("res smp", res)

      const toRow = (item: MaintenancePeriodApiItem): MaintenanceRow => ({
        id: item.id,
        type: item.type,
        name: item.name,
        maintenancePeriod: item.maintenance_period,
        actualStartDate: item.actual_start_date,
        actualEndDate: item.actual_end_date
      });

      // Create SMP/AMP/EAMP Nomenclature only ever shows maint_periods.
      const rows = (res.maint_periods || []).map(toRow);
      this.rowData.set(rows)
    } catch (err) {
      console.error('Failed to load data', err);
    } finally {
      // Guaranteed to run whether the request succeeds, errors, or the
      // mapping above throws — the overlay can never get stuck showing
      // "Loading…" forever regardless of what happens above.
      this.loading = false;
    }
  }

  async addMaintenancePeriod(): Promise<void> {
    const payload = {
      action: '',
      start_date: this.maintenanceForm.value.startDate,
      completion_date: this.maintenanceForm.value.endDate,
      refit_type: this.maintenanceForm.value.type
    };

    try {
      await firstValueFrom(this.call.refitAndOperationalOccation(payload));
      this.toastr.success(
        'Nomenclature created successfully',
        'Success'
      );
      this.maintenanceForm.reset();
      await this.loadRefitData(this.searchText);
    } catch (err) {
      console.error('Save failed', err);
      this.toastr.error((err as HttpErrorResponse).message);
    }
  }

  openAmendModal(row: MaintenanceRow): void {
    this.selectedRow = row;
    this.showAmendModal = true;
  }

  closeModal(): void {
    this.showAmendModal = false;
  }

  saveChanges(): void {
    this.showAmendModal = false;
    this.selectedRow = null;
    void this.loadRefitData(this.searchText);
  }
}
