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
import { ToastComponent } from '../../../../ui/master-compat';
import { SelectComponent as NewSelectComponent } from '../../../../ui/select.component';
import { MasterService } from '../../../../services/master.service';
import { ApiService } from '../../../../api.service';
import { ToastService } from '../../../../services/toast.service';
import { Apiendpoints } from '../../../../ApiEndPoints';
import { CalenderComponent } from '../../../../ui/calender.component';
import { InputComponent } from '../../../../ui/input.component';
import { RadioGroupComponent } from '../../../../ui/radio-group/radio-group.component';
import { ParameterCardComponent } from '../../../../ui/parameter-card/parameter-card.component';
import { FileUploadComponent } from '../../../../ui/file-upload/file-upload.component';
import { TextareaComponent } from '../../../../ui/textarea';
import { ReusableDeleteDialogDynamicContentComponent as ReusableDeleteDialogDynamicContent } from '../../../../ui/master-compat';
import {
  ReusableInputTableComponent,
  ReusableTableColumn,
} from '../../../../ui/reusable-input-table/reusable-input-table.component';
import { finalize, Observable } from 'rxjs';
import { MonthYearCalendarComponent as YearPickerComponent } from '../../../../ui/month-year-calendar.component';
import { ReusableButtonComponent } from '../../../../ui/master-compat';
import { ApprovalWorkFlow } from '../../../../ui/approval-work-flow/approval-work-flow';

@Component({
  selector: 'app-bhs-add-form',
  templateUrl: './bhs-add-form.html',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormCardComponent,
    LucideAngularModule,
    LoadingButtonComponent,
    ToastComponent,
    NewSelectComponent,
    CalenderComponent,
    InputComponent,
    RadioGroupComponent,
    ParameterCardComponent,
    FileUploadComponent,
    TextareaComponent,
    ReusableDeleteDialogDynamicContent,
    ReusableInputTableComponent,
    YearPickerComponent,
    ReusableButtonComponent,
    ApprovalWorkFlow,
  ],
})
export class BhsAddFormComponent implements OnInit {
  editMode = false;
  viewMode = false;

  rowId!: string | null;
  editDataDetails: any = null;
  showApprovalWorkflowPopup = false;

  readonly draftIcon = Save;
  readonly saveIcon = SaveAllIcon;
  readonly restartIcon = RotateCcw;
  readonly deleteIcon = Trash;

  // -------------------------------------------------------------------------
  // BOAT REGISTRATION OPTIONS
  // -------------------------------------------------------------------------

  boatRegistrationOptions: any[] = [];

  BerAberOptions: any[] = [
    { label: 'BER', value: 'ber' },
    { label: 'ABER', value: 'aber' },
    { label: 'SAT', value: 'sat' },
  ];

  satUnsatOptions: any[] = [
    { label: 'SAT', value: 'sat' },
    { label: 'UNSAT', value: 'unsat' },
  ];

  shipOptions: any[] = [];
  boatOptions: any[] = [];

  files: Record<string, File | null> = {
    boardFormationAuthority: null,
    boardMember1: null,
    boardMember2: null,
    boardPresident: null,
  };

  form!: FormGroup;
  saveLoading = false;
  draftLoading = false;

  // -------------------------------------------------------------------------
  // TABLE CONFIGURATION
  // -------------------------------------------------------------------------

  tableRows = 1;
  tableDetailsData: any[] = [];
  selectedRow: any = null;
  selectedRowIndex: number | null = null;

