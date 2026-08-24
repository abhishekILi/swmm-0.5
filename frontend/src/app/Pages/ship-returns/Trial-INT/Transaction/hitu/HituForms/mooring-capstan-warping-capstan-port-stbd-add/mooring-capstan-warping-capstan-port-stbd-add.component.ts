import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component } from '@angular/core';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { FormCardComponent } from '../../../../ui/form-card/form-card.component';
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
import {
  FileUploadComponent,
  UploadedFileItem,
} from '../../../../ui/file-upload/file-upload.component';
import { FormApiService } from '../../../../angulerFromconverting/form-api.service';
import { resolveTrialQueryParam } from '../../../../trial-route-prefill';
import { FileUrlUtil } from '../../../../file-url-util';
import { ApprovalWorkFlow } from '../../../../ui/approval-work-flow/approval-work-flow';

@Component({
  selector: 'app-mooring-capstan-warping-capstan-port-stbd-add',
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
    ApprovalWorkFlow,
    FileUploadComponent,
  ],
  templateUrl: './mooring-capstan-warping-capstan-port-stbd-add.component.html',
})
export class MooringCapstanWarpingCapstan {
  editMode = false;
  rowId!: string | null;
  editDataDetails: any = null;

  draftLoading = false;
  saveLoading = false;
  submitLoading = false;

  draftIcon = 'file-text';
  saveIcon = 'save';
  submitIcon = 'check-check';

  readonly restartIcon = 'rotate-ccw';

  form!: FormGroup;
  loading = false;
  showApprovalWorkflowPopup = false;
  isSubmitTime = false;

  uploadedAuthorityFiles: UploadedFileItem[] = [];

  commandOptions: any[] = [];
  classOfShipOptions: any[] = [];
  shipOptions: any[] = [];
  placesOptions: any[] = [];

  // -------------------- EQUIPMENT HEADER TABS --------------------
  workflowTrialId: string | undefined = undefined;
  eqpList: any[] = [];
  activeTab: any = null;

  get headerEquipmentTabs(): any[] {
    if (this.eqpList.length) return this.eqpList;

    const contextEquipments = this.formApiService?.context?.equipment_details;
    if (Array.isArray(contextEquipments) && contextEquipments.length) {
      return contextEquipments;
    }

    return this.formApiService?.currentEquipmentNomenclature
      ? [this.formApiService.currentEquipmentNomenclature]
      : [];
  }

  get activeHeaderEquipment(): any {
    return (
      this.activeTab ||
      this.formApiService?.currentEquipmentNomenclature ||
      null
    );
  }

  get activeEquipmentId(): number | null {
    return (
      this.activeHeaderEquipment?.equipment_id ??
      this.activeHeaderEquipment?.id ??
      null
    );
  }

  // -------------------- SAVE / SUBMIT BUTTON ENABLE CONDITION --------------------
  get canEdit(): boolean {
    const canEdit = !!this.formApiService?.context?.workflow_rights?.can_edit;
    console.log('[Mooring Capstan] can_edit condition evaluated as:', canEdit);
    return canEdit;
  }

  occasionOptions = [
    { label: 'Pre Refit Trials', value: 'pre_refit_trials' },
    { label: 'End of Refit Trials', value: 'end_of_refit_trials' },
    { label: 'Surprice Checks', value: 'surprice_checks' },
  ];

