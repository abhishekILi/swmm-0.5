import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { InputField } from "../../../../../shared/components/input-field/input-field";
import { TextareaInput } from "../../../../../shared/components/textarea-input/textarea-input";
import { ObsApiService } from "../../services/obs-api.service";
import { ObsRequisitionSelectionStore } from "../../services/obs-requisition-selection-store";
import { RequisitionEntry, IssueRequisitionPayload } from "../../models/requisition.model";

@Component({
  selector: "app-obs-requisition-issue",
  standalone: true,
  imports: [ReactiveFormsModule, InputField, TextareaInput],
  templateUrl: "./requisition-issue.html",
  styleUrl: "./requisition-issue.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RequisitionIssue implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  private readonly selectionStore = inject(ObsRequisitionSelectionStore);

  private kind: "routine" | "defect" = "routine";
  readonly entries = signal<RequisitionEntry[]>([]);
  readonly quantities = signal<Record<string, number>>({});
  readonly saving = signal(false);

  readonly form = this.fb.nonNullable.group({
    username: ["", Validators.required],
    remarks: ["", Validators.required],
  });

  ngOnInit(): void {
    this.kind = (this.route.snapshot.paramMap.get("kind") as "routine" | "defect") ?? "routine";
    const selected = this.selectionStore.selectedEntries();
    if (!selected.length) {
      this.goBack();
      return;
    }
    this.entries.set(selected);
    this.quantities.set(Object.fromEntries(selected.map((e) => [e.id, e.quantityRequired || 1])));
  }

  quantityFor(entryId: string): number {
    return this.quantities()[entryId] ?? 1;
  }

  updateQuantity(entryId: string, value: string): void {
    this.quantities.update((current) => ({ ...current, [entryId]: Number(value) || 0 }));
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    try {
      const raw = this.form.getRawValue();
      const payload: IssueRequisitionPayload = {
        ...raw,
        rows: this.entries().map((entry) => ({
          entryId: entry.id,
          patternNumber: entry.patternNumber,
          description: entry.description,
          quantityAuthorised: entry.quantityAuthorised,
          quantityAvailable: entry.quantityAvailable,
          quantityIssued: this.quantityFor(entry.id),
          dartNumber: entry.dartNumber,
        })),
      };
      await firstValueFrom(this.api.issueRequisition(this.kind, payload));
      this.selectionStore.clear();
      this.goBack();
    } finally {
      this.saving.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/requisitions", this.kind]);
  }
}
