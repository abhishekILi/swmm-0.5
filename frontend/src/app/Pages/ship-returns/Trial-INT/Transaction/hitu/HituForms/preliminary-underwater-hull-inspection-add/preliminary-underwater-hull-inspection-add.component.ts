import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component } from '@angular/core';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { FormCardComponent } from '../../../../ui/form-card/form-card.component';
import {
  LucideRotateCcw as RotateCcw,
  LucideSave as Save,
  LucideSaveAll as SaveAllIcon,
} from '@lucide/angular';
import { LoadingButtonComponent } from '../../../../ui/loading-button.component';
import { ToastComponent } from '../../../../ui/toast/toast.component';
import { SelectComponent } from '../../../../ui/select.component';
import { ApiService } from '../../../../api.service';
import { ToastService } from '../../../../services/toast.service';
import { Apiendpoints } from '../../../../ApiEndPoints';
import { CalenderComponent } from '../../../../ui/calender.component';
import { ParameterCardComponent } from '../../../../ui/parameter-card/parameter-card.component';
import { MonthYearCalendarComponent } from '../../../../ui/month-year-calendar.component';
import { InputComponent } from '../../../../ui/input.component';
import { YearCalendarComponent } from '../../../../ui/year-calender/year-calendar.component';
import { FileUploadComponent } from '../../../../ui/file-upload/file-upload.component';
import { SelectWithSearchComponent } from '../../../../ui/select-with-search/select-with-search-box.component';

@Component({
  selector: 'preliminary-underwater-hull-inspection-add',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormCardComponent,
    LoadingButtonComponent,
    ToastComponent,
    SelectComponent,
    CalenderComponent,
    ParameterCardComponent,
    MonthYearCalendarComponent,
    InputComponent,
    YearCalendarComponent,
    FileUploadComponent,
    SelectWithSearchComponent,
  ],
  templateUrl: './preliminary-underwater-hull-inspection-add.component.html',
})
export class PreliminaryUnderwaterHullInspectionAdd {
  editMode = false;
  rowId!: string | null;
  editDataDetails: any = null;

  readonly draftIcon = Save;
  readonly saveIcon = SaveAllIcon;
  readonly restartIcon = RotateCcw;

  form!: FormGroup;
  loading = false;

  classOfShipOptions: any[] = [];
  shipOptions: any[] = [];

  dockingVersionOptions = [
    { label: 'Ver I', value: 'Ver I' },
    { label: 'Ver II', value: 'Ver II' },
    { label: 'NHQ/MoD approved', value: 'NHQ/MoD approved' },
    { label: 'Others', value: 'Others' },
  ];

  natureOfDockingOptions = [
    { label: 'Ops', value: 'Ops' },
    { label: 'Emergency', value: 'Emergency' },
    { label: 'AMP', value: 'AMP' },
    { label: 'EAMP', value: 'EAMP' },
    { label: 'SR', value: 'SR' },
    { label: 'NR', value: 'NR' },
    { label: 'MR', value: 'MR' },
    { label: 'Others', value: 'Others' },
  ];

  lastRefitOptions = [
    { label: 'AMP', value: 'AMP' },
    { label: 'EAMP', value: 'EAMP' },
    { label: 'SR', value: 'SR' },
    { label: 'NR', value: 'NR' },
    { label: 'MR', value: 'MR' },
    { label: 'Others', value: 'Others' },
  ];

  // ----------------------------------------------------------------------------------------------------------------
  opsOptions = [
    { label: 'Ops', value: 'Ops' },
    { label: 'Non-ops', value: 'Non-ops' },
  ];
  opsNaOptions = [
    { label: 'NA', value: 'NA' },
    { label: 'Ops', value: 'Ops' },
    { label: 'Non-ops', value: 'Non-ops' },
  ];

  LubricatiedOptions = [
    { label: 'Lubricated', value: 'Lubricated' },
    { label: 'Not Lubricated', value: 'Not Lubricated' },
  ];

  noiseObserved = [
    { label: 'Nil', value: 'Nil' },
    { label: 'Noise Observed', value: 'Noise Observed' },
  ];

  securedNotSecured = [
    { label: 'Secured', value: 'Secured' },
    { label: 'Not Secured', value: 'Not Secured' },
  ];

