import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ColDef, RowData } from "ag-grid-community";
import { firstValueFrom } from "rxjs";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { HelpGuidance } from "../../shared/components/help-guidance/help-guidance";
import { NotificationService } from "../../../../Core/services/notification/notification.service";
import { MoApiService } from "../services/mo-api.service";
import { ApprovalEntry } from "../models/mo.model";

@Component({
  selector: "app-mo-approval",
  standalone: true,
  imports: [DataGrid, HelpGuidance],
  templateUrl: "./approval.html",
  styleUrl: "./approval.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Approval implements OnInit {
  private readonly api = inject(MoApiService);
  private readonly notifications = inject(NotificationService);

  readonly entries = signal<ApprovalEntry[]>([]);
  readonly selectedRows = signal<ApprovalEntry[]>([]);
  readonly sending = signal(false);

  readonly columnDefs: ColDef[] = [
    { field: "spareCartName", headerName: "Spare Cart Name", flex: 1 },
    { field: "patternNo", headerName: "Pattern No", flex: 1 },
    { field: "spareDescription", headerName: "Spare Description", flex: 1.4 },
    { field: "dartNo", headerName: "Dart No", width: 120 },
    { field: "equipmentClass", headerName: "Equipment Class", flex: 1 },
    { field: "category", headerName: "Category", width: 100 },
    {
      field: "critical",
      headerName: "Critical",
      width: 100,
      valueGetter: (p) => ((p.data as ApprovalEntry).critical ? "YES" : "NO"),
    },
    { field: "qty", headerName: "Qty", width: 90 },
  ];

  ngOnInit(): void {
    void this.load();
  }

  private async load(): Promise<void> {
    this.entries.set(await firstValueFrom(this.api.getApprovalList()));
  }

  onSelectionChanged(rows: RowData[]): void {
    this.selectedRows.set(rows as unknown as ApprovalEntry[]);
  }

  async sendToIlms(): Promise<void> {
    if (!this.selectedRows().length) return;
    this.sending.set(true);
    try {
      await firstValueFrom(this.api.sendApprovalsToIlms(this.selectedRows().map((e) => e.id)));
      this.notifications.success("Sent to ILMS.");
      void this.load();
    } finally {
      this.sending.set(false);
    }
  }
}
