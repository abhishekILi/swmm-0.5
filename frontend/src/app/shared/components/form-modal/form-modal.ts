import { ChangeDetectorRef, Component, Input, Output, EventEmitter, inject, OnInit } from '@angular/core';

import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule
} from '@angular/forms';

import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { SelectInput } from '../select-input/select-input';
import { InputField } from '../input-field/input-field';
import { DefectService } from '../../../Pages/op-maintenance/action-forms/defact-form/defect-service';
import { OperationMaintenance } from '../../../services/operation-maintenance';

interface ModalField {
  key: string;
  label: string;
  type: 'text' | 'select' | 'date' | 'textarea';

  placeholder?: string;

  options?: {
    label: string;
    value: string | number;
  }[];

  value?: string | number;
  readonly?: boolean;
}

/** A single entry from the `ops_period`/`refit_period` arrays already returned
 * by `add_dart/?department_id=<id>` — there is no separate "maintenance period
 * name" endpoint; that data lives here. */
interface MaintenancePeriodEntry {
  id: number | string;
  maintaince_period_type: string;
  occassion: string;
  period_name: string;
  start_date: string;
  end_date: string;
}

interface MaintenanceMasterData {
  maitainance_period_types?: string[];
  ops_period?: MaintenancePeriodEntry[];
  refit_period?: MaintenancePeriodEntry[];
}

interface MaintenancePeriodOption {
  id: number | string;
  name: string;
  start_date: string;
  end_date: string;
}

// Occasions that carry a linked existing-period lookup (id + start/end date), matching the
// legacy DART flow exactly: Operational's AMP/SMP/EAMP show an "Existing Nomenclature"
// picker + Completion Date; Refit's DL II shows an "Existing Refit" picker + End Date.
// Everything else is a plain occasion with no extra fields.
const OPERATIONAL_PERIOD_OCCASIONS = ['AMP', 'SMP', 'EAMP'];
const REFIT_PERIOD_OCCASIONS = ['DL II'];
const OPERATIONAL_TYPE = 'OPERATIONAL';
const REFIT_TYPE = 'REFIT';

// DART Occasion is a fixed, hardcoded list per maintenance period type — there is no
// backend endpoint for this, and none is planned; these match the legacy DART UI exactly.
const OPERATIONAL_OCCASIONS = [
  'Normal RA',
  'Signal RA',
  'OPDEF',
  'Guarantee DEFECT',
  'AMP',
  'SMP',
  'EAMP',
  'Trial Unit Observations',
  'OST/Workup Observations',
];
const REFIT_OCCASIONS = ['DL II', 'SDL', 'AWRF', 'REFIT RA'];

// Sentinel value for the "Existing Nomenclature" dropdown's escape hatch — selecting it
// sends the user to the SMP/AMP/EAMP master-data page instead of picking a period.
const CREATE_NEW_NOMENCLATURE = 'create_new';

@Component({
  selector: 'app-form-modal',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    SelectInput,
    InputField
  ],
  templateUrl: './form-modal.html',
  styleUrl: './form-modal.css',
})


export class FormModal implements OnInit {
  private fb = inject(FormBuilder);
  private defectService = inject(DefectService);
  private opMaintenance = inject(OperationMaintenance);
  private cdr = inject(ChangeDetectorRef);
  private router = inject(Router);

  @Input() title = 'Confirm Save';


  @Output() save = new EventEmitter<Record<string, unknown>>();

  @Output() cancel_btn = new EventEmitter<void>();
  showRefitFields = false;
  form!: FormGroup;


  fields: ModalField[] = [
    {
      key: 'dartForMaintenance',
      label: 'DART For Maintenance',
      type: 'select',
      value: '',
      options: []
    },
    {
      key: 'dartOccasion',
      label: 'DART Occasion',
      type: 'select',
      value: '',
      options: []
    },
    {
      key: 'existingRefit',
      label: 'Existing Refit',
      type: 'select',
      value: '',
      options: []
    },
    {
      key: 'startDate',
      label: 'Start Date',
      type: 'date',
      readonly: true
    },
    {
      key: 'endDate',
      label: 'End Date',
      type: 'date',
      readonly: true
    }
  ];

  /** Raw period entries from add_dart/'s `ops_period`/`refit_period` — filtered
   * down (by occasion, for Operational) into `maintenancePeriods` below whenever
   * the Occasion field changes. */
  private opsPeriods: MaintenancePeriodEntry[] = [];
  private refitPeriods: MaintenancePeriodEntry[] = [];
  maintenancePeriods: MaintenancePeriodOption[] = [];

