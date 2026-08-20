import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { FormBuilder, ReactiveFormsModule } from "@angular/forms";
import { ColDef } from "ag-grid-community";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { SelectInput } from "../../../../shared/components/select-input/select-input";
import { HelpGuidance } from "../../shared/components/help-guidance/help-guidance";
import { NotificationService } from "../../../../Core/services/notification/notification.service";

type MastersTab = "mapping" | "get-data";

interface MappedRow {
  vendorCode: string;
  vendorName: string;
  itemCode: string;
  itemDescription: string;
  insmaEquipment: string;
}

@Component({
  selector: "app-mo-masters",
  standalone: true,
  imports: [ReactiveFormsModule, DataGrid, SelectInput, HelpGuidance],
  templateUrl: "./mo-masters.html",
  styleUrl: "./mo-masters.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MoMasters {
  private readonly fb = inject(FormBuilder);
  private readonly notifications = inject(NotificationService);

  readonly activeTab = signal<MastersTab>("mapping");
  readonly mapForm = this.fb.nonNullable.group({ vendorCode: "", equipmentName: "" });
  readonly syncing = signal(false);

  readonly mappedRows = signal<MappedRow[]>([]);
  readonly columnDefs: ColDef[] = [
    { field: "vendorCode", headerName: "Vendor Code", flex: 1 },
    { field: "vendorName", headerName: "Vendor Name", flex: 1.2 },
    { field: "itemCode", headerName: "Item Code", flex: 1 },
    { field: "itemDescription", headerName: "Item Description", flex: 1.4 },
    { field: "insmaEquipment", headerName: "INSMA Equipment", flex: 1 },
  ];

  selectTab(tab: MastersTab): void {
    this.activeTab.set(tab);
  }

  submitMap(): void {
    this.notifications.success("Mapping saved.");
  }

  async getDataFromMo(): Promise<void> {
    this.syncing.set(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 400));
      this.notifications.success("Data fetched from MO.");
    } finally {
      this.syncing.set(false);
    }
  }
}