  OilLevelGauge = [
    { label: '40-100% filled', value: '40-100% filled' },
    {
      label: 'Less than 40% filled Empty',
      value: 'Less than 40% filled Empty',
    },
    { label: 'Empty', value: 'Empty' },
  ];

  SatUnsatOptions = [
    { label: 'SAT', value: 'SAT' },
    { label: 'UNSAT', value: 'UNSAT' },
  ];

  SatUnsatNAOptions = [
    { label: 'NA', value: 'NA' },
    { label: 'SAT', value: 'SAT' },
    { label: 'UNSAT', value: 'UNSAT' },
  ];

  fillingDrainPlugs = [
    { label: 'Charged', value: 'Charged' },
    { label: 'Painted', value: 'Painted' },
    { label: 'Choked', value: 'Choked' },
    { label: 'Missing', value: 'Missing' },
    { label: 'Others', value: 'Others' },
  ];

  ObservationsOptions = [
    { label: 'No Observation', value: 'NoObservation' },
    { label: 'Observation', value: 'Observation' },
  ];

  ObservationsNilOptions = [
    { label: 'Nil', value: 'Nil' },
    { label: 'Observation', value: 'Observation' },
  ];
  greasingOptions = [
    { label: 'Greased', value: 'Greased' },
    { label: 'Not Greased', value: 'Not Greased' },
  ];

  overallRemarksOptions = [
    { label: 'SAT', value: 'SAT' },
    { label: 'UNSAT', value: 'UNSAT' },
    { label: 'SAT with observations', value: 'SAT with observations' },
  ];

  overallRemarksNaOptions = [
    { label: 'NA', value: 'NA' },
    { label: 'SAT', value: 'SAT' },
    { label: 'UNSAT', value: 'UNSAT' },
    { label: 'SAT with observations', value: 'SAT with observations' },
  ];

  yesNoOptions = [
    { label: 'Yes', value: 'Yes' },
    { label: 'No', value: 'No' },
  ];

  gearBoxOptions = [
    { label: 'OC300', value: 'OC300' },
    { label: 'SS320', value: 'SS320' },
    { label: 'Others', value: 'Others' },
  ];

  montlyQuarterlyOption = [
    { label: 'Monthly', value: 'Monthly' },
    { label: 'Quarterly', value: 'Quarterly' },
  ];

  montlyQuarterlyNilOption = [
    { label: 'Monthly', value: 'Monthly' },
    { label: 'Quarterly', value: 'Quarterly' },
    { label: 'Nil', value: 'Nil' },
  ];

  spmCheckOptions = [
    { label: 'Green', value: 'Green' },
    { label: 'Yellow', value: 'Yellow' },
    { label: 'Red', value: 'Red' },
  ];

  constructor(
    private cdr: ChangeDetectorRef,
    private fb: FormBuilder,
    private router: Router,
    private apiService: ApiService,
    private toastService: ToastService,
  ) {}

  loadClasses() {
    this.apiService.getDropdownData('master/ship-classes/', { labelKey: 'name', valueKey: 'id' }).subscribe((res) => {
      this.classOfShipOptions = res || [];
      this.cdr.detectChanges();
    });
  }
  listenToClassChanges() {
    this.form.get('classOfShip')?.valueChanges.subscribe((classId) => {
      if (classId) {
        this.loadShips(classId);
        this.form.get('ship')?.reset();
      } else {
        this.shipOptions = [];
        this.form.get('ship')?.reset();
      }
    });
  }

  loadShips(id: number) {
    this.apiService.getDropdownData('master/ships/', { labelKey: 'name', valueKey: 'id' }).subscribe((res) => {
      this.shipOptions = res || [];
    });
  }

  showFillingDrainRemarkInput = false;
  showVisualInspectionInput = false;

  // Remarks feilds show and hide booleans ---------------------
  showElectricalHygieneInput = false;
  showOpsSwitchInput = false;
  showIndicatorInput = false;
  showRustObservationFields = false;

  ngOnInit(): void {
    this.buildForm();

    this.setupConditionalLogic();

    if (this.rowId) {
      this.editMode = true;
      this.getEditDataByRowId(this.rowId);
    }
  }

