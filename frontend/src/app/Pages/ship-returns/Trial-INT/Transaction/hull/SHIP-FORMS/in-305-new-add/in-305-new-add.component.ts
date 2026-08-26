import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import {
  LucideAngularModule,
  RotateCcw,
  Save,
  SaveAllIcon,
} from '../../../../ui/lucide-compat';
// import { MasterService } from '../../../../services/master.service';
import { ApiService } from '../../../../api.service';
import { ToastService } from '../../../../services/toast.service';
import { Apiendpoints } from '../../../../ApiEndPoints';
import { CommonModule } from '@angular/common';
import { FormCardComponent } from '../../../../ui/form-card/form-card.component';
import { LoadingButtonComponent } from '../../../../ui/loading-button.component';
import { ToastComponent } from '../../../../ui/master-compat';
import { SelectComponent as NewSelectComponent } from '../../../../ui/select.component';
import { InputComponent } from '../../../../ui/input.component';
import { FileUploadComponent } from '../../../../ui/file-upload/file-upload.component';

import { finalize } from 'rxjs';
import {
  ReusableInputTableComponent,
  ReusableTableColumn,
} from '../../../../ui/reusable-input-table/reusable-input-table.component';
import { ApprovalWorkFlow } from '../../../../ui/approval-work-flow/approval-work-flow';
import { CalenderComponent } from '../../../../ui/calender.component';
import { ReusableButtonComponent } from '../../../../ui/master-compat';

@Component({
  selector: 'app-in-305-new-add',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormCardComponent,
    LucideAngularModule,
    LoadingButtonComponent,
    ToastComponent,
    NewSelectComponent,
    InputComponent,
    FileUploadComponent,
    ReusableButtonComponent,
    ReusableInputTableComponent,
    ApprovalWorkFlow,
    CalenderComponent,
  ],
  templateUrl: './in-305-new-add.html',
})
export class In305NewAdd implements OnInit {
  readonly draftIcon = Save;
  readonly saveIcon = SaveAllIcon;
  readonly restartIcon = RotateCcw;

  editMode = false;
  viewMode = false;
  rowId!: string | null;
  editDataDetails: any = null;
  showApprovalWorkflowPopup = false;
  addButtonText = 'Add new record';
  user: any = null;
  LoggedInUser = '';

  form!: FormGroup;
  saveLoading = false;
  draftLoading = false;

  selectedShipStaffFile: File | null = null;
  selectedHodFile: File | null = null;

  shipOptions: any[] = [];
  forwardToOptions: any[] = [];
  dockYardOptions: any[] = [];