  tableRowDeleteDialogOpen = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    // private masterService: MasterService,
    private apiService: ApiService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
  ) {}

  // =========================================================================
  // INIT
  // =========================================================================

  ngOnInit(): void {
    // Get route values FIRST
    const mode = this.route.snapshot.data['mode'];
    this.rowId = this.route.snapshot.paramMap.get('id');

    // Build form
    this.buildForm();

    // Set mode
    if (mode === 'view') {
      this.viewMode = true;
    } else if (mode === 'edit') {
      this.editMode = true;
    }

    // Listen for ship changes
    this.listenToShipChanges();

    // Listen for boat registration changes
    this.listenToBoatRegistrationChanges();

    // Load initial ships only for new record
    if (!this.rowId) {
      this.loadShips();
    }

    // Initialize table
    this.updateTableRows(this.tableRows);

    // Load edit data if ID exists
    if (this.rowId) {
      this.getEditDataByRowId(this.rowId);
    }
  }

  // =========================================================================
  // FORM SETUP
  // =========================================================================

  buildForm() {
    this.form = this.fb.group({
      ship_id: [''],
      bhs_reg_no: [''],

      // These fields are automatically populated from selected boat
      bhs_type_of_boat: [{ value: '', disabled: true }],
      bhs_engine_oem: [{ value: '', disabled: true }],
      bhs_boat_builder: [{ value: '', disabled: true }],
      bhs_built_year: [{ value: '', disabled: true }],
      bhs_date_of_supply: [{ value: '', disabled: true }],
      bhs_unit: [{ value: '', disabled: true }],
      bhs_date_reappropriation: [{ value: '', disabled: true }],
      bhs_sn_port: [{ value: '', disabled: true }],
      bhs_sn_stbd: [{ value: '', disabled: true }],
      bhs_sn_center: [{ value: '', disabled: true }],

      bhs_year_of_rendering: ['', Validators.required],
      bhs_ber_aber: ['', Validators.required],
      bhs_occ_of_rendering: ['', Validators.required],
      bhs_cond_of_hull: ['', Validators.required],
      bhs_cond_of_fittings: ['', Validators.required],
      bhs_cond_of_davit_lifting: ['', Validators.required],
      status_of_integrated_navigation: ['', Validators.required],

      // ------------ SPEED TRAILS -------------------
      max_speed_during_current_trails: [''],
      max_rpm_during_current_trails: [''],
      max_speed_during_pdi_speed_trails: [''],
      max_rpm_during_pdi_speed_trails: [''],
      remedial_action_taken: [''],

      // ------------ WEIGHING OF BOAT -------------------
      weighing_undertaken_on: [''],
      weighing_location: [''],
      observed_weight: [''],
      pdi_trial_weight: [''],
      weight_remedial_action_taken: [''],
      major_repairs_since_last_return: [''],
      remaining_hull_life_years: [''],
      due_date_change_of_collar: [null],
      imo_certificate_validity: [null],
      assessment_board_remarks: [''],
    });
  }

  // =========================================================================
  // SHIP CHANGE
  // =========================================================================

  listenToShipChanges() {
    this.form.get('ship_id')?.valueChanges.subscribe((shipId) => {
      if (!shipId) {
        this.boatRegistrationOptions = [];

        this.form.patchValue(
          {
            bhs_reg_no: '',
          },
          { emitEvent: false },
        );

        this.clearBoatDetails();
        return;
      }

      // Whenever ship changes, fetch boats/registration numbers
      this.loadBoatRegistrationDetails(shipId);
    });
  }

  // =========================================================================
  // BOAT REGISTRATION CHANGE
  // =========================================================================

  listenToBoatRegistrationChanges() {
    this.form.get('bhs_reg_no')?.valueChanges.subscribe((boatId) => {
      if (boatId) {
        this.setBoatDetails(boatId);
      } else {
        this.clearBoatDetails();
      }
    });
  }

  getUser(): any {
    try {
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  }

  // =========================================================================
  // LOAD SHIPS
  // =========================================================================

  loadShips() {
    const user = this.getUser();
    this.apiService.get(Apiendpoints.MASTER_SHIP).subscribe({
      next: (res: any) => {
        this.shipOptions = (res?.results || res?.data || []).map((item: any) => ({
          label: item.name,
          value: item.id,
        }));

        if (user?.ship_id && !this.shipOptions.some((s: any) => s.value === user.ship_id)) {
          this.shipOptions.unshift({
            label: user.ship_name || `Ship ${user.ship_id}`,
            value: user.ship_id,
          });
        }

        if (user?.ship_id && !this.rowId) {
          this.form.patchValue({ ship_id: user.ship_id });
        } else if (this.shipOptions.length === 1 && !this.rowId) {
          this.form.patchValue({ ship_id: this.shipOptions[0].value });
        }

        this.cdr.detectChanges();
      },

      error: (err) => {
        console.error('Error loading ships:', err);
        if (user?.ship_id) {
          this.shipOptions = [{ label: user.ship_name || 'INS KOLKATA', value: user.ship_id }];
          if (!this.rowId) {
            this.form.patchValue({ ship_id: user.ship_id });
          }
        }
        this.cdr.detectChanges();
      },
    });
  }

  // =========================================================================
  // LOAD BOAT REGISTRATION DETAILS BY SHIP
  // =========================================================================

  loadBoatRegistrationDetails(
    shipId: number | string,
    selectedBoatId?: number | string,
  ) {
    if (!shipId) {
      this.boatRegistrationOptions = [];
      return;
    }

    this.apiService.get(`${Apiendpoints.MASTER_BOAT_DETAILS}?ship_id=${shipId}`).subscribe({
      next: (res: any) => {
        const dataList = res?.results || res?.data || [];
        if (!Array.isArray(dataList) || dataList.length === 0) {
          this.boatRegistrationOptions = [{ label: 'No boat found for this selected ship', value: null, disabled: true }];
          return;
        }
        this.boatRegistrationOptions = dataList.map((item: any) => ({
          label: item.display_label || `${item.boat_oem || ''} — ${item.registration_no || ''}`,
          value: item.id,
          data: item,
        }));
        if (selectedBoatId) {
          this.setBoatDetails(selectedBoatId);
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading boat registration details:', err);
        this.boatRegistrationOptions = [];
        this.cdr.detectChanges();
      },
    });
  }

  // =========================================================================
  // SET BOAT DETAILS
  // =========================================================================

  setBoatDetails(boatId: number | string) {
    const selectedBoat = this.boatRegistrationOptions.find(
      (option) => String(option.value) === String(boatId),
    );

    if (!selectedBoat?.data) {
      return;
    }

    const data = selectedBoat.data;

    console.log('Selected boat details:', data);

    this.form.patchValue(
      {
        // API: type_of_boat
        bhs_type_of_boat: data.type_of_boat || '',

        // API: engine_oem
        bhs_engine_oem: data.engine_oem || '',

        // API: boat_builder
        bhs_boat_builder: data.boat_builder || '',

        // API: built_year
        bhs_built_year: data.built_year || '',

        // API: date_of_supply
        bhs_date_of_supply: data.date_of_supply || '',

        // API: unit_name
        bhs_unit: data.unit_name || '',

        // API: date_of_reappropriation
        bhs_date_reappropriation: data.date_of_reappropriation || '',

        // API: engine_serial_p
        bhs_sn_port: data.engine_serial_p || '',

        // API: engine_serial_s
        bhs_sn_stbd: data.engine_serial_s || '',

        // API: engine_serial_c
        bhs_sn_center: data.engine_serial_c || '',
      },
      {
        emitEvent: false,
      },
    );

    this.cdr.detectChanges();
  }

  // =========================================================================
  // CLEAR BOAT DETAILS
  // =========================================================================

  clearBoatDetails() {
    this.form.patchValue(
      {
        bhs_type_of_boat: '',
        bhs_engine_oem: '',
        bhs_boat_builder: '',
        bhs_built_year: '',
        bhs_date_of_supply: '',
        bhs_unit: '',
        bhs_date_reappropriation: '',
        bhs_sn_port: '',
        bhs_sn_stbd: '',
        bhs_sn_center: '',
      },
      {
        emitEvent: false,
      },
    );

    this.cdr.detectChanges();
  }

  // =========================================================================
  // GET BOATS
  // =========================================================================

  loadBoats() {
    this.apiService.get(Apiendpoints.BOATS).subscribe({
      next: (res: any) => {
        const dataList = res?.results || res?.data || [];
        this.boatOptions = dataList;
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        console.error('Error loading boats:', err);
      },
    });
  }

  // =========================================================================
  // TABLE COLUMNS
  // =========================================================================

  tableColumns: ReusableTableColumn[] = [
    {
      field: 's_no',
      header: 'Ser',
      width: '70px',
      align: 'center' as const,
    },
    {
      field: 'condition_engine',
      header: 'Condition of Engine',
      width: '110px',
      fieldType: 'drop-down',
      options: [
        { label: 'SAT', value: 'SAT' },
        { label: 'UNSAT', value: 'UNSAT' },
      ],
    },
    {
      field: 'total_running_hrs_since_last_return',
      header: 'Total Running HRS of Engine Run Since Last Return',
      template: 'inputTpl',
    },
    {
      field: 'major_routines_undertaken',
      header: 'Major Routines undertaken Since Last Return on Engine',
      template: 'inputTpl',
    },
    {
      field: 'access_remaining_engine_life',
      header: 'Assessed Remaining life of Engine - Years',
      template: 'inputTpl',
    },
  ];

  // =========================================================================
  // TABLE ROW CHANGES
  // =========================================================================

  onTableDetailsRowChanges(event: Event): void {
    let value = +(event.target as HTMLInputElement).value;
    if (!value || value < 1) value = 1;

    this.tableRows = Math.max(1, Math.min(99, value));

    this.updateTableRows(this.tableRows);
    this.cdr.detectChanges();
  }

  updateTableRows(count: number): void {
    const currentLength = this.tableDetailsData.length;

    if (count > currentLength) {
      for (let i = currentLength; i < count; i++) {
        this.tableDetailsData.push({
          s_no: i + 1,
          condition_engine: '',
          total_running_hrs_since_last_return: '',
          major_routines_undertaken: '',
          access_remaining_engine_life: '',
        });
      }
    } else if (count < currentLength) {
      this.tableDetailsData.splice(count);
    }
    this.tableDetailsData = [...this.tableDetailsData];
  }

  // =========================================================================
  // TABLE ACTION
  // =========================================================================

  handleTableAction(event: any) {
    console.log('Table action:', event);

    if (event.type === 'delete') {
      this.selectedRow = {
        ...event.row,
        table: event.table,
      };

      this.tableRowDeleteDialogOpen = true;

      this.selectedRowIndex = event.index;
    }
  }

  closeDeleteDialog() {
    this.tableRowDeleteDialogOpen = false;
  }

  // =========================================================================
  // CONFIRM DELETE
  // =========================================================================

  confirmDelete() {
    if (this.selectedRowIndex !== null) {
      this.tableDetailsData.splice(this.selectedRowIndex, 1);
    }

    this.tableRowDeleteDialogOpen = false;
  }

  handleOpsTableChange(index: number, field: string, value: string) {
    if (this.viewMode) return;

    this.tableDetailsData[index][field] = value;
  }

  // =========================================================================
  // EDIT MODE
  // =========================================================================

  getEditDataByRowId(rowId: string) {
    this.apiService
      .get(`${Apiendpoints.BOAT_HISTORY_SHEET}${rowId}/`)
      .subscribe({
        next: (res: any) => {
          if (!res?.data) return;

          const data = res.data;

          this.editDataDetails = data;

          console.log('Boat History Sheet edit data:', data);

          // ---------------------------------------------------------------
          // PATCH MAIN FORM
          // ---------------------------------------------------------------

          this.form.patchValue(
            {
              ship_id: data.ship?.id || data.ship || '',

              // This should be boat ID
              bhs_reg_no: data.bhs_reg_no || '',

              bhs_year_of_rendering: data.bhs_year_of_rendering,

              bhs_ber_aber: data.bhs_ber_aber,

              bhs_occ_of_rendering: data.bhs_occ_of_rendering,

              bhs_cond_of_hull: data.bhs_cond_of_hull,

              bhs_cond_of_fittings: data.bhs_cond_of_fittings,

              bhs_cond_of_davit_lifting: data.bhs_cond_of_davit_lifting,

              status_of_integrated_navigation:
                data.status_of_integrated_navigation,

              max_speed_during_current_trails:
                data.max_speed_during_current_trails,

              max_rpm_during_current_trails: data.max_rpm_during_current_trails,

              max_speed_during_pdi_speed_trails:
                data.max_speed_during_pdi_speed_trails,

              max_rpm_during_pdi_speed_trails:
                data.max_rpm_during_pdi_speed_trails,

              remedial_action_taken: data.remedial_action_taken,

              weighing_undertaken_on: data.weighing_undertaken_on,

              weighing_location: data.weighing_location,

              observed_weight: data.observed_weight,

              pdi_trial_weight: data.pdi_trial_weight,

              weight_remedial_action_taken: data.weight_remedial_action_taken,

              major_repairs_since_last_return:
                data.major_repairs_since_last_return,

              remaining_hull_life_years: data.remaining_hull_life_years,

              due_date_change_of_collar: data.due_date_change_of_collar,

              imo_certificate_validity: data.imo_certificate_validity,

              assessment_board_remarks: data.assessment_board_remarks,
            },
            {
              // IMPORTANT:
              // Don't trigger ship_id -> API here.
              emitEvent: false,
            },
          );

          // ---------------------------------------------------------------
          // LOAD BOATS FOR THE SELECTED SHIP
          // ---------------------------------------------------------------

          const shipId = data.ship?.id || data.ship || '';

          const selectedBoatId = data.bhs_reg_no?.id || data.bhs_reg_no || '';

          if (shipId) {
            this.loadBoatRegistrationDetails(shipId, selectedBoatId);
          }

          // ---------------------------------------------------------------
          // TABLE DATA
          // ---------------------------------------------------------------

          this.tableDetailsData = (data.engine_table_data || []).map(
            (item: any, index: number) => ({
              id: item.id,

              s_no: index + 1,

              condition_engine: item.condition_engine || '',

              total_running_hrs_since_last_return:
                item.total_running_hrs_since_last_return || '',

              major_routines_undertaken: item.major_routines_undertaken || '',

              access_remaining_engine_life:
                item.access_remaining_engine_life || '',
            }),
          );

          this.tableRows = this.tableDetailsData.length || 1;

          if (this.tableDetailsData.length === 0) {
            this.updateTableRows(1);
          }

          // ---------------------------------------------------------------
          // VIEW MODE
          // ---------------------------------------------------------------

          if (this.viewMode) {
            this.form.disable();
          }

          this.cdr.detectChanges();
        },

        error: (err) => {
          console.error('Failed to load Boat History Sheet:', err);

          this.toastService.showError('Failed to load Boat History Sheet.');
        },
      });
  }

  // =========================================================================
  // FILE CHANGE
  // =========================================================================

  onFileChange(
    file: File,
    type:
      | 'boardFormationAuthority'
      | 'boardMember1'
      | 'boardMember2'
      | 'boardPresident',
  ) {
    this.files[type] = file;
  }

  // =========================================================================
  // CLEAR
  // =========================================================================

  clear() {
    // Reset form
    this.form.reset();

    // Explicitly reset disabled boat fields
    this.form.patchValue(
      {
        bhs_type_of_boat: '',
        bhs_engine_oem: '',
        bhs_boat_builder: '',
        bhs_built_year: '',
        bhs_date_of_supply: '',
        bhs_unit: '',
        bhs_date_reappropriation: '',
        bhs_sn_port: '',
        bhs_sn_stbd: '',
        bhs_sn_center: '',
      },
      {
        emitEvent: false,
      },
    );

    // Reset dropdown data
    this.boatRegistrationOptions = [];

    // Reset table
    this.tableRows = 1;
    this.tableDetailsData = [];

    this.updateTableRows(this.tableRows);

    // Reset files
    this.files = {
      boardFormationAuthority: null,
      boardMember1: null,
      boardMember2: null,
      boardPresident: null,
    };

    // Reset selection
    this.selectedRow = null;
    this.selectedRowIndex = null;
    this.tableRowDeleteDialogOpen = false;

    // Reset loaders
    this.saveLoading = false;
    this.draftLoading = false;

    this.cdr.detectChanges();
  }

  // =========================================================================
  // APPROVAL WORKFLOW
  // =========================================================================

  onApprovalPopupChange(open: boolean): void {
    this.showApprovalWorkflowPopup = open;

    this.cdr.detectChanges();
  }

  openApprovalWorkflow(): void {
    this.showApprovalWorkflowPopup = true;

    this.cdr.detectChanges();
  }

  // =========================================================================
  // BACK
  // =========================================================================

  handleBack() {
    this.router.navigate(['/afterAuth/ship-returns/hull-returns/returns/boat-history-sheet']);
  }

  // =========================================================================
  // VALIDATE FORM
  // =========================================================================

  validateForm(): boolean {
    if (this.form.invalid) {
      this.form.markAllAsTouched();

      this.toastService.showError('Please fill all required fields correctly.');

      return false;
    }

    return true;
  }

  // =========================================================================
  // UPLOAD DOCUMENT
  // =========================================================================

  uploadReferenceDocument(file: File, recordId: number, type: string) {
    const formData = new FormData();

    formData.append('file', file);
    formData.append('record_id', recordId.toString());
    formData.append('file_type', type);

    return this.apiService.post(Apiendpoints.DOCUMENT_UPLOAD, formData);
  }

  // =========================================================================
  // TABLE EMPTY CHECK
  // =========================================================================

  isTableRowsEmpty(item: any): boolean {
    return !(
      item?.condition_engine ||
      item?.total_running_hrs_since_last_return ||
      item?.major_routines_undertaken ||
      item?.access_remaining_engine_life
    );
  }

  // =========================================================================
  // UPLOAD ALL FILES
  // =========================================================================

  uploadAllFiles(recordId: number): Observable<any>[] {
    const uploads: Observable<any>[] = [];

    Object.entries(this.files).forEach(([key, file]) => {
      if (file) {
        uploads.push(this.uploadReferenceDocument(file, recordId, key));
      }
    });

    return uploads;
  }

  // =========================================================================
  // SAVE
  // =========================================================================

  async handleSave(draftStatus: 'draft' | 'save') {
    if (draftStatus === 'save' && !this.validateForm()) {
      return;
    }

    if (draftStatus === 'save') {
      this.saveLoading = true;
    } else {
      this.draftLoading = true;
    }

    // ---------------------------------------------------------------
    // TABLE DATA
    // ---------------------------------------------------------------

    const formatedTableData = this.tableDetailsData
      .filter((item: any) => !this.isTableRowsEmpty(item))
      .map((item: any, index: number) => ({
        ...item,
        id: item?.id || null,
        s_no: index + 1,
      }));

    // ---------------------------------------------------------------
    // FORM VALUES
    // ---------------------------------------------------------------

    const formValues = this.form.value;

    const payload: any = {
      draft_status: draftStatus,
      ...formValues,
      engine_table_data: formatedTableData,
    };

    // ---------------------------------------------------------------
    // EDIT
    // ---------------------------------------------------------------

    if (this.editMode) {
      payload.id = this.editDataDetails.id;
    }

    // ---------------------------------------------------------------
    // SAVE API
    // ---------------------------------------------------------------

    this.apiService
      .post(Apiendpoints.BOAT_HISTORY_SHEET, payload)
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
          // -------------------------------------------------------------
          // FILE UPLOAD
          // -------------------------------------------------------------

          const recordId = res?.data?.id;

          if (recordId) {
            const uploads = this.uploadAllFiles(recordId);

            if (uploads.length) {
              uploads.forEach((obs) => {
                obs.subscribe({
                  next: () => {
                    this.toastService.showSuccess('File uploaded successfully');
                  },

                  error: () => {
                    this.toastService.showError('File upload failed');
                  },
                });
              });
            }
          }

          // -------------------------------------------------------------
          // SUCCESS
          // -------------------------------------------------------------

          this.toastService.showSuccess(
            res?.message || 'Boat history sheet request saved successfully',
          );

          // -------------------------------------------------------------
          // APPROVAL WORKFLOW
          // -------------------------------------------------------------

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
              this.router.navigate(['/afterAuth/ship-returns/hull-returns/returns/boat-history-sheet']);
            }, 1000);
          }
        },

        error: (err) => {
          console.error('Boat History Sheet save error:', err);

          this.toastService.showError(
            'Failed to save Boat history sheet data.',
          );
        },
      });
  }
}
