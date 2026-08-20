import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { FormBuilder, ReactiveFormsModule } from "@angular/forms";
import { ColDef } from "ag-grid-community";
import { firstValueFrom } from "rxjs";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { SelectInput } from "../../../../shared/components/select-input/select-input";
import { HelpGuidance } from "../../shared/components/help-guidance/help-guidance";
import { NotificationService } from "../../../../Core/services/notification/notification.service";
import { WedApiService } from "../services/wed-api.service";

type MastersTab = "mapping" | "get-data";

interface MappedRow {
  insmaEquipmentName: string;
  wedEquipmentName: string;
  wedItemCode: string;
  createdAt: string;
}

@Component({
  selector: "app-wed-masters",
  standalone: true,
  imports: [ReactiveFormsModule, DataGrid, SelectInput, HelpGuidance],
  templateUrl: "./wed-masters.html",
  styleUrl: "./wed-masters.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WedMasters {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(WedApiService);
  private readonly notifications = inject(NotificationService);

  readonly activeTab = signal<MastersTab>("mapping");
  readonly mapForm = this.fb.nonNullable.group({ equipmentName: "", equipmentClass: "" });

  readonly syncingEquipment = signal(false);
  readonly syncingSpares = signal(false);

  readonly mappedRows = signal<MappedRow[]>([]);
  readonly columnDefs: ColDef[] = [
    { field: "insmaEquipmentName", headerName: "INSMA Equipment Name", flex: 1.2 },
    { field: "wedEquipmentName", headerName: "WED Equipment Name", flex: 1.2 },
    { field: "wedItemCode", headerName: "WED Item Code", flex: 1 },
    { field: "createdAt", headerName: "Created At", width: 160 },
  ];

  selectTab(tab: MastersTab): void {
    this.activeTab.set(tab);
  }

  submitMap(): void {
    this.notifications.success("Mapping saved.");
  }

  async syncEquipment(): Promise<void> {
    this.syncingEquipment.set(true);
    try {
      const result = await firstValueFrom(this.api.syncEquipmentFromWed());
      this.notifications.success(
        result.created || result.updated
          ? `Equipment synced. Created: ${result.created}, Updated: ${result.updated}.`
          : result.message,
      );
    } finally {
      this.syncingEquipment.set(false);
    }
  }

  async syncSpares(): Promise<void> {
    this.syncingSpares.set(true);
    try {
      const result = await firstValueFrom(this.api.syncSparesFromWed());
      this.notifications.success(
        result.created || result.updated
          ? `Spares synced. Created: ${result.created}, Updated: ${result.updated}.`
          : result.message,
      );
    } finally {
      this.syncingSpares.set(false);
    }
  }
}