  handleFile(file: File | null) {
    console.log('Selected file:', file);
  }

  buildForm() {
    this.form = this.fb.group({
      classOfShip: ['', Validators.required],
      ship: ['', Validators.required],
      date_of_inspection: [''],
      authority: [''],
      hitu_inspector: [''],

      // 2a.
      docking_version: [''],
      docking_version_remark: [''],

      // 2b
      docking_nature: [''],
      docking_nature_remark: [''],

      // 2c
      last_refit_type: [''],
      last_refit_year: [''],
      last_refit_remark: [''],

      // 1,
      //

      type: [''],
      make: [''],
      year_of_manufacture: [''],

      // 4a
      electrical_hygiene: [''],
      electrical_hygiene_remark: [''],
      electrical_hygiene_value: [''],
      // 4b
      ops_status_switches: [''],
      ops_status_switches_remark: [''],
      ops_status_switches_value: [''],
      //4c
      ops_status_of_indicator: [''],
      ops_status_of_indicator_remark: [''],
      ops_status_of_indicator_value: [''],

      // 8
      condition_of_foundation: [''],
      condition_of_foundation_remark: [''],
      Corrosion: [''],
      Pitting: [''],
      Preserved: [''],
      Others: [''],

      // 9
      condition_brake_band: [''],
      condition_brake_band_remark: [''],
      condition_brake_band_value: [''],

      // 10
      insulation_of_motor_cable_value: [''],
      insulation_of_motor_cable_remark: [''],

      // 11
      greasing_check: [''],
      greasing_remark: [''],

      // 12
      greasing_points: [''],
      greasing_points_remark: [''],
      greasing_points_value: [''],

      // 13
      drive: [''],
      drive_remark: [''],
      drive_value: [''],

      // 14
      condition_capston_drum: [''],
      condition_capston_drum_remark: [''],
      condition_capston_drum_value: [''],

      // 15A
      low_speed: [0],
      low_speed_remark: [''],
      low_speed_value: [''],

      // 15B
      rated_speed: [0],
      rated_speed_remark: [''],
      rated_speed_value: [''],

      // 15C
      max_speed: [0],
      max_speed_remark: [''],
      max_speed_value: [''],

      // 16
      oil_level: [0],
      oil_level_remark: [{ value: '', disabled: true }],

      oil_gear_box: [''],
      oil_gear_box_value: [''],
      oil_gear_box_remark: [''],

      // 18
      lastOilChangeDate: [''],
      nextDueOilChangeDate: [''],
      lastOilChangeDate_marks: [''],

      // 19
      water_content_value: [''],
      Viscosity_value: [''],
      base_number_value: [''],
      acid_number_value: [''],
      metal_traces_value: [''],

      // 20
      starting_current_reference: [''],
      starting_current_measured: [''],
      starting_current_remarks: [''],

      // 21
      running_current_reference: [''],
      running_current_measured: [''],
      running_current_remarks: [''],

      // 22
      log_book_reference: [''],
      log_book_measured: [''],
      log_book_remakrs: [''],

      // 23
      periodicity_reference: [''],
      periodicity_measured: [''],
      periodicity_remarks: [''],

      // 24
      spm_measured: [''],
      spm_remarks: [''],
      // 25
      other_observation: [''],
      // 26
      overall_remark: [''],
    });
  }

