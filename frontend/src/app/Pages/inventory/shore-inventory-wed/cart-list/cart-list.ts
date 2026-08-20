import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ActivatedRoute } from "@angular/router";
import { ColDef, RowData } from "ag-grid-community";
import { firstValueFrom } from "rxjs";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { HelpGuidance } from "../../shared/components/help-guidance/help-guidance";
import { NotificationService } from "../../../../Core/services/notification/notification.service";
import { WedApiService, WedCartKind } from "../services/wed-api.service";
import { WedCartEntry } from "../models/wed.model";

interface CartListRouteData {
  kind: WedCartKind;
  title: string;
  columns: ColDef[];
  showCheckboxes?: boolean;
  showApprovalButton?: boolean;
  showSyncButton?: boolean;
  syncButtonLabel?: string;
  showRaiseButton?: boolean;
  raiseButtonLabel?: string;
}

/**
 * Generic list+actions component reused for all 6 "Spares Transaction Cart"
 * pages (Survey/PTS/Demand/Receive/IIF/PTS-RIO-Pending) — same pattern as
 * Shore Inventory - MO's CartList, parametrized entirely via route data.
 */
@Component({
  selector: "app-wed-cart-list",
  standalone: true,
  imports: [DataGrid, HelpGuidance],
  templateUrl: "./cart-list.html",
  styleUrl: "./cart-list.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CartList implements OnInit {
  private readonly api = inject(WedApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);

  private kind: WedCartKind = "survey";
  title = "";
  columnDefs: ColDef[] = [];
  showCheckboxes = true;
  showApprovalButton = true;
  showSyncButton = false;
  syncButtonLabel = "Sync With WLMS";
  showRaiseButton = false;
  raiseButtonLabel = "Raise IIF";

  readonly entries = signal<WedCartEntry[]>([]);
  readonly selectedRows = signal<WedCartEntry[]>([]);
  readonly syncing = signal(false);
  readonly sending = signal(false);
  readonly raising = signal(false);

  ngOnInit(): void {
    const data = this.route.snapshot.data as CartListRouteData;
    this.kind = data.kind;
    this.title = data.title;
    this.columnDefs = data.columns;
    this.showCheckboxes = data.showCheckboxes ?? true;
    this.showApprovalButton = data.showApprovalButton ?? true;
    this.showSyncButton = data.showSyncButton ?? false;
    this.syncButtonLabel = data.syncButtonLabel ?? "Sync With WLMS";
    this.showRaiseButton = data.showRaiseButton ?? false;
    this.raiseButtonLabel = data.raiseButtonLabel ?? "Raise IIF";
    void this.load();
  }

  private async load(): Promise<void> {
    this.entries.set(await firstValueFrom(this.api.getCart(this.kind)));
  }

  onSelectionChanged(rows: RowData[]): void {
    this.selectedRows.set(rows as unknown as WedCartEntry[]);
  }

  async sendForHodApproval(): Promise<void> {
    if (!this.selectedRows().length) return;
    this.sending.set(true);
    try {
      await firstValueFrom(
        this.api.sendCartForHodApproval(this.kind, this.selectedRows().map((e) => e.id)),
      );
      this.notifications.success("Sent for HOD approval.");
      void this.load();
    } finally {
      this.sending.set(false);
    }
  }

  async sync(): Promise<void> {
    this.syncing.set(true);
    try {
      const result = await firstValueFrom(this.api.syncCartWithWlms(this.kind));
      this.notifications.success(result.updated ? `Sync complete — ${result.updated} record(s) synced.` : result.message);
      void this.load();
    } finally {
      this.syncing.set(false);
    }
  }

  async raise(): Promise<void> {
    this.raising.set(true);
    try {
      await firstValueFrom(this.api.raiseIif(this.kind, this.selectedRows().map((e) => e.id)));
      this.notifications.success("IIF raised.");
    } finally {
      this.raising.set(false);
    }
  }
}