  totalRows = 1;
  tableData: any[] = [];

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    // private masterService: MasterService,
    private apiService: ApiService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
    // private storageService: StorageService,
  ) {}

  getUser(): any {
    try {
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  }

  ngOnInit(): void {
    this.buildForm();
    const mode = this.route.snapshot.data['mode'];
    this.updateOpsTableRows(this.totalRows);

    this.editMode = mode === 'edit';
    this.viewMode = mode === 'view';
    this.rowId = this.route.snapshot.paramMap.get('id');

    this.user = this.getUser();
    this.LoggedInUser = this.user?.process_name || this.user?.role_center?.[0]?.process_name || '';

    this.loadShips();
    this.loadDockyard();

    const shipId = this.user?.ship_id || this.user?.role_center?.[0]?.ship_id;
    if (shipId && !this.rowId) {
      this.form.patchValue({
        ship_id: shipId,
      });
    }

    if (this.rowId) {
      this.getFormDetailsByRowId(this.rowId);
    }

    if (this.viewMode) {
      this.form.disable();
    }
    console.log('dockYardOptions', this.dockYardOptions);
  }

  loadShips() {
    this.apiService.get(Apiendpoints.MASTER_SHIP).subscribe((res: any) => {
      const dataList = res?.results || res?.data || [];
      this.shipOptions = dataList.map((item: any) => ({
        label: item.name,
        value: item.id,
      }));

      // ✅ AUTO SELECT if only one ship
      if (this.shipOptions.length === 1) {
        this.form.patchValue({
          ship_id: this.shipOptions[0].value,
        });
      }
      this.cdr.detectChanges();
    });
  }

  clear() {
    this.form.reset();
  }

  loadDockyard() {
    this.apiService.get(Apiendpoints.MASTER_DOCKYARD).subscribe((res: any) => {
      const dataList = res?.results || res?.data || [];
      this.dockYardOptions = dataList.map((item: any) => ({
        label: item.name,
        value: item.id,
      }));
      this.tableColumns = this.tableColumns.map((col) => {
        if (col.field === 'dockyard') {
          return { ...col, options: this.dockYardOptions };
        }
        return col;
      });
      this.cdr.detectChanges();
    });
  }
  buildForm() {
    this.form = this.fb.group({
      ship_id: ['', Validators.required],
      date_of_return: ['', Validators.required],
      forward_to: ['', Validators.required],
    });
  }

  onFileChange(file: File, type: 'shipStaff' | 'hod') {
    if (type === 'shipStaff') {
      this.selectedShipStaffFile = file;
    } else if (type === 'hod') {
      this.selectedHodFile = file;
    }
  }
  // ------------------------- FORM TABLE CONFIGURATIONS ----------------------
  tableColumns: ReusableTableColumn[] = [
    { field: 's_no', header: 'Ser', width: '70px', align: 'center' as const },
    {
      field: 'chain_cable_fitting',
      header: 'Chain Cable and Gear Para vane Towing Chains and Fitting ',
      template: 'inputTpl',
      width: '350px',
    },
    {
      field: 'quantity',
      header: 'Quantity',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'thickness_weight',
      header: 'Thickness/Weight (Diameter)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'initially_supplied_by',
      header: 'Initially Supplied By',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'initialy_supplied_on',
      header: 'Initially Supplied On',
      fieldType: 'date',
      width: '300px',
    },
    {
      field: 'dockyard',
      header: 'Dockyard Where Last Carried Out',
      fieldType: 'drop-down',
      options: this.dockYardOptions,
      width: '350px',
    },
    {
      field: 'dockyard_retest_date',
      header: 'Dockyard Retesting Date',
      fieldType: 'date',
      width: '200px',
    },
    {
      field: 'half_yearly_survey',
      header: 'Last survey date',
      fieldType: 'date',
      width: '200px',
    },
    {
      field: 'annealing',
      header: 'Annealing (if valid)',
      fieldType: 'date',
      width: '200px',
    },
  ];

  onOpsRowCountChange(event: Event) {
    let value = +(event.target as HTMLInputElement).value;
    if (!value || value < 1) value = 1;
    this.totalRows = value;
    this.updateOpsTableRows(value);
    this.cdr.detectChanges();
  }
  updateOpsTableRows(count: number) {
    const currentLength = this.tableData.length;
    if (count > currentLength) {
      for (let i = currentLength; i < count; i++) {
        this.tableData.push({
          s_no: i + 1,
          chain_cable_fitting: '',
          quantity: '',
          thickness_weight: '',
          initially_supplied_by: '',
          initialy_supplied_on: null,
          dockyard: '',
          dockyard_retest_date: null,
          half_yearly_survey: null,
          annealing: null,
        });
      }
    }
    if (count < currentLength) {
      this.tableData.splice(count);
    }
    this.tableData = [...this.tableData];
  }

  handleOpsTableChange(index: number, field: string, value: string) {
    if (this.viewMode) return;
    this.tableData[index][field] = value;
  }

  onApprovalPopupChange(open: boolean): void {
    this.showApprovalWorkflowPopup = open;
    this.cdr.detectChanges();
  }

  openApprovalWorkflow(): void {
    this.showApprovalWorkflowPopup = true;
    this.cdr.detectChanges();
  }

  handleBack() {
    this.router.navigate(['/afterAuth/ship-returns/hull-returns/returns/in-305']);
  }
  validateForm(): boolean {
    // Check main form
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.toastService.showError('Please fill all required fields correctly.');
      return false;
    }
    return true;
  }

  getFormDetailsByRowId(rowId: string) {
    this.apiService.get(`${Apiendpoints.IN_305}${rowId}/`).subscribe({
      next: (res: any) => {
        if (!res?.data) return;

        const data = res.data;
        this.editDataDetails = data;

        // ✅ ---------------- FORM PATCH ----------------
        this.form.patchValue({
          ship_id: data.ship?.id || '',
          forward_to: data.forward_to || '',
        });

        // ✅ ---------------- TABLE DATA ----------------
        this.tableData = (data.chain_data || []).map(
          (item: any, index: number) => ({
            id: item.id,
            s_no: index + 1,
            chain_cable_fitting: item.chain_cable_fitting || '',
            quantity: item.quantity || '',
            thickness_weight: item.thickness_weight || '',
            initially_supplied_by: item.initially_supplied_by || '',
            initialy_supplied_on: item.initially_supplied_on || null,
            dockyard: item.dockyard || '',
            dockyard_retest_date: item.dockyard_retest_date || null,
            half_yearly_survey: item.half_yearly_survey || null,
            annealing: item.annealing || null,
          }),
        );

        // ✅ Ensure at least 1 row exists
        this.totalRows = this.tableData.length || 1;

        if (this.tableData.length === 0) {
          this.updateOpsTableRows(1);
        }

        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error(err);
        this.toastService.showError('Failed to load data.');
      },
    });
  }

  /* ----------------------------- CHECKING AND REMOVING EMPTY ROWS ----------------------------------- */

  isTableRowEmpty(item: any): boolean {
    return !(
      item?.chain_cable_fitting ||
      item?.quantity ||
      item?.thickness_weight ||
      item?.initially_supplied_by ||
      item?.initialy_supplied_on ||
      item?.dockyard ||
      item?.dockyard_retest_date ||
      item?.half_yearly_survey ||
      item?.annealing
    );
  }

  async handleSave(draftStatus: 'draft' | 'save') {
    if (draftStatus === 'save' && !this.validateForm()) {
      return;
    }

    if (draftStatus === 'save') {
      this.saveLoading = true;
    } else {
      this.draftLoading = true;
    }

    const formattableData = this.tableData
      .filter((item: any) => !this.isTableRowEmpty(item))
      .map((item: any, index: number) => ({
        ...item,
        id: item?.id || null,
        s_no: index + 1,
      }));

    const formValues = this.form.value;

    const payload: any = { draft_status: draftStatus, ...formValues };
    payload.chain_data = formattableData;
    if (this.editMode) {
      payload.id = this.editDataDetails.id;
    }

    // ----------- NEEDED 305 API ENDPOINT
    this.apiService
      .post(Apiendpoints.IN_305, payload)
      .pipe(
        finalize(() => {
          if (draftStatus === 'save') {
            this.saveLoading = false;
          } else {
            this.draftLoading = false;
          }
          this.cdr.detectChanges();
        }),
      )
      .subscribe({
        next: (res: any) => {
          this.toastService.showSuccess(
            res?.message || 'In-305 request saved successfully',
          );
          if (draftStatus === 'save') {
            const savedId =
              res?.data?.id ??
              res?.data?.rowId ??
              res?.id ??
              this.editDataDetails?.id;

            if (savedId) {
              this.rowId = String(savedId);
              if (res?.data) {
                this.editDataDetails = res.data;
              } else if (this.editDataDetails) {
                this.editDataDetails.id = savedId;
              }
              this.openApprovalWorkflow();
            } else {
              this.toastService.showError(
                'Record saved, but approval workflow could not be opened.',
              );
            }
          } else {
            setTimeout(() => {
              this.router.navigate(['/afterAuth/ship-returns/hull-returns/returns/in-305']);
            }, 1000);
          }
        },
        error: () => {
          this.toastService.showError('Failed to save In-305 data.');
        },
      });
  }
}
