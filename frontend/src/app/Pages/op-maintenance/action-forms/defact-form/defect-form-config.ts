import { Validators, FormGroup, ValidatorFn } from "@angular/forms";

export interface FormField {
  key: string;
  label: string;
  controlType:
    | "text"
    | "number"
    | "date"
    | "select"
    | "textarea"
    | "file"
    | "radio";
  placeholder: string;
  fullWidth?: boolean;
  readonly?: boolean;
  validators?: ValidatorFn[];
  defaultValue?: string | number | boolean | null;
  options?: {
    label: string;
    value: string | number | boolean;
  }[];

  showWhen?: (form: FormGroup) => boolean;

  resetOnChange?: string[];
}

export const SFD_FIELDS: FormField[] = [
  {
    key: "equipmentName",
    label: "Equipment Name",
    placeholder: "Select an option",
    controlType: "select",
  },

  {
    key: "equipmentNomenclature",
    label: "Equipment Nomenclature",
    placeholder: "Select an option",
    controlType: "select",
  },

  {
    key: "equipmentSerialNo",
    label: "Equipment Serial No",
    placeholder: "Enter Equipment Serial No",
    controlType: "text",
    readonly: true,
  },

  {
    key: "onBoardLocation",
    label: "On Board Location",
    placeholder: "On Board Location",
    controlType: "text",
    readonly: true,
  },
  {
    key: "dartNo",
    label: "Dart No",
    placeholder: "Dart No",
    controlType: "text",
    readonly: true,
  },
  {
    key: "previousDartNo",
    label: "Previous Dart No",
    placeholder: "Previous Dart No",
    controlType: "text",
    readonly: true,
  },

  {
    key: "defectDate",
    label: "Defect Date",
    placeholder: "Select Defect Date",
    controlType: "date",
  },

  {
    key: "tentativeResolutionDate",
    label: "Tentative Defect Resolution By",
    placeholder: "Defect Resolution By",
    controlType: "date",
  },

  {
    key: "symptoms",
    label: "Symptoms",
    placeholder: "Select an option",
    controlType: "select",
    // options: [
    //   { label: "Low", value: "LOW" },
    //   { label: "Medium", value: "MEDIUM" },
    //   { label: "High", value: "HIGH" },
    //   { label: "Critical", value: "CRITICAL" },
    // ],
  },

  {
    key: "severity",
    label: "Severity",
    placeholder: "Select an option",
    controlType: "select",
    // options: [
    //   { label: "Low", value: "LOW" },
    //   { label: "Medium", value: "MEDIUM" },
    //   { label: "High", value: "HIGH" },
    //   { label: "Critical", value: "CRITICAL" },
    // ],
  },

  {
    key: "requiredAssistanceFor",
    label: "Required Assistance For",
    placeholder: "Select an option",
    controlType: "select",
    // options: [
    //   { label: "Low", value: "LOW" },
    //   { label: "Medium", value: "MEDIUM" },
    //   { label: "High", value: "HIGH" },
    //   { label: "Critical", value: "CRITICAL" },
    // ],
  },

  {
    key: "defectiveComponent",
    label: "Defective Component",
    placeholder: "Enter Defective Component",
    controlType: "text",
  },

  {
    key: "ssRemarksResolvedBy",
    label: "SS Remarks (Resolved By)",
    placeholder: "Select Date",
    controlType: "select",
    // options: [
    //   { label: "Low", value: "LOW" },
    //   { label: "Medium", value: "MEDIUM" },
    //   { label: "High", value: "HIGH" },
    //   { label: "Critical", value: "CRITICAL" },
    // ],
  },

  {
    key: "trialRequired",
    label: "Trial Required?",
    placeholder: "",
    controlType: "radio",
    defaultValue: false,
    options: [
      { label: "No", value: false },
      { label: "Yes", value: true },
    ],
    resetOnChange: ["trialAgency"],
  },

  {
    key: "trialAgency",
    label: "Trial Agency",
    placeholder: "Select Trial Agency",
    controlType: "select",
    showWhen: (form: FormGroup) => form.get("trialRequired")?.value === true,
    // options: [
    //   { label: "Agency 1", value: "AGENCY_1" },
    //   { label: "Agency 2", value: "AGENCY_2" },
    // ],
  },

  {
    key: "attachPhotograph",
    label: "Attach Photograph",
    placeholder: "Choose File",
    controlType: "file",
  },

  {
    key: "defectDescription",
    label: "Defect Description",
    placeholder: "Enter Defect / Assistance details",
    controlType: "textarea",
    fullWidth: true,
    validators: [Validators.maxLength(600)],
  },

  {
    key: "sparesRequired",
    label: "Spares Required?",
    placeholder: "",
    controlType: "radio",
    defaultValue: false,
    fullWidth: true,
    options: [
      { label: "No", value: false },
      { label: "Yes", value: true },
    ],
  },
];
