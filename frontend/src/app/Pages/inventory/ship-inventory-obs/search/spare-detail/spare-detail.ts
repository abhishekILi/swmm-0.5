import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { IconComponent } from "../../../../../shared/components/icon/icon.component";
import { ObsApiService } from "../../services/obs-api.service";
import { SPARE_CATEGORY_LABEL, Spare } from "../../models/spare.model";

@Component({
  selector: "app-obs-spare-detail",
  standalone: true,
  imports: [IconComponent],
  templateUrl: "./spare-detail.html",
  styleUrl: "./spare-detail.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpareDetail implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly categoryLabel = SPARE_CATEGORY_LABEL;
  readonly spare = signal<Spare | null>(null);
  private spareId = "";

  ngOnInit(): void {
    this.spareId = this.route.snapshot.paramMap.get("id") ?? "";
    void this.load();
  }

  private async load(): Promise<void> {
    const spare = await firstValueFrom(this.api.getSpare(this.spareId));
    this.spare.set(spare);
  }

  print(): void {
    window.print();
  }

  goBack(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search"]);
  }

  edit(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search", this.spareId, "edit"]);
  }

  issue(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search", this.spareId, "issue"]);
  }
}
