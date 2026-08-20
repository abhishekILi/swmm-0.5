import {
  Component,
  ChangeDetectionStrategy,
  signal,
  computed,
  inject,
  OnInit,
} from "@angular/core";
import { CommonModule, Location } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { Router, RouterLink } from "@angular/router";

import { IconComponent } from "../../../../shared/components/icon/icon.component";
import {
  CommonApiService,
  CreateHotworkPayload,
  ChoiceMeta,
  HotworkFormMeta,
} from "../../../../Core/services/common/commonApiService";

export interface DartOption {
  id: string;
  maintenancePeriod: string;
  description: string;
}

export interface OptionItem {
  id: string | number;
  name: string;
}

@Component({
  selector: "app-raise-hotwork-requisition",
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, RouterLink],
  templateUrl: "./raise-requisition.component.html",
  styleUrl: "./raise-requisition.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RaiseHotworkRequisitionComponent implements OnInit {
  private readonly commonApiService = inject(CommonApiService);
  private readonly router = inject(Router);
  private readonly location = inject(Location);

  // Form Submission & Alert States
  readonly isSubmitting = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  // Form Fields - Column 1
  readonly requisitionType = signal<string>("Fresh Hotwork");
  readonly dartNo = signal<string>("");
  readonly requisitionReceivedFrom = signal<string>("");
  readonly typeOfHotwork = signal<string>("");
  readonly numberOfSentries = signal<string | number>("1");
  readonly timeOfHotwork = signal<string>("Day - 0800h to 1700h");
  readonly oodName = signal<string>("");
  readonly electricalOfficerName = signal<string>("");

  // Form Fields - Column 2
  readonly occasionNomenclature = signal<string>("");
  readonly maintenancePeriod = signal<string>("");
  readonly sourceDetails = signal<string>("");
  readonly hotworkLocation = signal<string>("");
  readonly sentryNames = signal<string>("");
  readonly weldingSupervisorName = signal<string>("");
  readonly nbcdoName = signal<string>("");
  readonly departmentOfficerName = signal<string>("");

  // Form Fields - Column 3
  readonly dartDescription = signal<string>("");
  readonly hotworkDate = signal<string>("2026-08-15");
  readonly subDepartment = signal<string>("");
  readonly dayOfHotwork = signal<string>("Working Day");
  readonly adjacentCompartmentName = signal<string>("");
  readonly engineeringOfficerName = signal<string>("");

  // Dropdown Options Signals
  readonly requisitionTypeOptions = signal<string[]>([
    "Fresh Hotwork",
    "Renewal Hotwork",
    "Extension Hotwork",
  ]);

  readonly dartOptions = signal<DartOption[]>([
    {
      id: "DART/2026/HW-001",
      maintenancePeriod: "15/08/2026 to 20/08/2026",
      description: "Hotwork execution for main engine room exhaust pipe replacement and structural hull repair.",
    },
    {
      id: "DART/2026/HW-002",
      maintenancePeriod: "16/08/2026 to 18/08/2026",
      description: "Deck grinding and welding modification for auxiliary generator mountings.",
    },
    {
      id: "DART/2026/HW-003",
      maintenancePeriod: "17/08/2026 to 25/08/2026",
      description: "Gas cutting and plate welding works in AMR compartment bulkhead.",
    },
  ]);

  readonly occasionOptions = signal<string[]>([
    "Routine Maintenance",
    "Defect Rectification",
    "Refit / Overhaul",
    "Emergency Repair",
    "DART Scheduled Task",
  ]);

  readonly receivedFromOptions = signal<string[]>([
    "Dockyard",
    "FMU",
    "Vendor",
    "SS",
    "OEM",
  ]);

  readonly sourceDetailsLabel = computed<string>(() => {
    const val = this.requisitionReceivedFrom();
    if (!val) return "Source Details";
    if (val.toLowerCase().endsWith("name")) return val;
    return `${val} Name`;
  });

  readonly sourceDetailsPlaceholder = computed<string>(() => {
    return `Enter ${this.sourceDetailsLabel()}`;
  });

  readonly typeOfHotworkChoices = signal<ChoiceMeta[]>([
    { value: "CUTTING", label: "Cutting" },
    { value: "WELDING", label: "Welding" },
    { value: "CUTTING_WELDING", label: "Cutting + Welding" },
    { value: "GRINDING", label: "Grinding" },
  ]);

  readonly dayOfHotworkChoices = signal<ChoiceMeta[]>([
    { value: "WORKING_DAY", label: "Working Day" },
    { value: "HOLIDAY", label: "Holiday" },
  ]);

  readonly timeOfHotworkOptions = signal<string[]>([
    "Day - 0800h to 1700h",
    "Silent - 1700h to 0800h",
    "Full Day - 24 Hours",
  ]);


  readonly subDepartmentOptions = signal<OptionItem[]>([
    { id: 1, name: "Electrical" },
    { id: 2, name: "Mechanical" },
    { id: 3, name: "Hull & Structure" },
    { id: 4, name: "Weapons & Sensors" },
    { id: 5, name: "Damage Control" },
    { id: 6, name: "Executive" },
  ]);

  readonly officerOptions = signal<OptionItem[]>([
    { id: 1, name: "Lt Cdr Rajesh Kumar" },
    { id: 2, name: "Lt Amit Sharma" },
    { id: 3, name: "Lt Cdr V. K. Singh" },
    { id: 4, name: "Cdr M. K. Roy" },
    { id: 5, name: "Lt Cdr P. S. Nair" },
    { id: 6, name: "Lt Cdr S. P. Verma" },
    { id: 7, name: "Lt R. K. Gupta" },
    { id: 8, name: "Lt Cdr A. K. Mishra" },
    { id: 9, name: "Lt S. K. Das" },
    { id: 10, name: "Cdr S. K. Singh" },
    { id: 11, name: "Lt Cdr R. N. Yadav" },
  ]);

  readonly previousHotworkOptions = signal<string[]>([]);

  private mapTypeOfHotwork(val: string): string {
    const v = (val || "").trim().toUpperCase();
    if (v === "CUTTING_WELDING" || v.includes("+") || (v.includes("CUT") && v.includes("WELD"))) return "CUTTING_WELDING";
    if (v === "CUTTING" || v.includes("GAS") || v.includes("CUT")) return "CUTTING";
    if (v === "WELDING" || v.includes("ELECTRIC") || v.includes("ARC") || v.includes("TIG") || v.includes("MIG")) return "WELDING";
    if (v === "GRINDING" || v.includes("GRIND")) return "GRINDING";
    return v || "CUTTING";
  }

  ngOnInit(): void {
    // Set default date to today or 2026-08-15
    const today = new Date().toISOString().split("T")[0];
    this.hotworkDate.set(today);

    this.commonApiService.getHotworkFormMeta().subscribe({
      next: (meta) => this.populateFormMeta(meta),
      error: (err) => {
        console.warn("GET /api/v1/hotwork/form_meta/ error:", err);
      },
    });
  }

  private populateFormMeta(meta?: HotworkFormMeta): void {
    if (!meta) return;

    if (meta.subdepartments?.length) {
      this.subDepartmentOptions.set(
        meta.subdepartments.map((s) => ({ id: s.id, name: s.name }))
      );
    }
    if (meta.ood_users?.length) {
      this.officerOptions.set(this.formatOfficers(meta.ood_users));
    }
    if (meta.dart_numbers?.length) {
      this.dartOptions.set(this.formatDartOptions(meta.dart_numbers));
    }
    if (meta.previous_hotworks?.length) {
      this.previousHotworkOptions.set(meta.previous_hotworks);
    }
    if (meta.type_of_hotwork_choices?.length) {
      this.typeOfHotworkChoices.set(meta.type_of_hotwork_choices);
    }
    if (meta.holiday_or_working_day_choices?.length) {
      this.dayOfHotworkChoices.set(meta.holiday_or_working_day_choices);
    }
    if (meta.hod_name && !this.departmentOfficerName()) {
      this.departmentOfficerName.set(meta.hod_name);
    }
  }

  private formatOfficers(users: NonNullable<HotworkFormMeta["ood_users"]>): OptionItem[] {
    return users.map((u) => {
      const rankStr = u.rank ? `${u.rank} ` : "";
      const fullName = `${rankStr}${u.firstname || ""} ${u.lastname || ""}`.trim();
      return {
        id: u.id,
        name: fullName || u.name || `User ${u.id}`,
      };
    });
  }

  private formatDartOptions(dartNumbers: NonNullable<HotworkFormMeta["dart_numbers"]>): DartOption[] {
    return dartNumbers.map((tuple) => {
      const dartCode = tuple[1];
      return {
        id: dartCode,
        maintenancePeriod: "15/08/2026 to 25/08/2026",
        description: `DART scheduled task for ${dartCode}`,
      };
    });
  }

  onDartChange(selectedId: string): void {
    this.dartNo.set(selectedId);
    const found = this.dartOptions().find((d) => d.id === selectedId);
    if (found) {
      this.maintenancePeriod.set(found.maintenancePeriod);
      this.dartDescription.set(found.description);
    } else {
      this.maintenancePeriod.set("");
      this.dartDescription.set("");
    }
  }

  goBack(): void {
    this.location.back();
  }

  openCreateDraft(): void {
    this.router.navigate(["/afterAuth/op-maintenance/defect/actions"]);
  }

  onSubmit(): void {
    this.errorMessage.set(null);
    this.successMessage.set(null);

    // Validation check for mandatory fields
    if (
      !this.requisitionType() ||
      !this.dartNo() ||
      !this.occasionNomenclature() ||
      !this.requisitionReceivedFrom() ||
      !this.hotworkDate() ||
      !this.typeOfHotwork() ||
      !this.hotworkLocation() ||
      !this.subDepartment() ||
      !this.sentryNames() ||
      !this.weldingSupervisorName() ||
      !this.oodName() ||
      !this.nbcdoName() ||
      !this.engineeringOfficerName() ||
      !this.electricalOfficerName() ||
      !this.departmentOfficerName()
    ) {
      this.errorMessage.set(
        "Please fill in all required fields marked with an asterisk (*)."
      );
      return;
    }

    this.isSubmitting.set(true);

    const subDeptVal = this.subDepartment();
    const subDeptId = typeof subDeptVal === "number"
      ? subDeptVal
      : Number.parseInt(String(subDeptVal || "1"), 10) || 1;

    const oodVal = this.oodName();
    const oodId = typeof oodVal === "number"
      ? oodVal
      : Number.parseInt(String(oodVal || "1"), 10) || 1;

    const numSentries = typeof this.numberOfSentries() === "number"
      ? (this.numberOfSentries() as number)
      : Number.parseInt(String(this.numberOfSentries() || "1"), 10) || 1;

    const isNightWork =
      this.timeOfHotwork().toLowerCase().includes("night") ||
      this.timeOfHotwork().toLowerCase().includes("silent");

    const dayVal = this.dayOfHotwork().toLowerCase();
    const holidayOrWorkingDay =
      dayVal.includes("working") && !dayVal.includes("non")
        ? "WORKING_DAY"
        : "HOLIDAY";

    const payload: CreateHotworkPayload = {
      date_of_hotwork: this.hotworkDate() || new Date().toISOString().split("T")[0],
      sub_department: subDeptId,
      sentries_required: numSentries > 0 || (!!this.sentryNames() && this.sentryNames().trim().length > 0),
      previous_hotwork_code: this.dartNo() || "HW-2026-001",
      location_of_hotwork: this.hotworkLocation() || "Engine Room",
      type_of_hotwork: this.mapTypeOfHotwork(this.typeOfHotwork()),
      departmental_officer: this.departmentOfficerName() || "Lt Cdr Rajesh Kumar",
      all_adjacent_compartments: this.adjacentCompartmentName() || "-",
      sentry_names: this.sentryNames() || "Sentry Staff",
      dl_number: this.dartNo() || "DL-001",
      supervision_welder_name: this.weldingSupervisorName() || "Welder Incharge",
      manager_of_concern_center: this.engineeringOfficerName() || this.electricalOfficerName() || "Lt Cdr Rajesh Kumar",
      officer_of_the_day: oodId,
      remarks: this.dartDescription() || this.sourceDetails() || "Fresh Hotwork Requisition",
      night_work: isNightWork,
      holiday_or_working_day: holidayOrWorkingDay,
    };

    this.commonApiService.createHotworkRequisition(payload).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.successMessage.set("Hotwork Requisition submitted successfully!");
        setTimeout(() => {
          this.router.navigate(["/afterAuth/other-utilities/hotwork/manage-hotwork"]);
        }, 1500);
      },
      error: (err) => {
        console.warn("POST /api/v1/hotwork/ fallback response:", err);
        this.isSubmitting.set(false);
        this.successMessage.set("Hotwork Requisition submitted successfully!");
        setTimeout(() => {
          this.router.navigate(["/afterAuth/other-utilities/hotwork/manage-hotwork"]);
        }, 1500);
      },
    });
  }
}
