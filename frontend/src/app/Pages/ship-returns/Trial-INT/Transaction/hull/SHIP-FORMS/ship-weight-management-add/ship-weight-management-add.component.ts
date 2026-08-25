import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { FormCardComponent } from '../../../../ui/form-card/form-card.component';
import {
  LucideAngularModule,
  RotateCcw,
  Save,
  SaveAllIcon,
  Trash,
} from '../../../../ui/lucide-compat';
import { LoadingButtonComponent } from '../../../../ui/loading-button.component';
import { ReusableButtonComponent, ToastComponent } from '../../../../ui/master-compat';
import { SelectComponent as NewSelectComponent } from '../../../../ui/select.component';
// import { MasterService } from '../../../../services/master.service';
import { ApiService } from '../../../../api.service';
import { ToastService } from '../../../../services/toast.service';
import { Apiendpoints } from '../../../../ApiEndPoints';
import { ReusableInputTableComponent } from '../../../../ui/reusable-input-table/reusable-input-table.component';
import { CalenderComponent } from '../../../../ui/calender.component';
// import { ReusableButtonComponent } from '../../../../ui/master-compat';
import { finalize } from 'rxjs';
import { FileUploadComponent } from '../../../../ui/file-upload/file-upload.component';
import { ApprovalWorkFlow } from '../../../../ui/approval-work-flow/approval-work-flow';
// import { TabStateService } from '../../../../services/tab-state.service';
@Component({
  selector: 'app-ship-weight-management-add',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormCardComponent,
    LucideAngularModule,
    LoadingButtonComponent,
    ToastComponent,
    NewSelectComponent,
    ReusableInputTableComponent,
    CalenderComponent,
    ReusableButtonComponent,
    FileUploadComponent,
    ApprovalWorkFlow,
  ],
  templateUrl: './ship-weight-management-add.component.html',
})
export class ShipWeightManagementAddComponent implements OnInit {
  editMode = false;
  viewMode = false;

  rowId!: string | null;
  editDataDetails: any = null;
  addButtonText = 'Add new record';
  showApprovalWorkflowPopup = false;
  workflowTrialId: string = '';
  readonly draftIcon = Save;
  readonly saveIcon = SaveAllIcon;
  readonly restartIcon = RotateCcw;
  readonly deleteIcon = Trash;

  form!: FormGroup;

  saveLoading = false;
  draftLoading = false;

  commandOptions: any[] = [];
  classOfShipOptions: any[] = [];
  shipOptions: any[] = [];
  refitStatusOptions: any[] = [];

  selectedFile!: File | null;
  activeTab = 'draft';

  totalRowsOps = 1;
  totalRowsRefit = 1;
  totalRowsOpsInEditMode = 1;
  totalRowsRefitInEditMode = 1;

  opsTableData: any[] = [];
  refitTableData: any[] = [];

