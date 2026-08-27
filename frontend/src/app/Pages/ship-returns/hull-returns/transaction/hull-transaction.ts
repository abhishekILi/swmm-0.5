import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, inject, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { defaultIfEmpty, finalize, forkJoin, Subject, debounceTime } from 'rxjs';
import { ColDef } from 'ag-grid-community';
import { PaginateTableComponent } from '../../Trial-INT/ui/paginate-table/paginate-table.component';
import { SelectComponent } from '../../Trial-INT/ui/select.component';
import { AgActionCellComponent } from '../../Trial-INT/ui/master-compat';
import { ApiService, DropdownOption, RequestParams } from '../../Trial-INT/api.service';
import { NotificationService } from '../../../../Core/services/notification/notification.service';
import { AppService } from '../../../../Core/services/app/app.service';

const STATIC_STATUS: DropdownOption<string>[] = [
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
];

@Component({
  selector: 'app-hull-transaction',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    PaginateTableComponent,
    SelectComponent,
  ],
  templateUrl: './hull-transaction.html',
  styleUrl: './hull-transaction.css',
  providers: [ApiService],
})
export class HullTransaction implements OnInit, OnDestroy {
  private readonly apiService = inject(ApiService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly ngZone = inject(NgZone);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly notificationService = inject(NotificationService);
  private readonly appService = inject(AppService);

  @ViewChild('paginateTable') paginateTable!: PaginateTableComponent;

  addButtons = [
    { label: 'Initiate', key: 'add', show: true, cls: 'bg-blue-900 text-white' },
  ];

  selectedTrialUnit: string | number | null = null;
  selectedStatus: string | null = null;

  trialUnitOptions: DropdownOption[] = [];
  statusOptions: DropdownOption<string>[] = [...STATIC_STATUS];

  currentTableUrl = 'api/data/trials/?type=hull';
  private readonly destroy$ = new Subject<void>();

  columnDefs: ColDef[] = [
    {
      headerName: '#',
      valueGetter: (params: any) => (params.node?.rowIndex ?? 0) + 1,
      minWidth: 50,
      maxWidth: 70,
      filter: false,
    },
    { headerName: 'Date', field: 'trial_date', flex: 1 },
    { headerName: 'Trial Number', field: 'trial_number', flex: 1.2, minWidth: 180 },
    { headerName: 'Trial Unit', field: 'trial_unit_name', flex: 1, minWidth: 150 },
    { headerName: 'Satellite Unit', field: 'satellite_unit_name', flex: 1, minWidth: 180 },
    { headerName: 'Ship', field: 'ship_name', flex: 1, minWidth: 150 },
    { headerName: 'Trial Type', field: 'trial_type_name', flex: 1.5, minWidth: 150 },
    {
      headerName: 'Equipment',
      field: 'equipment_details',
      minWidth: 250,
      flex: 2,
      cellRenderer: (params: any) => {
        const details = params.data?.equipment_details;
        if (Array.isArray(details) && details.length > 0) {
          return details
            .map((item: any) => `${item.equipment_name || ''}${item.nomenclature ? ` (${item.nomenclature})` : ''}`)
            .join('<br/>');
        }
        return params.data?.equipment_name || '';
      },
    },
    {
      headerName: 'Action',
      field: 'actions',
      minWidth: 180,
      pinned: 'right',
      sortable: false,
      filter: false,
      cellRenderer: AgActionCellComponent,
      cellRendererParams: {
        actionDisplayMode: 'float',
        onAction: (k: string, r: any) => this.handleAction(k, r),
        actions: [
          { key: 'edit', label: 'Edit', iconClass: 'fa fa-edit', btnClass: 'bg-blue-100 text-blue-600 hover:bg-blue-200' },
          { key: 'view', label: 'View', iconClass: 'fa fa-eye', btnClass: 'bg-green-100 text-green-600 hover:bg-green-200' },
          { key: 'status', label: 'Status', iconClass: 'fa fa-info-circle', btnClass: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200' },
          { key: 'delete', label: 'Delete', iconClass: 'fa fa-trash', btnClass: 'bg-red-100 text-red-600 hover:bg-red-200' },
        ],
      },
    },
  ];

  ngOnInit(): void {
    this.loadDropdowns();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadDropdowns(): void {
    this.apiService.getDropdownData('master/trial-units/', { labelKey: 'name', valueKey: 'id' })
      .pipe(defaultIfEmpty([]))
      .subscribe((units) => {
        this.trialUnitOptions = units;
        this.cdr.markForCheck();
      });
  }

  onFilterChange(): void {
    const params: string[] = ['type=hull'];
    if (this.selectedTrialUnit) params.push(`trial_unit_id=${this.selectedTrialUnit}`);
    if (this.selectedStatus) params.push(`status=${this.selectedStatus}`);
    this.currentTableUrl = `api/data/trials/?${params.join('&')}`;
    this.cdr.detectChanges();
  }

  clearFilters(): void {
    this.selectedTrialUnit = null;
    this.selectedStatus = null;
    this.onFilterChange();
  }

  openInitiateForm(): void {
    console.log('Initiate form clicked');
  }

  handleAction(action: string, rowData: any): void {
    console.log('Action triggered:', action, rowData);
  }
}
