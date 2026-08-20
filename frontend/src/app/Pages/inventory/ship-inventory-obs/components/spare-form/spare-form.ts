import { ChangeDetectionStrategy, Component, OnInit, inject, input, output } from "@angular/core";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { InputField } from "../../../../../shared/components/input-field/input-field";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { TextareaInput } from "../../../../../shared/components/textarea-input/textarea-input";
import { FileInput } from "../../../../../shared/components/file-input/file-input";
import { ObsApiService } from "../../services/obs-api.service";
import { DropdownOptionDto, Spare, SpareCategory, SpareFormPayload } from "../../models/spare.model";

const CATEGORY_OPTIONS: { label: string; value: SpareCategory }[] = [
  { label: "Consumable", value: "CONSUMABLE" },
  { label: "Permanent", value: "PERMANENT" },
  { label: "Returnable", value: "RETURNABLE" },
  { label: "IM", value: "IM" },
];

const CRITICAL_OPTIONS: { label: string; value: "YES" | "NO" }[] = [
  { label: "NO", value: "NO" },
  { label: "YES", value: "YES" },
];

@Component({
  selector: "app-obs-spare-form",
  standalone: true,
  imports: [ReactiveFormsModule, InputField, SelectInput, TextareaInput, FileInput],
  templateUrl: "./spare-form.html",
  styleUrl: "./spare-form.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpareForm implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly fb = inject(FormBuilder);

  readonly initialValue = input<Spare | null>(null);
  readonly saving = input(false);
  readonly submitted = output<SpareFormPayload>();
  readonly cancelled = output<void>();

  readonly categoryOptions = CATEGORY_OPTIONS;
  readonly criticalOptions = CRITICAL_OPTIONS;
  spareClasses: DropdownOptionDto[] = [];
  equipmentClasses: DropdownOptionDto[] = [];
  denominations: DropdownOptionDto[] = [];
  authorities: DropdownOptionDto[] = [];

  readonly form = this.fb.nonNullable.group({
    spareClass: ["", Validators.required],
    equipmentClass: ["", Validators.required],
    patternNumber: ["", Validators.required],
    description: ["", Validators.required],
    compartment: [""],
    rackPosition: [""],
    rackNumber: [""],
    location: [""],
    category: ["PERMANENT" as SpareCategory, Validators.required],
    critical: ["NO" as "YES" | "NO"],
    denomination: ["", Validators.required],
    authority: ["", Validators.required],
    quantityAuthorised: [0, [Validators.required, Validators.min(0)]],
    quantityAvailable: [0, [Validators.required, Validators.min(0)]],
    page: [""],
    line: [""],
    remarks: [""],
    image: this.fb.control<File | null>(null),
  });

  ngOnInit(): void {
    void this.loadDropdowns();
  }

  private async loadDropdowns(): Promise<void> {
    const [spareClasses, equipmentClasses, denominations, authorities] = await Promise.all([
      firstValueFrom(this.api.getSpareClasses()),
      firstValueFrom(this.api.getEquipmentClasses()),
      firstValueFrom(this.api.getDenominations()),
      firstValueFrom(this.api.getAuthorities()),
    ]);
    this.spareClasses = spareClasses;
    this.equipmentClasses = equipmentClasses;
    this.denominations = denominations;
    this.authorities = authorities;

    const initial = this.initialValue();
    if (initial) {
      // `Spare` (the read model `getSpare()` returns) carries `spareClass`/`equipmentClass`/
      // `denomination`/`authority` as human-readable NAMES for display — not the option ids
      // these dropdowns need. Spreading `initial` straight into the form (as this used to do)
      // patched those controls with names the dropdowns don't recognise, which then round-tripped
      // as literal strings like "Engine Class A" into what the backend expects to be a numeric FK
      // id, producing the "equipment_class ... nonexistent type" validation error on Save.
      // Reverse-map each by matching the loaded option lists' labels back to their ids.
      const byLabel = (options: DropdownOptionDto[], label: string): string =>
        options.find((o) => o.label === label)?.value ?? "";
      this.form.patchValue({
        ...initial,
        spareClass: byLabel(spareClasses, initial.spareClass),
        equipmentClass: byLabel(equipmentClasses, initial.equipmentClass),
        denomination: byLabel(denominations, initial.denomination),
        authority: byLabel(authorities, initial.authority),
        critical: initial.critical ? "YES" : "NO",
      });
      return;
    }

    // Match the reference defaults once the real option lists are in: Denomination "KGS",
    // Authority "Delegated Powers" — only applied when that option actually exists, so a
    // department without a KGS denomination or that authority silently keeps no default.
    const kgs = denominations.find((d) => d.label.toUpperCase() === "KGS");
    if (kgs) this.form.controls.denomination.setValue(kgs.value);
    const delegatedPowers = authorities.find((a) => a.label.toUpperCase() === "DELEGATED POWERS");
    if (delegatedPowers) this.form.controls.authority.setValue(delegatedPowers.value);
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    // InputField (type="number") is a text-backed control — coerce back to number here
    // rather than trusting the reactive form's inferred type at runtime.
    this.submitted.emit({
      ...raw,
      critical: raw.critical === "YES",
      quantityAuthorised: Number(raw.quantityAuthorised),
      quantityAvailable: Number(raw.quantityAvailable),
    });
  }

  cancel(): void {
    this.cancelled.emit();
  }
}