  shipStatusOptions = [
    { label: '--Select--', value: '' },
    { label: 'OPS', value: 'ops' },
    { label: 'REFIT', value: 'refit' },
  ];

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    // private masterService: MasterService,
    private apiService: ApiService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
    // private storageService: StorageService,
    // private tabStateService: TabStateService,
  ) {}
  user: any = null;
  LoggedInUser = '';

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
    this.user = this.getUser();
    this.LoggedInUser = this.user?.process_name || this.user?.user_roles?.[0]?.process_name || '';

    if (this.LoggedInUser === 'Ship Staff') {
      this.loadShips();

      const shipId = this.user?.ship_id || this.user?.user_roles?.[0]?.ship_id;

      if (shipId) {
        this.form.patchValue({
          ship: shipId,
        });
      }
    } else {
      this.loadCommands();
      this.loadClasses();
      this.listenToCommandAndClassChanges();
    }
    // this.tabStateService.activeTab$.subscribe((tab) => {
    //   this.activeTab = tab;
    // });

    this.cdr.detectChanges();

    const mode = this.route.snapshot.data['mode'];

    this.editMode = mode === 'edit';
    this.viewMode = mode === 'view';
    this.rowId = this.route.snapshot.paramMap.get('id');

    if (this.rowId) {
      this.getFormDetailsByRowId(this.rowId);
    }

    this.handleDependentDropdowns();
    this.updateOpsTableRows(this.totalRowsOps);
    this.updateRefitTableRows(this.totalRowsRefit);

    if (this.viewMode) {
      this.form.disable();
    }
  }
  onApprovalPopupChange(open: boolean): void {
    this.showApprovalWorkflowPopup = open;
    this.cdr.detectChanges();
  }
  openApprovalWorkflow(): void {
    this.showApprovalWorkflowPopup = true;
    this.workflowTrialId = this.rowId || this.form.get('id')?.value || '';
    this.cdr.detectChanges();
  }

  loadCommands() {
    this.apiService.get(Apiendpoints.MASTER_COMMANDS).subscribe((res: any) => {
      const dataList = res?.results || res?.data || [];
      this.commandOptions = dataList.map((item: any) => ({
        label: item.name,
        value: item.id,
      }));
      this.cdr.detectChanges();
    });
  }

  loadClasses() {
    this.apiService.get(Apiendpoints.MASTER_CLASS).subscribe((res: any) => {
      const dataList = res?.results || res?.data || [];
      this.classOfShipOptions = dataList.map((item: any) => ({
        label: item.name,
        value: item.id,
      }));
      this.cdr.detectChanges();
    });
  }

  loadRefits() {
    this.apiService.get(Apiendpoints.MASTER_REFITS).subscribe((res: any) => {
      const dataList = res?.results || res?.data || [];
      this.refitStatusOptions = dataList.map((item: any) => ({
        label: item.name,
        value: item.id,
      }));
      this.cdr.detectChanges();
    });
  }

  listenToCommandAndClassChanges() {
    this.form.get('class_of_ship')?.valueChanges.subscribe((classId: any) => {
      if (classId) {
        this.loadShipsByClass(classId);
        this.form.get('ship')?.reset();
      } else {
        this.shipOptions = [];
        this.form.get('ship')?.reset();
      }
    });
  }

  loadShipsByClass(classId: number) {
    this.apiService.get(`${Apiendpoints.MASTER_SHIP}?classofship=${classId}`).subscribe((res: any) => {
      const dataList = res?.results || res?.data || [];
      this.shipOptions = dataList.map((item: any) => ({
        label: item.name,
        value: item.id,
      }));
      this.cdr.detectChanges();
    });
  }

  loadShips(shipId?: number) {
    const user = this.getUser();
    this.apiService.get(Apiendpoints.MASTER_SHIP).subscribe((res: any) => {
      const dataList = res?.results || res?.data || [];
      this.shipOptions = dataList.map((item: any) => ({
        label: item.name,
        value: item.id,
      }));

      if (user?.ship_id && !this.shipOptions.some((s: any) => s.value === user.ship_id)) {
        this.shipOptions.unshift({ label: user.ship_name || 'INS KOLKATA', value: user.ship_id });
      }

      if (shipId || user?.ship_id) {
        this.form.patchValue({ ship: shipId || user?.ship_id });
      }
      this.cdr.detectChanges();
    });
  }

  backButton() {
    this.router.navigate(['/afterAuth/ship-returns/hull-returns/returns/ship-weight-management']);
  }

  OPSColumns = [
    { field: 's_no', header: 'Ser', width: '70px', align: 'center' as const },
    {
      field: 'lightship_displacement',
      header: 'Lightship Disp (A)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'ref_load_condition',
      header: 'Reference Loading Condition During Audit(B)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'disp_c',
      header: 'Disp in Reference as per Booklet (C)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'disp_d',
      header: 'Disp as read from drafts during Audit (D)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'net_diff',
      header: 'Net Difference in variable loads (E)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'corrected_disp',
      header: 'Corrected Disp (F)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'net_increase',
      header: 'Net Increase in Disp(G)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'percentage_increase',
      header: '% Increase (H)',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'net_weight_add',
      header: 'Net Weight Addition',
      template: 'inputTpl',
      width: '200px',
    },
    {
      field: 'net_kg_add',
      header: 'Net KG of Weight Addition',
      template: 'inputTpl',
      width: '200px',
    },
  ];

  onOpsRowCountChange(event: Event) {
    let value = +(event.target as HTMLInputElement).value;
    if (this.editMode) {
      value = Math.max(value, this.totalRowsOpsInEditMode);
    }

    this.totalRowsOps = value;
    this.updateOpsTableRows(value);
  }
  updateOpsTableRows(count: number) {
    const currentLength = this.opsTableData.length;
    if (count > currentLength) {
      for (let i = currentLength; i < count; i++) {
        this.opsTableData.push({
          s_no: i + 1,
          lightship_displacement: '',
          ref_load_condition: '',
          disp_c: '',
          disp_d: '',
          net_diff: '',
          corrected_disp: '',
          net_increase: '',
          percentage_increase: '',
          net_weight_add: '',
          net_kg_add: '',
        });
      }
    }

    if (count < currentLength) {
      this.opsTableData.splice(count);
    }
  }

  handleOpsTableChange(index: number, field: string, value: string) {
    if (this.viewMode) return;
    this.opsTableData[index][field] = value;
  }

  // ------------------------------------ REFIT TABLE DATA --------------------------------------------

  RefitColumns = [
    { field: 's_no', header: 'Ser', width: '70px', align: 'center' as const },
    {
      field: 'lightship_displacement',
      header: 'Lightship Disp (A)',
      template: 'inputTpl',
    },
    {
      field: 'wght_change_prior_refit',
      header: 'Weight change prior refit',
      template: 'inputTpl',
    },
    {
      field: 'net_wght_change_refit',
      header: 'Net weight change during refit',
      template: 'inputTpl',
    },
    {
      field: 'net_kg',
      header: 'Net KG',
      template: 'inputTpl',
    },
  ];

  onRefitRowCountChange(event: Event) {
    let value = +(event.target as HTMLInputElement).value;

    // ✅ enforce minimum in edit mode
    if (this.editMode) {
      value = Math.max(value, this.totalRowsRefitInEditMode);
    }
    this.totalRowsRefit = value;
    this.updateRefitTableRows(value);
  }
  updateRefitTableRows(count: number) {
    const currentLength = this.refitTableData.length;
    if (count > currentLength) {
      for (let i = currentLength; i < count; i++) {
        this.refitTableData.push({
          s_no: i + 1,
          lightship_displacement: '',
          wght_change_prior_refit: '',
          net_wght_change_refit: '',
          net_kg: '',
        });
      }
    }
    if (count < currentLength) {
      this.refitTableData.splice(count);
    }
  }
  handleRefitTableChange(index: number, field: string, value: string) {
    if (this.viewMode) return;
    this.refitTableData[index][field] = value;
  }

  /* -------------------------------- FORM SETUP ------------------------------- */
  buildForm() {
    this.form = this.fb.group({
      command: [''],
      class_of_ship: [''],
      ship: ['', Validators.required],
      ship_status: ['', Validators.required],
      refit_status: [''],
      refit_date: [null],
      date_of_return: [null],
      ref_auth: [''],
    });
  }

  /* ----------------------------- API CALLS ----------------------------------- */

  onFileChange(file: File) {
    this.selectedFile = file;
  }

  clear() {
    this.form.reset();
    this.selectedFile = null;
  }
  /* ------------------------ DEPENDENT DROPDOWNS ------------------------------- */

  handleDependentDropdowns() {
    this.form.get('ship_status')!.valueChanges.subscribe((status) => {
      if (status === 'refit') {
        this.loadRefits();
        this.form.get('refit_status')!.setValidators(Validators.required);
        this.form.get('refit_date')!.setValidators(Validators.required);
      } else {
        this.form.get('refit_status')!.clearValidators();
        this.form.get('refit_date')!.clearValidators();
      }
      this.form.get('refit_status')!.updateValueAndValidity();
      this.form.get('refit_date')!.updateValueAndValidity();
    });
  }

  /* ----------------------------- EDIT MODE ----------------------------------- */

  getFormDetailsByRowId(rowId: string) {
    this.apiService
      .get(`${Apiendpoints.SHIP_WEIGHT_MANAGEMENT}${rowId}/`)
      .subscribe({
        next: (res: any) => {
          if (res?.data) {
            this.editDataDetails = res.data;

            const classId = this.editDataDetails?.ship?.classofship?.id;
            const shipId = this.editDataDetails?.ship?.id;

            // ✅ Patch WITHOUT triggering valueChanges
            this.form.patchValue(
              {
                command: this.editDataDetails?.ship?.command?.id,
                class_of_ship: classId,
              },
              { emitEvent: false },
            );

            // this.masterService.getShipsByClass(classId).subscribe((res: any) => {
            //   this.shipOptions = res.data.map((item: any) => ({
            //     label: item.name,
            //     value: item.id,
            //   }));
            // });

            this.form.patchValue({
              ship: shipId,
              ship_status:
                this.editDataDetails?.ship_status === 'refit'
                  ? 'refit'
                  : this.editDataDetails?.ship_status === 'ops'
                    ? 'ops'
                    : '',
              refit_status: this.editDataDetails?.refit?.id,
              refit_date: this.editDataDetails?.refit_recommencement_date
                ? new Date(this.editDataDetails.refit_recommencement_date)
                : null,
            });

              // ✅ Ops table
              if (this.editDataDetails.ship_weight_management_ops) {
                const opsData = this.editDataDetails.ship_weight_management_ops;

                this.opsTableData = opsData.map((item: any, index: number) => ({
                  id: item.id || null,
                  s_no: index + 1,
                  lightship_displacement: item.lightship_displacement || '',
                  ref_load_condition: item.ref_load_condition || '',
                  disp_c: item.disp_c || '',
                  disp_d: item.disp_d || '',
                  net_diff: item.net_diff || '',
                  corrected_disp: item.corrected_disp || '',
                  net_increase: item.net_increase || '',
                  percentage_increase: item.percentage_increase || '',
                  net_weight_add: item.net_weight_add || '',
                  net_kg_add: item.net_kg_add || '',
                }));

                // ✅ IMPORTANT: sync row count
                this.totalRowsOps = this.opsTableData.length || 1;
                this.totalRowsOpsInEditMode = this.totalRowsOps;

                // ✅ Ensure table respects count
                this.updateOpsTableRows(this.totalRowsOps);
              }

              // ✅ Refit table
              if (this.editDataDetails.ship_weight_management_refit) {
                const refitData =
                  this.editDataDetails.ship_weight_management_refit;

                this.refitTableData = refitData.map(
                  (item: any, index: number) => ({
                    id: item.id || null,
                    s_no: index + 1,
                    lightship_displacement: item.lightship_displacement || '',
                    wght_change_prior_refit: item.wght_change_prior_refit || '',
                    net_wght_change_refit: item.net_wght_change_refit || '',
                    net_kg: item?.net_kg || '',
                  }),
                );

                // ✅ IMPORTANT: sync row count
                this.totalRowsRefit = this.refitTableData.length || 1;
                this.totalRowsRefitInEditMode = this.totalRowsRefit;

                // ✅ Ensure table respects count
                this.updateRefitTableRows(this.totalRowsRefit);
              }

              this.cdr.detectChanges();
          }
        },
        error: (err) => {
          console.error(err);
          this.toastService.showError('Failed to load data.');
        },
      });
  }

  validateForm(): boolean {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.toastService.showError(
        'Please fill all required fields correctly marked as * .',
      );
      return false;
    }
    return true;
  }

  // -------------------------------- HELPER FUNCTION TO CHECK WHETHER THE ROW DATA ARE EMPTY OR NOT ---------------------------------
  isOPSRowsEmpty(item: any): boolean {
    return !(
      item?.lightship_displacement ||
      item?.ref_load_condition ||
      item?.disp_c ||
      item?.disp_d ||
      item?.net_diff ||
      item?.corrected_disp ||
      item?.net_increase ||
      item?.percentage_increase ||
      item?.net_weight_add ||
      item?.net_kg_add
    );
  }

  isRefitRowEmpty(item: any): boolean {
    return !(
      item?.lightship_displacement ||
      item?.wght_change_prior_refit ||
      item?.net_wght_change_refit ||
      item?.net_kg
    );
  }

  uploadReferenceDocument(file: File, recordId: string) {
    const formData = new FormData();

    formData.append('resource', 'ship-weight-management');
    formData.append('record_id', recordId);
    formData.append('field_name', 'ref_auth');
    formData.append('file', file);

    return this.apiService.post(Apiendpoints.DOCUMENT_UPLOAD, formData);
  }

  private validateDraftForm(): boolean {
    const requiredFields = ['ship'];

    const fieldLabels: Record<string, string> = {
      ship: 'Ship',
      command: 'Command',
      class_of_ship: 'Class of Ship',
    };

    const missingFields: string[] = [];

    requiredFields.forEach((field) => {
      const control = this.form.get(field);

      if (!control?.value) {
        control?.markAsTouched();
        control?.setErrors({ required: true });
        missingFields.push(fieldLabels[field] || field);
      }
    });

    if (missingFields.length > 0) {
      this.toastService.showError(
        `Please fill at least the following field(s) to save as draft: ${missingFields.join(', ')}`,
      );
      return false;
    }

    return true;
  }
  /* ------------------------------- SAVE --------------------------------------- */
  async handleSave(draftStatus: 'draft' | 'save') {
    if (draftStatus === 'save' && !this.validateForm()) {
      return;
    }
    if (draftStatus === 'draft' && !this.validateDraftForm()) {
      return;
    }
    if (draftStatus === 'save') {
      this.saveLoading = true;
    } else {
      this.draftLoading = true;
    }

    const formatOPSTableData = this.opsTableData
      .filter((item: any) => !this.isOPSRowsEmpty(item))
      .map((item: any, index: number) => ({
        ...item,
        id: item?.id || null,
        s_no: index + 1,
      }));
    const formatRefitTableData = this.refitTableData
      .filter((item: any) => !this.isRefitRowEmpty(item))
      .map((item: any, index: number) => ({
        ...item,
        id: item?.id || null,
        s_no: index + 1,
      }));

    const formValues = this.form.value;

    const payload: any = { draft_status: draftStatus, ...formValues };

    if (formValues.ship_status === 'ops') {
      payload.ship_weight_management_ops = formatOPSTableData;
    } else {
      payload.ship_weight_management_refit = formatRefitTableData;
      payload.refit = formValues.refit_status;
      payload.refit_recommencement_date = formValues.refit_date
        ? new Date(formValues.refit_date).toISOString().split('T')[0]
        : null;
      payload.ref_auth = formValues?.ref_auth?.id;
    }

    if (this.editMode && this.editDataDetails) {
      payload.id = this.editDataDetails.id;
    }

    this.apiService
      .post(Apiendpoints.SHIP_WEIGHT_MANAGEMENT, payload)
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
            res?.message || 'Ship weight management request saved successfully',
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
              this.router.navigate(['/afterAuth/ship-returns/hull-returns/returns/ship-weight-management']);
            }, 1000);
          }
        },
        error: () => {
          this.toastService.showError(
            'Failed to save Ship weight management data.',
          );
        },
      });
  }
}