  async ngOnInit() {
    await this.loadMasterData();

    const controls: Record<string, unknown> = {};

    this.fields.forEach(field => {
      controls[field.key] = [
        {
          value: field.value ?? null,
          disabled:
            field.key === 'startDate' ||
            field.key === 'endDate'
        }
      ];
    });

    this.form = this.fb.group(controls);

    // Maintenance Type Change
    this.form
      .get('dartForMaintenance')
      ?.valueChanges.subscribe(value => {
        this.updateDartOccasionOptions(value);
        this.resetPeriodFieldLabels();

        this.form.patchValue({
          dartOccasion: null,
          existingRefit: null,
          startDate: null,
          endDate: null
        });
      });

    // Occasion Change
    this.form
      .get('dartOccasion')
      ?.valueChanges.subscribe(occasion => {

        const maintenanceType: string =
          this.form.get('dartForMaintenance')?.value ?? '';

        const isOperationalPeriod =
          maintenanceType.toUpperCase() === OPERATIONAL_TYPE &&
          OPERATIONAL_PERIOD_OCCASIONS.includes(occasion);

        const isRefitPeriod =
          maintenanceType.toUpperCase() === REFIT_TYPE &&
          REFIT_PERIOD_OCCASIONS.includes(occasion);

        const needsPeriodBlock = isOperationalPeriod || isRefitPeriod;

        this.showRefitFields = needsPeriodBlock;

        const refitField = this.fields.find(f => f.key === 'existingRefit');
        const endDateField = this.fields.find(f => f.key === 'endDate');

        if (refitField) {
          refitField.label = isOperationalPeriod
            ? `Existing Nomenclature ${occasion}`
            : 'Existing Refit';
        }
        if (endDateField) {
          endDateField.label = isOperationalPeriod ? 'Completion Date' : 'End Date';
        }

        if (!needsPeriodBlock) {
          this.form.patchValue({
            existingRefit: null,
            startDate: null,
            endDate: null
          });

          return;
        }

        this.applyExistingPeriodOptions(occasion, isOperationalPeriod);
        this.cdr.detectChanges();
      });

    // Existing Refit / Existing Nomenclature Change
    this.form
      .get('existingRefit')
      ?.valueChanges.subscribe(id => {

        if (id === CREATE_NEW_NOMENCLATURE) {
          this.router.navigateByUrl('/afterAuth/op-maintenance/references/masters');
          this.cancel_btn.emit();
          return;
        }

        const selected =
          this.maintenancePeriods.find(
            x => x.id === id
          );

        if (!selected) {
          return;
        }

        this.form.patchValue({
          startDate: selected.start_date,
          endDate: selected.end_date
        });
      });

    this.cdr.detectChanges();
  }
  async loadMasterData() {
    const departmentId = (await this.opMaintenance.getCurrentDepartmentId()) ?? 1;
    const data =
      (await this.defectService.getMasterData(departmentId)) as MaintenanceMasterData;

    // Maintenance Type Dropdown
    const maintenanceField =
      this.fields.find(
        f => f.key === 'dartForMaintenance'
      );

    if (maintenanceField) {
      maintenanceField.options =
        (data.maitainance_period_types ?? [OPERATIONAL_TYPE, REFIT_TYPE]).map(
          (item: string) => ({
            label: item,
            value: item
          })
        );
    }

    // ops_period/refit_period come straight from add_dart/'s response — there is
    // no separate "maintenance period name" endpoint to call.
    this.opsPeriods = data.ops_period ?? [];
    this.refitPeriods = data.refit_period ?? [];
  }

  /** Populates the "Existing Nomenclature"/"Existing Refit" dropdown from the
   * already-fetched master data instead of a network call:
   * - Operational + AMP/SMP/EAMP: `opsPeriods` filtered to the matching occasion.
   * - Refit + DL II: every `refitPeriods` entry (they represent the active refit
   *   cycles, not ones tied 1:1 to a "DL II" occasion), plus no create-new option. */
  private applyExistingPeriodOptions(occasion: string, isOperationalPeriod: boolean): void {
    const source = isOperationalPeriod
      ? this.opsPeriods.filter(p => p.occassion?.toUpperCase() === occasion.toUpperCase())
      : this.refitPeriods;

    this.maintenancePeriods = source.map(p => ({
      id: p.id,
      name: p.period_name,
      start_date: p.start_date,
      end_date: p.end_date,
    }));

    const refitField = this.fields.find(f => f.key === 'existingRefit');
    if (!refitField) {
      return;
    }

    const periodOptions = this.maintenancePeriods.map(item => ({
      label: item.name,
      value: item.id,
    }));

    refitField.options = isOperationalPeriod
      ? [...periodOptions, { label: 'Create New Nomenclature', value: CREATE_NEW_NOMENCLATURE }]
      : periodOptions;

    this.form.patchValue({
      existingRefit: null,
      startDate: null,
      endDate: null
    }, { emitEvent: false });
  }

  private resetPeriodFieldLabels(): void {
    const refitField = this.fields.find(f => f.key === 'existingRefit');
    const endDateField = this.fields.find(f => f.key === 'endDate');

    if (refitField) {
      refitField.label = 'Existing Refit';
    }
    if (endDateField) {
      endDateField.label = 'End Date';
    }
  }

  updateDartOccasionOptions(
    maintenanceType: string
  ) {
    const occasionField =
      this.fields.find(
        f => f.key === 'dartOccasion'
      );

    if (!occasionField) {
      return;
    }

    const maintenanceTypeKey = (maintenanceType ?? '').toUpperCase();
    let occasions: string[] = [];

    if (maintenanceTypeKey === REFIT_TYPE) {
      occasions = REFIT_OCCASIONS;
    } else if (maintenanceTypeKey === OPERATIONAL_TYPE) {
      occasions = OPERATIONAL_OCCASIONS;
    }

    occasionField.options = occasions.map((item: string) => ({
      label: item,
      value: item
    }));
  }

  shouldShowField(field: ModalField): boolean {
    const dependentFields = [
      'existingRefit',
      'startDate',
      'endDate'
    ];

    if (dependentFields.includes(field.key)) {
      return this.showRefitFields;
    }

    return true;
  }
  onSave() {
    this.save.emit(this.form.getRawValue());
  }

  onCancel() {
    this.cancel_btn.emit();
  }

}
