import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { InputField } from "../../../../../shared/components/input-field/input-field";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { TextareaInput } from "../../../../../shared/components/textarea-input/textarea-input";
import { ObsApiService } from "../../services/obs-api.service";
import { ObsSelectionStore } from "../../services/obs-selection-store";
import { Spare } from "../../models/spare.model";
import { IssueReason, MultiIssuePayload, MultiIssueRow } from "../../models/issue.model";

const REASON_OPTIONS = [
  { label: "Defect", value: "Defect" },
  { label: "Ty Loan - Other Ship", value: "Ty Loan - Other Ship" },
];

@Component({
  selector: "app-obs-multi-issue",
  standalone: true,
  imports: [ReactiveFormsModule, InputField, SelectInput, TextareaInput],
  templateUrl: "./multi-issue.html",
  styleUrl: "./multi-issue.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MultiIssue implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly selectionStore = inject(ObsSelectionStore);

  readonly spares = signal<Spare[]>([]);
  readonly quantities = signal<Record<string, number>>({});
  readonly saving = signal(false);
  readonly reasonOptions = REASON_OPTIONS;
  readonly isDefect = signal(true);

  readonly form = this.fb.nonNullable.group({
    reason: ["Defect" as IssueReason, Validators.required],
    remarks: ["", Validators.required],
    username: [""],
    section: [""],
    equipmentName: [""],
    command: [""],
    shipId: [""],
    customShip: [""],
  });

  ngOnInit(): void {
    const selected = this.selectionStore.selectedSpares();
    if (!selected.length) {
      this.goBack();
      return;
    }
    this.spares.set(selected);
    this.quantities.set(Object.fromEntries(selected.map((s) => [s.id, 1])));

    this.form.controls.reason.valueChanges.subscribe((value) => {
      this.isDefect.set(value === "Defect");
    });
  }

  quantityFor(spareId: string): number {
    return this.quantities()[spareId] ?? 1;
  }

  updateQuantity(spareId: string, value: string): void {
    this.quantities.update((current) => ({ ...current, [spareId]: Number(value) || 0 }));
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    try {
      const raw = this.form.getRawValue();
      const rows: MultiIssueRow[] = this.spares().map((spare) => ({
        spareId: spare.id,
        patternNumber: spare.patternNumber,
        description: spare.description,
        quantityAuthorised: spare.quantityAuthorised,
        quantityAvailable: spare.quantityAvailable,
        quantityIssued: this.quantityFor(spare.id),
      }));
      const payload: MultiIssuePayload = { ...raw, rows };
      await firstValueFrom(this.api.issueMultiple(payload));
      this.selectionStore.clear();
      this.goBack();
    } finally {
      this.saving.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search"]);
  }
}
