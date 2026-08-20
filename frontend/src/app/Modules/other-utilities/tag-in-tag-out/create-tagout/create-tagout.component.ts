import {
  Component,
  ChangeDetectionStrategy,
  signal,
  inject,
  OnInit,
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { Router } from "@angular/router";

import { IconComponent } from "../../../../shared/components/icon/icon.component";
import {
  CommonApiService,
  CreateTagoutPayload,
  CurrentUserResponse,
  DepartmentItem,
} from "../../../../Core/services/common/commonApiService";

export interface EquipmentOption {
  id: number;
  name: string;
}

export interface SelectOption {
  value: string;
  label: string;
}

interface EquipmentItem {
  id?: number;
  name?: string;
  nomenclature?: string;
  equipment_name?: string;
  label?: string;
}

interface EquipmentDropdownResponse {
  equipments?: EquipmentItem[];
  equipment?: EquipmentItem[];
}

@Component({
  selector: "app-create-tagout",
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: "./create-tagout.component.html",
  styleUrl: "./create-tagout.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CreateTagoutComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly commonApiService = inject(CommonApiService);

  // Form Signals - Basic
  readonly date = signal<string>(new Date().toISOString().slice(0, 10));
  readonly ship = signal<string>("INS TABAR");
  readonly department = signal<string>("ENGINEERING");

  // Equipment Details
  readonly tagoutEquipmentName = signal<number | null>(null);
  readonly nameOfSubSystem = signal<string>("");
  readonly nameOfComponent = signal<string>("");
  readonly serialNoOfComponent = signal<string>("");
  readonly patternNoOfComponent = signal<string>("");
  readonly weightOfItem = signal<string>("");

  // Status & Type
  readonly type = signal<"Danger" | "Warning">("Danger");
  readonly condition = signal<"Ops" | "Non Ops" | "Partially Ops">("Ops");
  readonly specialInstructions = signal<string>("");

  // Department & Reason
  readonly departmentAffected = signal<string>("ENGINEERING");
  readonly expectedDateOfTagin = signal<string>("");
  readonly tagoutReason = signal<string>("ty_loan_rtlapp");

  // Description & Maintainer
  readonly tagoutDescription = signal<string>("");
  readonly tagoutMaintainer = signal<string>("Cdr Hod ENG");

  // Additional Schema Specific Fields
  readonly tyLoanShip = signal<string>("");
  readonly tyAuthority = signal<string>("");
  readonly tyItemTakenBy = signal<string>("");
  readonly tyAdditionalItems = signal<string>("");
  readonly surveryDemandAuthority = signal<string>("");
  readonly repairRaNumber = signal<string>("");
  readonly repairLandedDetails = signal<string>("");
  readonly repairItemTakenBy = signal<string>("");
  readonly repairAdditionalItems = signal<string>("");
  readonly aberAuthority = signal<string>("");
  readonly replacementItem = signal<string>("");
  readonly estimatedBomArrivalDate = signal<string>("");

  // State Signals
  readonly isSubmitting = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  // Master Dropdown Options
  readonly equipmentOptions = signal<EquipmentOption[]>([
    { id: 1, name: "Main Engine" },
    { id: 2, name: "Auxiliary Boiler" },
    { id: 3, name: "Steering Gear Unit" },
    { id: 4, name: "Main Fire Pump" },
    { id: 5, name: "Lube Oil Purifier" },
    { id: 6, name: "Air Compressor" },
    { id: 7, name: "Diesel Generator #1" },
    { id: 8, name: "Chiller Plant #2" },
    { id: 9, name: "Radar Cooling System" },
  ]);

  readonly departmentOptions = signal<DepartmentItem[]>([]);

  readonly reasonOptions = signal<SelectOption[]>([
    { value: "ty_loan_rtlapp", label: "TY Loan / RTLAPP" },
    { value: "survey_and_demand", label: "Survey & Demand" },
    { value: "repair_or_overhauling", label: "Repair / Overhauling" },
    { value: "aber_replacement", label: "ABER Replacement" },
  ]);

  ngOnInit(): void {
    this.loadEquipmentDropdowns();
    this.loadDepartments();
    this.loadCurrentUserProfile();
  }

  private loadEquipmentDropdowns(): void {
    this.commonApiService.getTagoutShipEquipments().subscribe({
      next: (res) => {
        const equipments = res?.ship_equipments;
        if (equipments && Array.isArray(equipments) && equipments.length > 0) {
          const list: EquipmentOption[] = equipments.map((e, idx) => ({
            id: e.id || idx + 1,
            name: e.nomenclature || e.name || `Equipment #${e.id || idx + 1}`,
          }));
          this.equipmentOptions.set(list);
        } else {
          this.loadTagoutFormMetaFallback();
        }
      },
      error: () => {
        this.loadTagoutFormMetaFallback();
      },
    });
  }

  private loadTagoutFormMetaFallback(): void {
    this.commonApiService.getTagoutFormMeta().subscribe({
      next: (res) => {
        const equipments = res?.ship_equipments;
        if (equipments && Array.isArray(equipments) && equipments.length > 0) {
          const list: EquipmentOption[] = equipments.map((e, idx) => ({
            id: e.id || idx + 1,
            name: e.nomenclature || e.name || `Equipment #${e.id || idx + 1}`,
          }));
          this.equipmentOptions.set(list);
        } else {
          this.loadEquipmentFallback();
        }
      },
      error: () => {
        this.loadEquipmentFallback();
      },
    });
  }

  private loadEquipmentFallback(): void {
    this.commonApiService.getEquipmentSystemDropdowns().subscribe({
      next: (res: EquipmentDropdownResponse) => {
        const items = res?.equipments || res?.equipment;
        if (items && Array.isArray(items) && items.length > 0) {
          const list: EquipmentOption[] = items.map((e: EquipmentItem, idx: number) => ({
            id: e.id || idx + 1,
            name: e.nomenclature || e.name || e.equipment_name || e.label || `Equipment #${e.id || idx + 1}`,
          }));
          this.equipmentOptions.set(list);
        }
      },
      error: () => {
        // Keeps default clean options
      },
    });
  }

  private loadDepartments(): void {
    this.commonApiService.getDepartments().subscribe({
      next: (depts: DepartmentItem[]) => {
        if (Array.isArray(depts) && depts.length > 0) {
          this.departmentOptions.set(depts);
          if (!this.departmentAffected() && depts[0]) {
            this.departmentAffected.set(String(depts[0].id));
          }
        }
      },
      error: () => {
        // Keeps default clean options
      },
    });
  }

  private loadCurrentUserProfile(): void {
    this.commonApiService.getCurrentUser().subscribe({
      next: (res: CurrentUserResponse) => {
        const profile = res?.profile;
        if (!profile) return;

        // Auto-populate Department text & affected department ID
        const deptName = profile.department_detail?.name || profile.section;
        if (deptName) {
          this.department.set(deptName);
        }
        if (profile.department) {
          this.departmentAffected.set(String(profile.department));
        }

        // Auto-populate Ship
        const shipName =
          profile.command_name_detail?.unit_name ||
          profile.command_name_detail?.command_name;
        if (shipName) {
          this.ship.set(shipName);
        }

        // Auto-populate Maintainer Name & Rank
        const rankName = profile.rank_detail?.name || "";
        const firstName = profile.firstname || "";
        const lastName = profile.lastname || "";
        const fullName =
          `${rankName} ${firstName} ${lastName}`.trim() || profile.designation;
        if (fullName) {
          this.tagoutMaintainer.set(fullName);
        }
      },
      error: () => {
        // Keeps default clean values on error
      },
    });
  }

  onTypeChange(val: "Danger" | "Warning"): void {
    this.type.set(val);
    if (val === "Danger") {
      this.specialInstructions.set("");
    }
  }

  onReasonChange(val: string): void {
    this.tagoutReason.set(val);
    if (val !== "ty_loan_rtlapp") {
      this.tyLoanShip.set("");
      this.tyAuthority.set("");
      this.tyItemTakenBy.set("");
      this.tyAdditionalItems.set("");
    }
    if (val !== "survey_and_demand") {
      this.surveryDemandAuthority.set("");
    }
    if (val !== "repair_or_overhauling") {
      this.repairRaNumber.set("");
      this.repairLandedDetails.set("");
      this.repairItemTakenBy.set("");
      this.repairAdditionalItems.set("");
    }
    if (val !== "aber_replacement") {
      this.aberAuthority.set("");
      this.replacementItem.set("");
      this.estimatedBomArrivalDate.set("");
    }
  }

  onSubmit(): void {
    const validationError = this.validateForm();
    if (validationError) {
      this.errorMessage.set(validationError);
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const payload = this.buildPayload();
    console.log("Submitting Tagout Payload to POST api/v1/inout-tags/tagouts/:", payload);

    this.commonApiService.createTagout(payload).subscribe({
      next: (res) => this.handleSuccess(res),
      error: (err: unknown) => this.handleError(err),
    });
  }

  private validateForm(): string | null {
    return this.validateBasicFields() || this.validateReasonFields();
  }

  private validateBasicFields(): string | null {
    if (!this.tagoutEquipmentName()) return "Please select TagOut Equipment Name.";
    if (!this.nameOfSubSystem().trim()) return "Please enter Name Of Sub System.";
    if (!this.nameOfComponent().trim()) return "Please enter Name Of Component.";
    if (!this.serialNoOfComponent().trim()) return "Please enter Serial No Of Component.";
    if (!this.weightOfItem().trim()) return "Please enter Weight Of Item.";
    if (!this.expectedDateOfTagin()) return "Please select Expected Date Of Tag in.";
    if (!this.tagoutDescription().trim()) return "Please enter TagOut Description.";
    return null;
  }

  private validateReasonFields(): string | null {
    const reason = this.tagoutReason();
    switch (reason) {
      case "ty_loan_rtlapp":
        if (!this.tyAuthority().trim()) return "Please enter Authority for Ty Loan / RTLAPP.";
        if (!this.tyAdditionalItems().trim()) return "Please enter Any Additional Items for Ty Loan / RTLAPP.";
        break;
      case "survey_and_demand":
        if (!this.surveryDemandAuthority().trim()) return "Please enter Authority for Survey & Demand.";
        break;
      case "repair_or_overhauling":
        if (!this.repairRaNumber().trim()) return "Please enter RA Number for Repair / Overhauling.";
        if (!this.repairLandedDetails().trim()) return "Please enter Landed In Centre No. / OEM Details.";
        break;
      case "aber_replacement":
        if (!this.aberAuthority().trim()) return "Please enter Authority for ABER Replacement.";
        if (!this.replacementItem().trim()) return "Please enter Replacement Item.";
        break;
    }
    return null;
  }

  private getConditionValue(): string {
    const cond = this.condition();
    if (cond === "Non Ops") return "non_ops";
    if (cond === "Partially Ops") return "partially_ops";
    return "ops";
  }

  private getEquipmentPk(): number {
    const val = Number(this.tagoutEquipmentName());
    return !isNaN(val) && val >= 1 ? val : 1;
  }

  private buildPayload(): CreateTagoutPayload {
    const typeValue = this.type() ? this.type().toLowerCase() : "danger";
    const conditionValue = this.getConditionValue();
    const equipPk = this.getEquipmentPk();
    const reasonSlug = this.tagoutReason() || "ty_loan_rtlapp";
    const defaultDate = this.date() || new Date().toISOString().slice(0, 10);

    const descText =
      this.tagoutDescription().trim() ||
      `TagOut initiated for ${this.nameOfComponent() || this.nameOfSubSystem() || "Equipment"}`;

    return {
      date: defaultDate,
      tagout_equipment_name: equipPk,
      name_of_subsystem: this.nameOfSubSystem() || "N/A",
      name_of_component: this.nameOfComponent() || "N/A",
      serial_number_of_component: this.serialNoOfComponent() || "N/A",
      serial_no_of_component: this.serialNoOfComponent() || "N/A",
      pattern_number_of_component: this.patternNoOfComponent() || "N/A",
      pattern_no_of_components: this.patternNoOfComponent() || "N/A",
      weight_of_component: this.weightOfItem() || "0",
      weight_of_item: this.weightOfItem() || "0",
      type: typeValue,
      condition: conditionValue,
      special_instructions: this.specialInstructions() || "None",
      departments_affected: [Number(this.departmentAffected()) || 1],
      department_affected: [Number(this.departmentAffected()) || 1],
      expected_date_of_tagin: this.expectedDateOfTagin() || defaultDate,
      tagout_reason: reasonSlug,
      tag_out_reason: reasonSlug,
      tagout_description: descText,
      tagout_maintainer_name_rank: this.tagoutMaintainer() || "Cdr Hod ENG",

      ty_loan_ship: this.tyLoanShip() || "",
      ty_authority: this.tyAuthority() || "",
      authority: this.tyAuthority() || "",
      ty_item_taken_by: this.tyItemTakenBy() || "",
      item_taken_by: this.tyItemTakenBy() || "",
      ty_additional_items: this.tyAdditionalItems() || "",
      additional_items: this.tyAdditionalItems() || "",

      survery_demand_authority: this.surveryDemandAuthority() || "",
      survey_authority: this.surveryDemandAuthority() || "",

      repair_ra_number: this.repairRaNumber() || "",
      ra_number: this.repairRaNumber() || "",
      repair_landed_details: this.repairLandedDetails() || "",
      oem_details: this.repairLandedDetails() || "",
      repair_item_taken_by: this.repairItemTakenBy() || "",
      repair_additional_items: this.repairAdditionalItems() || "",

      aber_authority: this.aberAuthority() || "",
      replacement_item: this.replacementItem() || "",
      estimated_bom_arrival_date:
        this.estimatedBomArrivalDate() || this.expectedDateOfTagin() || defaultDate,
    };
  }

  private handleSuccess(res: unknown): void {
    console.log("POST api/v1/inout-tags/tagouts/ success:", res);
    this.isSubmitting.set(false);
    this.successMessage.set("TagOut submitted successfully!");
    setTimeout(() => {
      this.goBack();
    }, 1200);
  }

  private handleError(err: unknown): void {
    console.error("POST api/v1/inout-tags/tagouts/ error:", err);
    this.isSubmitting.set(false);

    const errObj = err as { error?: unknown; message?: string; status?: number };
    let msg = this.extractErrorMessage(errObj);

    if (errObj?.status === 0 || msg.includes("isTrusted")) {
      msg = "Unable to connect to the backend server. Please ensure the backend server is running.";
    }

    this.errorMessage.set(msg);
  }

  private extractErrorMessage(errObj: { error?: unknown; message?: string }): string {
    if (typeof errObj?.error === "string") {
      return errObj.error;
    }
    if (typeof errObj?.error === "object" && errObj.error !== null) {
      return this.parseErrorRecord(errObj.error as Record<string, unknown>);
    }
    if (errObj?.message) {
      return errObj.message;
    }
    return "Failed to submit TagOut.";
  }

  private parseErrorRecord(errRecord: Record<string, unknown>): string {
    if ("isTrusted" in errRecord || (typeof ProgressEvent !== "undefined" && errRecord instanceof ProgressEvent)) {
      return "Unable to connect to the backend server. Please ensure the backend server is running.";
    }

    const errs: string[] = [];
    for (const [key, val] of Object.entries(errRecord)) {
      errs.push(`${key}: ${this.formatErrorVal(val)}`);
    }
    return errs.join("; ") || "Server validation error occurred.";
  }

  private formatErrorVal(val: unknown): string {
    if (Array.isArray(val)) {
      return val.join(", ");
    }
    if (typeof val === "string") {
      return val;
    }
    return JSON.stringify(val);
  }

  goBack(): void {
    this.router.navigate(["/afterAuth/other-utilities/tag-in-tag-out/tag-out"]);
  }
}