  capstanOptions = [
    { label: 'MOORING CAPSTAN', value: 'MOORING CAPSTAN' },
    { label: 'WARPING CAPSTAN', value: 'WARPING CAPSTAN' },
  ];
  // PORT/ STBD
  stbdOptions = [
    { label: 'PORT', value: 'PORT' },
    { label: 'STBD', value: 'STBD' },
  ];

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
    { label: 'Less than 40% filled', value: 'Less than 40% filled' },
    { label: 'Empty', value: 'Empty' },
  ];

  SatUnsatOptions = [
    { label: 'SAT', value: 'SAT' },
    { label: 'UNSAT', value: 'UNSAT' },
  ];

  NilSatUnsatOptions = [
    { label: 'NIL', value: 'NIL' },
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
    { label: 'NA', value: 'NA' },
    { label: 'Green', value: 'Green' },
    { label: 'Yellow', value: 'Yellow' },
    { label: 'Red', value: 'Red' },
  ];

  //   0-20 dbm (Green/Yellow/ Red)
  // (0-20/ 20-35/ >35)

  constructor(
    private cdr: ChangeDetectorRef,
    private fb: FormBuilder,
    private router: Router,
    private apiService: ApiService,
    private toastService: ToastService,
    private route: ActivatedRoute,
    private toast: ToastService,
    public formApiService: FormApiService,
  ) {}

  showFillingDrainRemarkInput = false;
  showVisualInspectionInput = false;

  // Remarks feilds show and hide booleans ---------------------
  showElectricalHygieneInput = false;
  showOpsSwitchInput = false;
  showIndicatorInput = false;
  showRustObservationFields = false;
  showBrakeBandInput = false;
  showGreasingPointsInput = false;
  showDriveInput = false;
  showCapstanDrumInput = false;
  showCapstanDrumObservationInput = false;

  SatWithObsUnsatOptions = [
    { label: 'SAT with observation', value: 'SAT with observation' },
    { label: 'UNSAT', value: 'UNSAT' },
  ];

  ngOnInit(): void {
    this.buildForm();
    this.loadPlaceOfConductTrail();

    this.setupConditionalLogic();
    this.loadTrialPrefillFromQuery();

    if (this.rowId) {
      this.editMode = true;
      this.getEditDataByRowId(this.rowId);
    }

    // initial console check for the button-enable condition
    console.log('[Mooring Capstan] ngOnInit - can_edit:', this.canEdit);
  }

  buildForm() {
    this.form = this.fb.group({
      capstan: [''],
      port: [''],
      ship: [{ value: '', disabled: true }],
      class_of_ship: [''],
      date_of_inspection: [''],
      place_of_conduct_trail: ['', Validators.required],
      occasion_of_conduct_trail: ['', Validators.required],

      date_of_conduct_trail: [''],
      authority: ['', Validators.required],
      authority_date: ['', Validators.required],
      authority_doc: [''],

      // 1,2 & 3
      type: [''],
      manufacturer_name: [{ value: '', disabled: true }],
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
      condition_capston_drum_observation: [''],

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
      oil_level_remark: [''],

      oil_gear_box: [''],
      oil_gear_box_value: [''],
      oil_gear_box_remark: [''],

      // 18
      lastOilChangeDate: [''],
      nextDueOilChangeDate: [''],
      lastOilChangeDate_marks: [''],
      lastDateOfOilChange: [''],

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

  setOilChangeRemark() {
    const lastDate = this.form.get('lastDateOfOilChange')?.value;
    const monthYear = this.form.get('lastOilChangeDate')?.value;
    const remarkControl = this.form.get('lastOilChangeDate_marks');

    if (!lastDate || !monthYear) {
      remarkControl?.setValue(null);
      remarkControl?.enable();
      return;
    }

    const d1 = new Date(lastDate);
    const d2 = new Date(monthYear);

    const months =
      (d2.getFullYear() - d1.getFullYear()) * 12 +
      (d2.getMonth() - d1.getMonth());

    if (months < 12) {
      remarkControl?.setValue('SAT');
    } else {
      remarkControl?.setValue('UNSAT');
    }

    remarkControl?.disable();
  }

  setupConditionalLogic() {
    // ---------------- 4A Electrical Hygiene ----------------
    this.form.get('electrical_hygiene')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('electrical_hygiene_remark');
      const valueControl = this.form.get('electrical_hygiene_value');

      this.showElectricalHygieneInput = false;
      valueControl?.reset();

      if (value === 'SAT') {
        remarkControl?.setValue('NIL');
        remarkControl?.disable();
      } else if (
        value === 'SAT with observations' ||
        value === 'SAT with observation' ||
        value === 'UNSAT'
      ) {
        this.showElectricalHygieneInput = true;
        remarkControl?.setValue(null);
      } else {
        remarkControl?.setValue(null);
      }
    });

    this.form.get('lastOilChangeDate')?.valueChanges.subscribe(() => {
      this.setOilChangeRemark();
    });

    this.form.get('lastDateOfOilChange')?.valueChanges.subscribe(() => {
      this.setOilChangeRemark();
    });

    // ---------------- 4B Ops Status of Switches ----------------
    this.form.get('ops_status_switches')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('ops_status_switches_remark');
      const valueControl = this.form.get('ops_status_switches_value');

      this.showOpsSwitchInput = false;
      valueControl?.reset();

      if (value === 'Ops') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
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
          remarkControl?.disable();
        } else if (value === 'Ops') {
          remarkControl?.setValue('SAT');
          remarkControl?.disable();
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

        if (value === 'NoObservation' || value === 'No Observation') {
          remarkControl?.setValue('SAT');
          remarkControl?.disable();
        } else if (value === 'Observation') {
          this.showRustObservationFields = true;
          remarkControl?.setValue(null);
        } else {
          remarkControl?.setValue(null);
        }
      });

    this.form.get('condition_brake_band')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('condition_brake_band_remark');
      const valueControl = this.form.get('condition_brake_band_value');

      this.showBrakeBandInput = false;
      valueControl?.reset();

      if (value === 'NA' || value === 'SAT') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'UNSAT') {
        this.showBrakeBandInput = true;
        remarkControl?.setValue(null);
      } else {
        remarkControl?.setValue(null);
        remarkControl?.disable();
      }
    });

    this.form.get('greasing_points')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('greasing_points_remark');
      const valueControl = this.form.get('greasing_points_value');

      this.showGreasingPointsInput = false;
      valueControl?.reset();

      if (value === 'Charged') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'Others') {
        this.showGreasingPointsInput = true;
        remarkControl?.setValue(null);
        remarkControl?.disable();
      } else if (value) {
        remarkControl?.setValue('UNSAT');
        remarkControl?.disable();
      } else {
        remarkControl?.setValue(null);
        remarkControl?.disable();
      }
    });

    this.form.get('drive')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('drive_remark');
      const valueControl = this.form.get('drive_value');

      this.showDriveInput = false;
      valueControl?.reset();

      if (value === 'Nil') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'Noise Observed') {
        this.showDriveInput = true;
        remarkControl?.setValue(null);
      } else {
        remarkControl?.setValue(null);
      }
    });

    this.form.get('condition_capston_drum')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('condition_capston_drum_remark');
      const valueControl = this.form.get('condition_capston_drum_value');
      const observationControl = this.form.get(
        'condition_capston_drum_observation',
      );

      this.showCapstanDrumInput = false;
      this.showCapstanDrumObservationInput = false;
      valueControl?.reset();
      observationControl?.reset();

      if (value === 'Nil') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'Observation') {
        this.showCapstanDrumObservationInput = true;
        remarkControl?.setValue(null);
      } else {
        remarkControl?.setValue(null);
      }
    });

    this.form
      .get('insulation_of_motor_cable_value')
      ?.valueChanges.subscribe((value) => {
        const remarkControl = this.form.get('insulation_of_motor_cable_remark');
        const numericValue = Number(value);

        if (
          value === null ||
          value === undefined ||
          value === '' ||
          Number.isNaN(numericValue)
        ) {
          remarkControl?.setValue(null);
          return;
        }

        remarkControl?.setValue(numericValue >= 2 ? 'SAT' : 'UNSAT');
        remarkControl?.disable();
      });

    this.form.get('greasing_check')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('greasing_remark');

      if (value === 'Greased') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'Not Greased') {
        remarkControl?.setValue('UNSAT');
        remarkControl?.disable();
      } else {
        remarkControl?.setValue(null);
      }
    });

    ['low_speed', 'rated_speed', 'max_speed'].forEach((controlName) => {
      this.form.get(controlName)?.valueChanges.subscribe((value) => {
        const remarkControl = this.form.get(`${controlName}_remark`);
        const numericValue = Number(value);

        if (
          value === null ||
          value === undefined ||
          value === '' ||
          Number.isNaN(numericValue)
        ) {
          remarkControl?.setValue(null);
          remarkControl?.disable();
          return;
        }

        remarkControl?.setValue(numericValue >= 0 ? 'SAT' : 'UNSAT');
        remarkControl?.disable();
      });
    });

    this.form.get('oil_level')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('oil_level_remark');
      const remarkMap: Record<string, string> = {
        '40-100% filled': 'SAT',
        'Less than 40% filled': 'SAT with observations',
        Empty: 'UNSAT',
      };

      remarkControl?.setValue(remarkMap[value] ?? null);
      remarkControl?.disable();
    });

    this.form.get('oil_gear_box_value')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('oil_gear_box_remark');

      if (value === 'Yes') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'No') {
        remarkControl?.setValue('UNSAT');
        remarkControl?.disable();
      } else {
        remarkControl?.setValue(null);
        remarkControl?.disable();
      }
    });

    this.form.get('log_book_measured')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('log_book_remakrs');

      if (value === 'Yes') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'No') {
        remarkControl?.setValue('UNSAT');
        remarkControl?.disable();
      } else {
        remarkControl?.setValue(null);
      }
    });

    this.form.get('periodicity_measured')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('periodicity_remarks');

      if (value === 'Monthly' || value === 'Quarterly') {
        remarkControl?.setValue('SAT');
        remarkControl?.disable();
      } else if (value === 'Nil') {
        remarkControl?.setValue('UNSAT');
        remarkControl?.disable();
      } else {
        remarkControl?.setValue(null);
      }
    });

    this.form.get('spm_measured')?.valueChanges.subscribe((value) => {
      const remarkControl = this.form.get('spm_remarks');
      const remarkMap: Record<string, string> = {
        NA: 'NA',
        Green: 'SAT',
        Yellow: 'SAT with observations',
        Red: 'UNSAT',
      };

      remarkControl?.setValue(remarkMap[value] ?? null);
      remarkControl?.disable();
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

  /* ----------------------------- EQUIPMENT TABS / PREFILL ----------------------------------- */

  /**
   * Loads the trial workflow response, builds the equipment header tabs from
   * the top-level `equipment_details` stored in formApiService.context, then
   * fetches the per-equipment flat data via getFormByEquipment for the first tab.
   *
   * NOTE: FormApiService.getForm() early-returns res.json_data (not the full
   * trial object) when json_data is present, so equipment_details must be read
   * from formApiService.context which always holds the full trial response.
   */
  private async loadTrialPrefillFromQuery(): Promise<void> {
    const trialId = resolveTrialQueryParam(this.route, this.router);
    if (!trialId) return;

    this.workflowTrialId = trialId;

    try {
      // getForm() populates formApiService.context with the full trial object
      // and returns either json_data or the draft data — we ignore the return
      // value for tab-building and use context instead.
      await this.formApiService.getForm(trialId);
      const trialContext = this.formApiService.context;
      console.log('[Mooring Capstan] Trial context:', trialContext);

      // ── Build equipment tab list from the full trial context ───────────
      this.eqpList = Array.isArray(trialContext?.equipment_details)
        ? trialContext.equipment_details
        : [];

      this.activeTab =
        this.formApiService.currentEquipmentNomenclature ||
        this.eqpList[0] ||
        null;

      if (this.activeTab) {
        this.formApiService.setCurrentEquipmentNomenclature(this.activeTab);
      }

      console.log(
        '[Mooring Capstan] Equipment tabs:',
        this.eqpList,
        'Active tab:',
        this.activeTab,
      );

      // ── Ship name from the full trial context ──────────────────────────
      this.form.patchValue(
        { ship: trialContext?.ship_name || '' },
        { emitEvent: false },
      );

      // ── Fetch per-equipment flat data for the active tab ───────────────
      const nomenclature = this.formApiService.resolveNomenclature(
        this.activeTab,
      );
      const equipmentPayload = await this.formApiService.getFormByEquipment(
        trialId,
        nomenclature,
      );

      console.log(
        '[Mooring Capstan] Equipment payload to patch:',
        equipmentPayload,
      );

      this.fillData(equipmentPayload);
      this.applyEquipmentDefaults(this.activeTab);
      this.cdr.detectChanges();
    } catch (e) {
      console.error(
        '[Mooring Capstan] Trial prefill failed (load trial proforma DA)',
        e,
      );
    }
  }

  /** Called when user switches equipment tab */
  async setActiveTab(tab: any): Promise<void> {
    if (!tab || this.isSameEquipment(this.activeTab, tab)) return;

    this.activeTab = tab;
    this.formApiService.setCurrentEquipmentNomenclature(tab);

    if (!this.workflowTrialId) return;

    this.resetFormData();
    this.applyEquipmentDefaults(tab);

    try {
      const nomenclature = this.formApiService.resolveNomenclature(tab);
      // getFormByEquipment already returns the flat data object directly
      // (res?.data || res?.json_data from the json-data endpoint).
      // Do NOT attempt further json_data extraction — pass it straight to fillData.
      const equipmentPayload = await this.formApiService.getFormByEquipment(
        this.workflowTrialId,
        nomenclature,
      );

      console.log(
        '[Mooring Capstan] Switched tab payload to patch:',
        equipmentPayload,
      );

      this.fillData(equipmentPayload);
      this.applyEquipmentDefaults(this.activeTab);
      this.cdr.detectChanges();
    } catch (error) {
      console.error(
        '[Mooring Capstan] Failed to load data for selected equipment',
        error,
      );
      this.toastService.showError('Failed to load selected equipment data.');
    }
  }

  private applyEquipmentDefaults(tab: any): void {
    if (!tab) return;

    const equipmentList =
      this.formApiService?.context?.equipment_details || this.eqpList || [];
    const selectedEquipment =
      equipmentList.find(
        (eq: any) =>
          (eq.id ?? eq.equipment_id) === (tab.id ?? tab.equipment_id),
      ) || tab; // tab itself already carries manufacturer_name/model per the API shape

    this.form.patchValue(
      {
        manufacturer_name: selectedEquipment?.manufacturer_name ?? '',
        model: selectedEquipment?.model ?? '',
      },
      { emitEvent: false },
    );
  }

  /**
   * The json_data payload from this API is nested per-equipment:
   * {
   *   ...flat shared/placeholder keys (mostly unused, all empty)...,
   *   "Damage Control Console": { ...full field set for this equipment... },
   *   "Fire Detection and Alarm Panel": { ...full field set for this equipment... }
   * }
   * This pulls out the object for the given equipment key. If no nested
   * object exists under that key (e.g. brand-new trial with no equipment-
   * specific data yet), it falls back to the flat top-level object so the
   * form isn't left completely empty.
   */
  private extractEquipmentPayload(
    jsonData: any,
    equipmentKey: string | undefined,
  ): any {
    if (!jsonData || typeof jsonData !== 'object') return null;

    if (
      equipmentKey &&
      jsonData[equipmentKey] &&
      typeof jsonData[equipmentKey] === 'object'
    ) {
      return jsonData[equipmentKey];
    }

    console.warn(
      '[Mooring Capstan] No nested payload found for equipment key:',
      equipmentKey,
      '— falling back to flat/top-level json_data.',
    );
    return jsonData;
  }

  trackByEquipment(_: number, equipment: any): string | number {
    return (
      equipment?.equipment_id ?? equipment?.id ?? equipment?.nomenclature ?? _
    );
  }

  isSameEquipment(left: any, right: any): boolean {
    return (
      (left?.equipment_id ?? left?.id ?? left?.nomenclature) ===
      (right?.equipment_id ?? right?.id ?? right?.nomenclature)
    );
  }

  /** Resets the form (keeping ship name) when switching equipment tabs */
  private resetFormData(): void {
    const ship = this.form.get('ship')?.value;
    this.form.reset({}, { emitEvent: false });
    this.form.patchValue({ ship }, { emitEvent: false });
  }

  /**
   * Patches the whole form from the flat json_data payload.
   * Keys here map 1:1 to the form control names (confirmed against the
   * sample API response), so each field is patched explicitly with a
   * fallback so nothing is left undefined.
   */
  fillData(payload: any): void {
    if (!payload) return;

    console.log('[Mooring Capstan] Patching form with:', payload);

    // Use emitEvent:false so that valueChanges subscriptions (which reset/disable
    // dependent controls as side-effects) do NOT fire during the bulk patch.
    // After patching we manually restore the conditional UI flags.
    this.form.patchValue(
      {
        capstan: payload.capstan ?? '',
        port: payload.port ?? '',
        ship: payload.ship || this.form.get('ship')?.value || '',
        class_of_ship: payload.class_of_ship ?? '',
        date_of_inspection: payload.date_of_inspection ?? '',
        place_of_conduct_trail: payload.place_of_conduct_trail ?? '',
        occasion_of_conduct_trail: payload.occasion_of_conduct_trail ?? '',
        date_of_conduct_trail: payload.date_of_conduct_trail ?? '',
        authority: payload.authority ?? '',
        authority_date: payload.authority_date ?? '',
        authority_doc: payload.authority_doc ?? '',

        type: payload.type ?? '',
        make: payload.make ?? '',
        year_of_manufacture: payload.year_of_manufacture ?? '',

        electrical_hygiene: payload.electrical_hygiene ?? '',
        electrical_hygiene_remark: payload.electrical_hygiene_remark ?? '',
        electrical_hygiene_value: payload.electrical_hygiene_value ?? '',

        ops_status_switches: payload.ops_status_switches ?? '',
        ops_status_switches_remark: payload.ops_status_switches_remark ?? '',
        ops_status_switches_value: payload.ops_status_switches_value ?? '',

        ops_status_of_indicator: payload.ops_status_of_indicator ?? '',
        ops_status_of_indicator_remark:
          payload.ops_status_of_indicator_remark ?? '',
        ops_status_of_indicator_value:
          payload.ops_status_of_indicator_value ?? '',

        condition_of_foundation: payload.condition_of_foundation ?? '',
        condition_of_foundation_remark:
          payload.condition_of_foundation_remark ?? '',
        Corrosion: payload.Corrosion ?? '',
        Pitting: payload.Pitting ?? '',
        Preserved: payload.Preserved ?? '',
        Others: payload.Others ?? '',

        condition_brake_band: payload.condition_brake_band ?? '',
        condition_brake_band_remark: payload.condition_brake_band_remark ?? '',
        condition_brake_band_value: payload.condition_brake_band_value ?? '',

        insulation_of_motor_cable_value:
          payload.insulation_of_motor_cable_value ?? '',
        insulation_of_motor_cable_remark:
          payload.insulation_of_motor_cable_remark ?? '',

        greasing_check: payload.greasing_check ?? '',
        greasing_remark: payload.greasing_remark ?? '',

        greasing_points: payload.greasing_points ?? '',
        greasing_points_remark: payload.greasing_points_remark ?? '',
        greasing_points_value: payload.greasing_points_value ?? '',

        drive: payload.drive ?? '',
        drive_remark: payload.drive_remark ?? '',
        drive_value: payload.drive_value ?? '',

        condition_capston_drum: payload.condition_capston_drum ?? '',
        condition_capston_drum_remark:
          payload.condition_capston_drum_remark ?? '',
        condition_capston_drum_value:
          payload.condition_capston_drum_value ?? '',
        condition_capston_drum_observation:
          payload.condition_capston_drum_observation ?? '',

        low_speed: payload.low_speed ?? 0,
        low_speed_remark: payload.low_speed_remark ?? '',
        low_speed_value: payload.low_speed_value ?? '',

        rated_speed: payload.rated_speed ?? 0,
        rated_speed_remark: payload.rated_speed_remark ?? '',
        rated_speed_value: payload.rated_speed_value ?? '',

        max_speed: payload.max_speed ?? 0,
        max_speed_remark: payload.max_speed_remark ?? '',
        max_speed_value: payload.max_speed_value ?? '',

        oil_level: payload.oil_level ?? 0,
        oil_level_remark: payload.oil_level_remark ?? '',

        oil_gear_box: payload.oil_gear_box ?? '',
        oil_gear_box_value: payload.oil_gear_box_value ?? '',
        oil_gear_box_remark: payload.oil_gear_box_remark ?? '',

        lastOilChangeDate: payload.lastOilChangeDate ?? '',
        nextDueOilChangeDate: payload.nextDueOilChangeDate ?? '',
        lastOilChangeDate_marks: payload.lastOilChangeDate_marks ?? '',
        lastDateOfOilChange: payload.lastDateOfOilChange ?? '',

        water_content_value: payload.water_content_value ?? '',
        Viscosity_value: payload.Viscosity_value ?? '',
        base_number_value: payload.base_number_value ?? '',
        acid_number_value: payload.acid_number_value ?? '',
        metal_traces_value: payload.metal_traces_value ?? '',

        starting_current_reference: payload.starting_current_reference ?? '',
        starting_current_measured: payload.starting_current_measured ?? '',
        starting_current_remarks: payload.starting_current_remarks ?? '',

        running_current_reference: payload.running_current_reference ?? '',
        running_current_measured: payload.running_current_measured ?? '',
        running_current_remarks: payload.running_current_remarks ?? '',

        log_book_reference: payload.log_book_reference ?? '',
        log_book_measured: payload.log_book_measured ?? '',
        log_book_remakrs: payload.log_book_remakrs ?? '',

        periodicity_reference: payload.periodicity_reference ?? '',
        periodicity_measured: payload.periodicity_measured ?? '',
        periodicity_remarks: payload.periodicity_remarks ?? '',

        spm_measured: payload.spm_measured ?? '',
        spm_remarks: payload.spm_remarks ?? '',

        other_observation: payload.other_observation ?? '',
        overall_remark: payload.overall_remark ?? '',
      },
      { emitEvent: false },
    );

    // ── Restore conditional show/hide flags based on the patched values ──
    // These flags control *_value / *_remark input visibility. Since we
    // suppressed valueChanges, we derive them directly from the payload.
    const eh = payload.electrical_hygiene ?? '';
    this.showElectricalHygieneInput =
      eh === 'SAT with observations' ||
      eh === 'SAT with observation' ||
      eh === 'UNSAT';

    const sw = payload.ops_status_switches ?? '';
    this.showOpsSwitchInput = sw === 'Non-ops';

    const ind = payload.ops_status_of_indicator ?? '';
    this.showIndicatorInput = ind === 'Non-ops';

    const fnd = payload.condition_of_foundation ?? '';
    this.showRustObservationFields = fnd === 'Observation';

    const bb = payload.condition_brake_band ?? '';
    this.showBrakeBandInput = bb === 'UNSAT';

    const gp = payload.greasing_points ?? '';
    this.showGreasingPointsInput = gp === 'Others';

    const drv = payload.drive ?? '';
    this.showDriveInput = drv === 'Noise Observed';

    const drum = payload.condition_capston_drum ?? '';
    this.showCapstanDrumInput = false; // unused in template but kept in sync
    this.showCapstanDrumObservationInput = drum === 'Observation';

    // Re-enable any controls that were disabled by previous conditional logic
    // (e.g. switching away from a tab that had SAT → disabled remark field)
    [
      'electrical_hygiene_remark',
      'ops_status_switches_remark',
      'ops_status_of_indicator_remark',
      'condition_of_foundation_remark',
      'condition_brake_band_remark',
      'greasing_points_remark',
      'drive_remark',
      'condition_capston_drum_remark',
      'insulation_of_motor_cable_remark',
      'greasing_remark',
      'low_speed_remark',
      'rated_speed_remark',
      'max_speed_remark',
      'oil_level_remark',
      'oil_gear_box_remark',
      'log_book_remakrs',
      'periodicity_remarks',
      'spm_remarks',
      'lastOilChangeDate_marks',
    ].forEach((ctrl) => this.form.get(ctrl)?.enable({ emitEvent: false }));
  }

  /* ----------------------------- EDIT MODE ----------------------------------- */

  getEditDataByRowId(rowId: string) {
    this.apiService.get(`${Apiendpoints.BER_CERTIFICATE}${rowId}`).subscribe({
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

  buildPayload() {
    const formDataValues = this.form.getRawValue();

    const equipmentValues: any = {
      ...formDataValues,
      authority_doc: FileUrlUtil.getFileUrl(formDataValues.authority_doc?.id),
    };

    const equipmentKey = this.activeTab?.name || this.activeTab?.nomenclature;

    console.log(
      '[Mooring Capstan] Building payload for equipment key:',
      equipmentKey,
      equipmentValues,
    );

    // Nest under the active equipment's key so the OTHER equipment's saved
    // data in json_data isn't overwritten/lost by this save.
    const payload: any = equipmentKey
      ? { [equipmentKey]: equipmentValues }
      : equipmentValues;

    return payload;
  }

  handleSave(type: 'clear' | 'draft' | 'save' | 'submit') {
    // if (!this.canEdit) {
    //   console.warn('[Mooring Capstan] Save blocked - can_edit is false');
    //   return;
    // }
    if (type === 'clear') {
      this.form.reset();
      this.toast.showSuccess('Form cleared successfully');
      return;
    }

    if (type === 'save' && !this.validateForm()) {
      return;
    }

    const payload = this.buildPayload();

    if (type === 'draft') {
      this.saveDraft(payload);
      return;
    }

    this.submitFinalForm(payload, type);
  }

  private saveDraft(payload: any): void {
    this.draftLoading = true;

    this.formApiService
      .saveDraft(payload, resolveTrialQueryParam(this.route, this.router) || '')
      .subscribe({
        next: () => this.toast.showSuccess('Draft saved successfully.'),
        error: () => this.toast.showError('Failed to save draft.'),
        complete: () => {
          this.draftLoading = false;
        },
      });
  }

  private submitFinalForm(payload: any, type: 'save' | 'submit'): void {
    if (type === 'save') {
      this.saveLoading = true;
    } else {
      this.submitLoading = true;
    }

    this.formApiService
      .submitForm(
        payload,
        resolveTrialQueryParam(this.route, this.router) || '',
      )
      .subscribe({
        next: () => {
          if (type === 'submit') {
            this.toast.showSuccess('Forms Submitted successfully.');
            this.isSubmitTime = true;
            this.showApprovalWorkflowPopup = true;
          } else {
            this.toast.showSuccess('Forms Saved successfully.');
            this.router.navigate(['/afterAuth/ship-returns/transactions/trial']);
          }
          this.cdr.detectChanges();
        },
        error: () => {
          if (type === 'submit') {
            this.toast.showError('Failed to submit form.');
          } else {
            this.toast.showSuccess('Failed to save form.');
          }

          if (type === 'save') {
            this.saveLoading = false;
          } else {
            this.submitLoading = false;
          }
        },
        complete: () => {
          if (type === 'save') {
            this.saveLoading = false;
          } else {
            this.submitLoading = false;
          }
        },
      });
  }
  // ---------------- place of conduct trial --------------------------------
  loadPlaceOfConductTrail() {
    this.apiService
      .getDropdownData('master/locations/', {
        labelKey: 'name',
        valueKey: 'id',
      })
      .subscribe((res) => {
        Promise.resolve().then(() => {
          this.placesOptions = res || [];
          this.cdr.markForCheck();
        });
      });
  }

  handleFilesUploaded(files: UploadedFileItem[]): void {
    this.uploadedAuthorityFiles = files;
  }
}
