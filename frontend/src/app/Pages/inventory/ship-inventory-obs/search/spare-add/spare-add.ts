import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { SpareForm } from "../../components/spare-form/spare-form";
import { ObsApiService } from "../../services/obs-api.service";
import { SpareFormPayload } from "../../models/spare.model";

@Component({
  selector: "app-obs-spare-add",
  standalone: true,
  imports: [SpareForm],
  templateUrl: "./spare-add.html",
  styleUrl: "./spare-add.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpareAdd {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);

  readonly saving = signal(false);

  async onSubmit(payload: SpareFormPayload): Promise<void> {
    this.saving.set(true);
    try {
      await firstValueFrom(this.api.addSpare(payload));
      this.goBack();
    } finally {
      this.saving.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search"]);
  }
}
