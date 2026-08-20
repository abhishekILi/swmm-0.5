import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { SpareForm } from "../../components/spare-form/spare-form";
import { ObsApiService } from "../../services/obs-api.service";
import { Spare, SpareFormPayload } from "../../models/spare.model";

@Component({
  selector: "app-obs-spare-edit",
  standalone: true,
  imports: [SpareForm],
  templateUrl: "./spare-edit.html",
  styleUrl: "./spare-edit.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpareEdit implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  private spareId = "";
  readonly spare = signal<Spare | null>(null);
  readonly saving = signal(false);

  ngOnInit(): void {
    this.spareId = this.route.snapshot.paramMap.get("id") ?? "";
    void this.load();
  }

  private async load(): Promise<void> {
    const spare = await firstValueFrom(this.api.getSpare(this.spareId));
    this.spare.set(spare);
  }

  async onSubmit(payload: SpareFormPayload): Promise<void> {
    this.saving.set(true);
    try {
      await firstValueFrom(this.api.updateSpare(this.spareId, payload));
      this.goBack();
    } finally {
      this.saving.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search"]);
  }
}
