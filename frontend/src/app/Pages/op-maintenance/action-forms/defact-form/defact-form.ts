import { Component, EventEmitter, input, OnInit, Output, signal, inject } from "@angular/core";
import {
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
} from "@angular/forms";
import { CommonModule } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { SelectInput } from "../../../../shared/components/select-input/select-input";
import { InputField } from "../../../../shared/components/input-field/input-field";
import { ShipConfig } from "../../../../services/ship-config/ship-config";
import { FormField, SFD_FIELDS } from "./defect-form-config";
import { RadioInput } from "../../../../shared/components/radio-input/radio-input";
import { FileInput } from "../../../../shared/components/file-input/file-input";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { ColDef } from "ag-grid-community";
import { DefectService } from "./defect-service";
import { OperationMaintenance } from "../../../../services/operation-maintenance";
import { Router } from "@angular/router";
import { GridTextCell } from "../../../../shared/components/data-grid/grid-text-cell";
import { GridActionButton } from "../../../../shared/components/data-grid/grid-action-button/grid-action-button";
import { NotificationService } from '../../../../Core/services/notification/notification.service';
import { AppService } from "../../../../Core/services/app/app.service";
import { SpareItem, ConfirmModalData, MasterEquipmentItem } from "../action-forms.model";
import { RowData } from "ag-grid-community";

interface SymptomItem {
  id?: string | number;
  symptom_code?: string;
}

interface SeverityItem {
  id?: string | number;
  severity_name?: string;
}

interface AssistanceItem {
  id?: string | number;
  required_assistance_for?: string;
}

interface RemarksByItem {
  id?: string | number;
  description?: string;
}

interface TrialAgencyItem {
  id?: string | number;
  name?: string;
}

interface MasterDataResponse {
  next_suggested_dart_no?: string;
  previous_dart_no?: string;
  equipment_list?: MasterEquipmentItem[];
  symptoms?: SymptomItem[];
  severities?: SeverityItem[];
  assistance_options?: AssistanceItem[];
  remarks_by_list?: RemarksByItem[];
  trial_agencies?: TrialAgencyItem[];
}

interface EquipmentObjectsResponse {
  ship_equipments?: { id: string | number; nomenclature: string }[];
}

interface NomenclatureDetailsResponse {
  equipment_serial_no?: string;
  location_on_board?: string;
}

interface InitiateDartResponse {
  message?: string;
}

interface ApiErrorResponse {
  error?: {
    message?: string;
    [key: string]: unknown;
  };
  message?: string;
}

