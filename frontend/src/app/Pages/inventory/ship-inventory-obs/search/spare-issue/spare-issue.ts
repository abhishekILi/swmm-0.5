import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { InputField } from "../../../../../shared/components/input-field/input-field";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { TextareaInput } from "../../../../../shared/components/textarea-input/textarea-input";
import { ObsApiService } from "../../services/obs-api.service";
import { Spare } from "../../models/spare.model";
import { IssueReason, IssueSparePayload } from "../../models/issue.model";

const REASON_OPTIONS = [
  { label: "Defect", value: "Defect" },
  { label: "Ty Loan - Other Ship", value: "Ty Loan - Other Ship" },
];

@Component({
  selector: "app-obs-spare-issue",
  standalone: true,
  imports: [ReactiveFormsModule, InputField, SelectInput, TextareaInput],
  templateUrl: "./spare-issue.html",
  styleUrl: "./spare-issue.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpareIssue implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);

  private spareId = "";
  readonly spare = signal<Spare | null>(null);
  readonly saving = signal(false);
  readonly reasonOptions = REASON_OPTIONS;
  readonly isDefect = signal(true);

  readonly form = this.fb.nonNullable.group({
    reason: ["Defect" as IssueReason, Validators.required],
    remarks: ["", Validators.required],
    quantityIssued: [1, [Validators.required, Validators.min(1)]],
    username: [""],
    section: [""],
    equipmentName: [""],
    command: [""],
    shipId: [""],
    customShip: [""],
    issuedTo: [""],
    dartNo: [""],
  });

  ngOnInit(): void {
    this.spareId = this.route.snapshot.paramMap.get("id") ?? "";
    void this.load();

    this.form.controls.reason.valueChanges.subscribe((value) => {
      this.isDefect.set(value === "Defect");
    });
  }

  private async load(): Promise<void> {
    const spare = await firstValueFrom(this.api.getSpare(this.spareId));
    this.spare.set(spare);
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    try {
      const raw = this.form.getRawValue();
      const payload: IssueSparePayload = { ...raw, quantityIssued: Number(raw.quantityIssued) };
      await firstValueFrom(this.api.issueSpare(this.spareId, payload));
      this.goBack();
    } finally {
      this.saving.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search", this.spareId]);
  }
}