  setupConditionalLogic() {
    // ---------------- 4A Electrical Hygiene ----------------
    this.form.get('electrical_hygiene')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('electrical_hygiene_remark');
      const valueControl = this.form.get('electrical_hygiene_value');

      this.showElectricalHygieneInput = false;
      valueControl?.reset();

      if (value === 'SAT') {
        remarkControl?.setValue('SAT');
      } else if (value === 'SAT with observation' || value === 'UNSAT') {
        this.showElectricalHygieneInput = true;
        remarkControl?.setValue(null);
      } else {
        remarkControl?.setValue(null);
      }
    });

    // ---------------- 4B Ops Status of Switches ----------------
    this.form.get('ops_status_switches')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('ops_status_switches_remark');
      const valueControl = this.form.get('ops_status_switches_value');

      this.showOpsSwitchInput = false;
      valueControl?.reset();

      if (value === 'Ops') {
        remarkControl?.setValue('SAT');
      } else if (value === 'Non-ops') {
        this.showOpsSwitchInput = true;
        remarkControl?.setValue(null);
      } else {
        remarkControl?.setValue(null);
      }
    });

    // ---------------- 4C Ops Status of Indicators ----------------
    this.form
      .get('ops_status_of_indicator')
      ?.valueChanges.subscribe((value) => {
        const remarkControl = this.form.get('ops_status_of_indicator_remark');
        const valueControl = this.form.get('ops_status_of_indicator_value');

        this.showIndicatorInput = false;
        valueControl?.reset();

        if (value === 'NA') {
          remarkControl?.setValue('NA');
        } else if (value === 'Ops') {
          remarkControl?.setValue('SAT');
        } else if (value === 'Non-ops') {
          this.showIndicatorInput = true;
          remarkControl?.setValue(null);
        } else {
          remarkControl?.setValue(null);
        }
      });

    // ---------------- PARAMETER 8 - Condition of Foundations ----------------
    this.form
      .get('condition_of_foundation')
      ?.valueChanges.subscribe((value) => {
        const remarkControl = this.form.get('condition_of_foundation_remark');

        this.showRustObservationFields = false;

        // Reset all observation fields
        this.form.get('Corrosion')?.reset();
        this.form.get('Pitting')?.reset();
        this.form.get('Preserved')?.reset();
        this.form.get('Others')?.reset();

        if (value === 'No Observation') {
          remarkControl?.setValue('SAT');
        } else if (value === 'Observation') {
          this.showRustObservationFields = true;
          remarkControl?.setValue(null);
        } else {
          remarkControl?.setValue(null);
        }
      });
  }

  checkSpeed() {
    const slow = this.form.get('slow_speed')?.value;
    const fast = this.form.get('fast_speed')?.value;

    const MIN = 2; // Replace with actual values
    const MAX = 5;

    const remark = this.form.get('speed_remark');

    const slowValid = slow >= MIN && slow <= MAX;
    const fastValid = fast >= MIN && fast <= MAX;

    if (slowValid && fastValid) {
      remark?.setValue('SAT');
      remark?.disable();
    } else {
      remark?.setValue('UNSAT');
      remark?.enable(); // allow remarks input
    }
  }

  /* ----------------------------- EDIT MODE ----------------------------------- */

  getEditDataByRowId(rowId: string) {
    this.apiService.get(`hitumodule/preliminary-underwater-hull-inspection/${rowId}`).subscribe({
      next: (res: any) => {
        if (res?.data) {
          this.editDataDetails = res.data;
          this.form.patchValue({
            command: this.editDataDetails?.ship?.command?.id,
            class_of_ship: this.editDataDetails?.ship?.classofship?.id,
          });
        }
      },
      error: (err) => {
        console.error('Error fetching BER certificate data:', err);
        this.toastService.showError('Failed to load BER certificate details.');
      },
    });
  }

  validateForm(): boolean {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.toastService.showError('Please fill all required fields correctly.');
      return false;
    }
    return true;
  }

  /* ------------------------------- SAVE --------------------------------------- */

  async handleSave(draftStatus: 'draft' | 'save') {
    if (draftStatus === 'save' && !this.validateForm()) {
      return;
    }
    this.loading = true;

    const value = this.form.value;

    const payload: any = {
      ship: value.ship,
      class_of_ship: value.class_of_ship.toLowerCase(),
      draft_status: draftStatus,
    };

    if (this.editMode) {
      payload.id = this.editDataDetails.id;
    }
    this.apiService.post(Apiendpoints.WATER_TIGHT_DOOR, payload).subscribe({
      next: (res: any) => {
        this.toastService.showSuccess(
          res?.message || 'Emergency escape hatch request saved successfully',
        );

        setTimeout(() => {
          this.router.navigate(['/app/ship/ber-certificate']);
        }, 1000);
      },
      error: (err) => {
        console.error('Error in adding Emergency escape hatch request', err);
        this.toastService.showError(
          'Failed to save Emergency escape hatch request data.',
        );
      },
      complete: () => {
        this.loading = false;
      },
    });

    this.router.navigate(['/app/ship/ship-weight-management']);
  }
}