const FALLBACK_DEPARTMENT_ID = 1;
@Component({
  selector: "app-defact-form",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    SelectInput,
    InputField,
    RadioInput,
    FileInput,
    DataGrid
  ],
  templateUrl: "./defact-form.html",
  styleUrl: "./defact-form.css",
})
export class DefactForm implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private shipConfig = inject(ShipConfig);
  private DefectService = inject(DefectService);
  private opMaintenance = inject(OperationMaintenance);
  private router = inject(Router);
  private toast = inject(NotificationService);
  private appService = inject(AppService);

  private departmentId = FALLBACK_DEPARTMENT_ID;

  fields = signal<FormField[]>(SFD_FIELDS);
  form!: FormGroup;
  selectedSpares = input<SpareItem[]>([]);
  @Output() openSpare = new EventEmitter<void>();
  @Output() removeSpare = new EventEmitter<string>();
  @Output() openConfirm = new EventEmitter<void>();
  masterEquipmentList: MasterEquipmentItem[] = [];
  showSpareModal = signal(false);
  modalData = input<ConfirmModalData | undefined>();

  today = new Date();

  @Output() previewRequested = new EventEmitter<string[]>();

  openPreview(images: string[]) {
    this.previewRequested.emit(images);
  }


  openConfirmModal() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    if (
      this.form.get("sparesRequired")?.value &&
      this.selectedSpares().length === 0
    ) {
      alert("Please select spare parts");
      return;
    }

    this.openConfirm.emit();
  }


  openSpareModal() {
    this.openSpare.emit();
  }

  closeSpareModal() {
    this.showSpareModal.set(false);
  }

  onSparesSelected() {
    this.showSpareModal.set(false);
  }

  async ngOnInit() {
    await this.loadMasterData();
    this.listenEquipmentChange();
    this.listenNomenclatureChange();


  }

  async loadMasterData() {
    this.departmentId =
      (await this.opMaintenance.getCurrentDepartmentId()) ?? FALLBACK_DEPARTMENT_ID;

    const data = await this.DefectService.getMasterData(this.departmentId) as MasterDataResponse;

    this.masterEquipmentList = data.equipment_list ?? [];

    this.form.patchValue({
      dartNo: data.next_suggested_dart_no,
      previousDartNo: data.previous_dart_no,
    });

    this.fields.update((fields) =>
      fields.map((field) => {
        switch (field.key) {
          case "equipmentName":
            return {
              ...field,
              options: (data.equipment_list ?? []).map((item) => ({
                label: item.equipment_name ?? '',
                value: item.id ?? '',
              })),
            };

          case "equipmentNomenclature":
            return {
              ...field,
              options: [],
            };

          case "symptoms":
            return {
              ...field,
              options: (data.symptoms ?? []).map((item) => ({
                label: item.symptom_code ?? '',
                value: item.id ?? '',
              })),
            };

          case "severity":
            return {
              ...field,
              options: (data.severities ?? []).map((item) => ({
                label: item.severity_name ?? '',
                value: item.id ?? '',
              })),
            };

          case "requiredAssistanceFor":
            return {
              ...field,
              options: (data.assistance_options ?? []).map((item) => ({
                label: item.required_assistance_for ?? '',
                value: item.id ?? '',
              })),
            };

          case "ssRemarksResolvedBy":
            return {
              ...field,
              options: (data.remarks_by_list ?? []).map((item) => ({
                label: item.description ?? '',
                value: item.id ?? '',
              })),
            };

          case "trialAgency":
            return {
              ...field,
              options: (data.trial_agencies ?? []).map((item) => ({
                label: item.name ?? '',
                value: item.id ?? '',
              })),
            };

          default:
            return field;
        }
      }),
    );
  }

  private toNomenclatureOptions(shipEquipments: EquipmentObjectsResponse['ship_equipments']) {
    return (shipEquipments ?? []).map((item) => ({ label: item.nomenclature, value: item.id }));
  }

  // listen equipment change
  private listenEquipmentChange() {
    this.form
      .get("equipmentName")
      ?.valueChanges.subscribe(async (equipmentId) => {
        // Clear previous selected nomenclature
        this.form.patchValue({
          equipmentNomenclature: null,
        });

        const equipment = this.masterEquipmentList.find(
          (e: MasterEquipmentItem) => e.id === equipmentId,
        );

        if (!equipment) {
          return;
        }

        const response = await this.DefectService.getEquipmentObjects(
          equipment.equipment_code ?? '',
        ) as EquipmentObjectsResponse;

        this.fields.update((fields) =>
          fields.map((field) => {
            if (field.key !== "equipmentNomenclature") {
              return field;
            }

            return {
              ...field,
              options: this.toNomenclatureOptions(response.ship_equipments),
            };
          }),
        );
      });
  }

  private listenNomenclatureChange() {
    this.form
      .get("equipmentNomenclature")
      ?.valueChanges.subscribe(async (nomenclatureId) => {
        if (!nomenclatureId) {
          this.form.patchValue({
            equipmentNomenclature: null,
            equipmentSerialNo: null,
            onBoardLocation: null,
            // previousDartNo: null,
          });

          return;
        }

        const response =
          await this.DefectService.getNomenclatureDetails(nomenclatureId) as NomenclatureDetailsResponse;

        this.form.patchValue({
          equipmentSerialNo: response.equipment_serial_no,
          onBoardLocation: response.location_on_board,
        });
      });
  }

  constructor() {
    const controls: Record<string, FormControl> = {};
    this.fields().forEach((field) => {
      controls[field.key] = new FormControl(
        {
          value: field.defaultValue ?? null,
          disabled: field.readonly ?? false,
        },
        field.validators || [],
      );
    });
    this.form = this.fb.group(controls);
    this.setupDependencies();
  }

  // function for reset the value onchange of depandncies

  private setupDependencies(): void {
    this.fields().forEach((field) => {
      if (!field.resetOnChange?.length) {
        return;
      }
      this.form.get(field.key)?.valueChanges.subscribe(() => {
        field.resetOnChange?.forEach((controlName) => {
          this.form.get(controlName)?.reset();
        });
      });
    });
  }

  // hide field behalf on conditions

  isFieldVisible(field: FormField): boolean {
    if (!field.showWhen) {
      return true;
    }
    return field.showWhen(this.form);
  }

  loading = signal(false);




  async submit(modalData: ConfirmModalData) {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (
      this.form.get("sparesRequired")?.value &&
      this.selectedSpares().length === 0
    ) {
      alert("Please select spare parts");
      return;
    }

    const obsSpares: Record<string, unknown>[] = [];
    const pilSpares: Record<string, unknown>[] = [];
    const ilmsSpares: Record<string, unknown>[] = [];

    this.selectedSpares().forEach((spare) => {
      const tab = spare.sourceTab;

      const baseObj = {
        pattern: spare.item_code,
        description: spare.item_desc,
        qty: Number(spare.qtyRequired ?? 1),
      };

      // OBS + Mapped OBS
      if (tab === "OBS" || tab === "Mapped-OBS") {
        obsSpares.push({
          ...baseObj,
          inventory_type: "OBS",
        });
      }

      // PIL
      else if (tab === "PIL") {
        pilSpares.push(baseObj);
      }

      // MO + Mapped MO
      else if (
        tab === "MO Inventory" ||
        tab === "Mapped-MO Inventory"
      ) {
        ilmsSpares.push({
          ...baseObj,
          inventory_type: "MO",
        });
      }

      // WED + Mapped WED
      else if (
        tab === "WED Inventory" ||
        tab === "Mapped-WED Inventory"
      ) {
        ilmsSpares.push({
          ...baseObj,
          inventory_type: "WED",
        });
      }
    });



    try {

      this.appService.showLoader()

      const raw = this.form.getRawValue();

      console.log("raw data", raw)

      const formData = new FormData();
      formData.append("dart_type", "Defect");
      formData.append("department_id", String(this.departmentId));
      formData.append("equipmentName", String(raw.equipmentName ?? ""));
      formData.append(
        "nomenclature",
        String(raw.equipmentNomenclature ?? ""),
      );
      formData.append("equipmentSerialNo", String(raw.equipmentSerialNo ?? ""));
      formData.append("dartNo", String(raw.dartNo ?? ""));
      formData.append("previous_dart_no", String(raw.previousDartNo ?? ""));
      formData.append("onboard_location", String(raw.onBoardLocation ?? ""));
      formData.append("defectDate", String(raw.defectDate ?? ""));
      formData.append(
        "scheduledDate",
        String(raw.tentativeResolutionDate ?? ""),
      );
      formData.append("symptoms", String(raw.symptoms ?? ""));
      formData.append("severity", String(raw.severity ?? ""));
      formData.append(
        "requiredAssistance",
        String(raw.requiredAssistanceFor ?? ""),
      );
      formData.append(
        "ssRemarks",
        String(raw.ssRemarksResolvedBy ?? ""),
      );
      formData.append(
        "defectiveComponent",
        String(raw.defectiveComponent ?? ""),
      );

      formData.append(
        "maintenance_period",
        modalData?.dartForMaintenance?.toUpperCase() ?? ""
      );

      formData.append(
        "dart_occasion",
        modalData?.dartOccasion ?? ""
      );


      formData.append(
        "startDate",
        modalData?.startDate ?? ""
      );

      formData.append(
        "endDate",
        modalData?.endDate ?? ""
      );

      formData.append("defect_description", String(raw.defectDescription ?? ""));
      formData.append(
        "trial",
        raw.trialRequired ? "YES" : "NO"
      );
      formData.append("trial_agency", raw.trialAgency)
      formData.append("UniversalIDMOSTList", String(raw.trialAgency ?? ""));
      formData.append(
        "spares_required",
        raw.sparesRequired ? "YES" : "NO"
      );


      // file upload
      if (raw.attachPhotograph instanceof File) {
        formData.append(
          "attachPhotograph",
          raw.attachPhotograph,
          raw.attachPhotograph.name
        );
      }


      formData.append(
        "ops_period_id",
        String(modalData?.existingRefit ?? "")
      )

      // spares

      formData.append("obs_spares", JSON.stringify(obsSpares));
      formData.append("pil_spares", JSON.stringify(pilSpares));
      formData.append("ilms_spares", JSON.stringify(ilmsSpares));


      const response = await this.DefectService.initiateDart(formData) as InitiateDartResponse;

      this.toast.success(response?.message ?? "DART created successfully");
      this.router.navigateByUrl("/afterAuth/op-maintenance/open-darts", {
        replaceUrl: true,
      });
    } catch (err: unknown) {
      console.error(err);

      const error = err as ApiErrorResponse;
      let errorMessage = "Something went wrong";

      if (error?.error?.message) {
        errorMessage = error.error.message;
      } else if (typeof error?.error === "object" && error.error) {
        errorMessage = Object.entries(error.error)
          .map(([key, value]) => {
            const msg = Array.isArray(value) ? value.join(", ") : value;
            return `${key}: ${msg}`;
          })
          .join("\n");
      }

      this.toast.error(errorMessage);
    } finally {
      this.appService.hideLoader()
    }
  }

  reset() {
    this.form.reset();
  }

  onFileChange(event: Event, controlName: string): void {
    const input = event.target as HTMLInputElement;

    if (input.files?.length) {
      const file = input.files[0];
      this.form.get(controlName)?.setValue(file);
    }
  }

  getError(fieldName: string): string {
    const control = this.form.get(fieldName);

    if (!control?.touched) return "";

    if (control.hasError("required")) {
      return "This field is required";
    }

    if (control.hasError("maxlength")) {
      const { requiredLength, actualLength } = control.getError("maxlength");
      return `Maximum ${requiredLength} characters allowed (${actualLength} entered)`;
    }

    return "";
  }



  selectedSpareColumns: ColDef[] = [
    {
      field: "item_code",
      headerName: "Pattern No",
    },
    {
      field: "item_desc",
      headerName: "Description",
      flex: 1,
    },
    {
      field: "inventoryType",
      headerName: "Inventory Type",
    },
    {
      field: "crp_category",
      headerName: "WED Inventory Type",
    },
    {
      headerName: 'Qty Required',
      field: 'qtyRequired',
      cellRenderer: GridTextCell,
      cellRendererParams: {
        onValueChange: (row: RowData, field: string, value: unknown) => {
          (row as Record<string, unknown>)[field] = Number(value as string) || 1;

          console.log('Updated Row:', row);
        },
      },
    },
    {
      headerName: 'Actions',
      cellRenderer: GridActionButton,
      cellRendererParams: {
        label: 'Remove',
        backgroundColor: '#fb162281',
        onDelete: (row: RowData) => {
          console.log('remove spare emits')
          this.removeSpare.emit(String((row as Record<string, unknown>)['pk'] ?? ''));
        },
      },
    }
  ];
}
