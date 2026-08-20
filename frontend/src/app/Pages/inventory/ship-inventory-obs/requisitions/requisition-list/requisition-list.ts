import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { ColDef, RowData } from "ag-grid-community";
import { DataGrid } from "../../../../../shared/components/data-grid/data-grid";
import { ActionRendererComponent } from "../../../../../shared/components/data-grid/grid-action-icons";
import { GridStatusChipRenderer } from "../../../../../shared/components/data-grid/grid-status-chip-renderer";
import { ModalComponent } from "../../../../../shared/components/modal/modal.component";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { ExportKind, ExportToolbar } from "../../../../../shared/components/export-toolbar/export-toolbar";
import { ToolbarSearch } from "../../../../../shared/components/toolbar-search/toolbar-search";
import { IconComponent } from "../../../../../shared/components/icon/icon.component";
import { HelpGuidance } from "../../../shared/components/help-guidance/help-guidance";
import { PrintColumn, ReportExportService } from "../../../../../Core/services/generic-export-service/generic-export.service";
import { ObsApiService } from "../../services/obs-api.service";
import { ObsRequisitionSelectionStore } from "../../services/obs-requisition-selection-store";
import { NotificationService } from "../../../../../Core/services/notification/notification.service";
import { getErrorMessage } from "../../../../../Core/services/common/http-feedback";
import { ParentInventory, RequisitionCartType, RequisitionEntry } from "../../models/requisition.model";

type RequisitionKind = "routine" | "defect";

function printColumnFormat(field: string): ((value: unknown) => string) | undefined {
  if (field === "critical") return (v) => (v ? "YES" : "NO");
  if (field === "availableWithMo") return (v) => (v === "Available Onboard" ? "HELD" : "NOT HELD");
  return undefined;
}

const CART_TYPE_OPTIONS: { label: string; value: RequisitionCartType }[] = [
  { label: "Survey Cart", value: "Survey" },
  { label: "PTS Cart", value: "PTS" },
];

@Component({
  selector: "app-obs-requisition-list",
  standalone: true,
  imports: [ReactiveFormsModule, DataGrid, ModalComponent, SelectInput, ExportToolbar, ToolbarSearch, IconComponent, HelpGuidance],
  templateUrl: "./requisition-list.html",
  styleUrl: "./requisition-list.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RequisitionList implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  private readonly selectionStore = inject(ObsRequisitionSelectionStore);
  private readonly notifications = inject(NotificationService);
  private readonly exportService = inject(ReportExportService);

  kind: RequisitionKind = "routine";
  title = "";

  readonly cartTypeOptions = CART_TYPE_OPTIONS;
  readonly entries = signal<RequisitionEntry[]>([]);
  readonly selectedRows = signal<RequisitionEntry[]>([]);
  readonly cartModalOpen = signal(false);
  readonly cartTarget = signal<ParentInventory>("ILMS");
  readonly saving = signal(false);
  readonly exportBusy = signal<ExportKind | null>(null);
  readonly searchText = signal("");
  columnDefs: ColDef[] = [];
  printColumns: PrintColumn[] = [];
  helpHtml = "";

  readonly filteredEntries = computed(() => {
    const query = this.searchText().trim().toLowerCase();
    if (!query) return this.entries();
    return this.entries().filter((entry) =>
      [entry.patternNumber, entry.description, entry.equipmentClass, entry.category, entry.authority, entry.dartNumber]
        .some((value) => (value ?? "").toLowerCase().includes(query)),
    );
  });

  readonly cartForm = this.fb.nonNullable.group({
    cartType: ["Survey" as RequisitionCartType, Validators.required],
  });

  ngOnInit(): void {
    const data = this.route.snapshot.data as { kind: RequisitionKind; title: string };
    this.kind = data.kind;
    this.title = data.title;
    this.helpHtml =
      this.kind === "routine"
        ? `<p class="mb-0">Spares requested by maintainers for a <strong>planned routine</strong>. Tick rows and use <strong>Initiate Issue</strong> to issue them, or <strong>Send to Cart (MO/WED)</strong> to forward for replenishment.</p>`
        : `<p class="mb-2">Spares requested by maintainers against a <strong>defect</strong>. Every item needs a <strong>DART number</strong> before it can be issued — tick the rows and use <strong>Raise DART - Multiple</strong> first.</p><p class="mb-0">Once a DART number is present, tick the rows and use <strong>Initiate Issue</strong>, or <strong>Send to Cart (MO/WED)</strong> to forward for replenishment.</p>`;
    this.columnDefs = this.buildColumns();
    this.printColumns = this.columnDefs
      .filter((c): c is ColDef & { field: string } => !!c.field)
      .map((c) => ({
        header: String(c.headerName ?? c.field),
        field: c.field,
        format: printColumnFormat(c.field),
      }));
    void this.load();
  }

  private buildColumns(): ColDef[] {
    const base: ColDef[] = [
      { field: "requestedFrom", headerName: "Parent Inventory", flex: 1, filter: "agTextColumnFilter" },
      { field: "patternNumber", headerName: "Pattern Number", flex: 1, filter: "agTextColumnFilter" },
      { field: "description", headerName: "Item Description", flex: 1.3, filter: "agTextColumnFilter" },
      {
        field: "availableWithMo",
        headerName: "Onboard Availability Status",
        width: 170,
        cellRenderer: GridStatusChipRenderer,
        cellRendererParams: {
          toneMap: { "Available Onboard": "success", "Requires MO/WED": "danger" },
          labelMap: { "Available Onboard": "HELD", "Requires MO/WED": "NOT HELD" },
        },
      },
      { field: "quantityRequired", headerName: "Qty Requested By Maintainer", width: 180, filter: "agTextColumnFilter" },
      { field: "quantityAuthorised", headerName: "Qty Authorised", width: 130, filter: "agTextColumnFilter" },
      { field: "quantityAvailable", headerName: "Qty Held", width: 110, filter: "agTextColumnFilter" },
      { field: "authority", headerName: "Authority", width: 130, filter: "agTextColumnFilter" },
      { field: "equipmentClass", headerName: "Equipment Class", flex: 1, filter: "agTextColumnFilter" },
      { field: "category", headerName: "Item Category", width: 130, filter: "agTextColumnFilter" },
      {
        field: "critical",
        headerName: "Critical",
        width: 100,
        valueGetter: (p) => ((p.data as RequisitionEntry).critical ? "YES" : "NO"),
      },
    ];

    const withKindColumn: ColDef[] =
      this.kind === "routine"
        ? [
            ...base,
            { field: "routineName", headerName: "Routine Name", flex: 1, filter: "agTextColumnFilter" },
            { field: "routineNo", headerName: "Routine No", width: 120, filter: "agTextColumnFilter" },
          ]
        : [
            ...base,
            { field: "dartNumber", headerName: "DART No", width: 130, filter: "agTextColumnFilter" },
            { field: "remarks", headerName: "Remarks", flex: 1, filter: "agTextColumnFilter" },
          ];

    return [
      ...withKindColumn,
      {
        headerName: "Action",
        width: 110,
        sortable: false,
        filter: false,
        cellRenderer: ActionRendererComponent,
        cellRendererParams: {
          actions: (row: RowData) => [
            { icon: "edit", label: "Issue", color: "#1d96e9", action: () => this.issueRow(row as unknown as RequisitionEntry) },
            { icon: "delete", label: "Delete", color: "#dc2626", action: () => this.deleteRow(row as unknown as RequisitionEntry) },
          ],
        },
      },
    ];
  }

  onExport(kind: ExportKind): void {
    const rows = this.filteredEntries() as unknown as Record<string, unknown>[];
    if (kind === "excel") {
      this.exportService.downloadCsv(this.printColumns, rows, `${this.kind}-requisitions.csv`);
      return;
    }
    this.exportService.printRows(this.title, this.printColumns, rows);
  }

  copyRows(): void {
    void this.exportService.copyRows(this.printColumns, this.filteredEntries() as unknown as Record<string, unknown>[]);
    this.notifications.success("Copied to clipboard.");
  }

  private async load(): Promise<void> {
    const entries =
      this.kind === "routine"
        ? await firstValueFrom(this.api.getRoutineRequisitions())
        : await firstValueFrom(this.api.getDefectRequisitions());
    this.entries.set(entries);
  }

  onSelectionChanged(rows: RowData[]): void {
    this.selectedRows.set(rows as unknown as RequisitionEntry[]);
  }

  get canIssue(): boolean {
    if (this.kind === "routine") return this.selectedRows().length > 0;
    // Defect items need a DART number before they can be issued.
    return this.selectedRows().length > 0 && this.selectedRows().every((r) => !!r.dartNumber);
  }

  async raiseDart(): Promise<void> {
    if (!this.selectedRows().length) return;
    try {
      await firstValueFrom(
        this.api.raiseDartForDefectRequisitions(this.selectedRows().map((r) => r.id)),
      );
      void this.load();
    } catch (error) {
      // `raiseDartForDefectRequisitions` is a client-side stub (no backend endpoint yet) — it
      // never reaches the HTTP interceptor, so this is the only feedback surface for it.
      this.notifications.error(getErrorMessage(error));
    }
  }

  initiateIssue(): void {
    if (!this.selectedRows().length) return;
    this.selectionStore.setSelection(this.selectedRows());
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/requisitions", this.kind, "issue"]);
  }

  issueRow(entry: RequisitionEntry): void {
    this.selectionStore.setSelection([entry]);
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/requisitions", this.kind, "issue"]);
  }

  async deleteRow(entry: RequisitionEntry): Promise<void> {
    if (!confirm(`Delete requisition for "${entry.patternNumber}"?`)) return;
    try {
      await firstValueFrom(this.api.deleteRequisition(this.kind, entry.id));
      void this.load();
    } catch {
      // Real HTTP call — the interceptor already raises the error toast for it.
    }
  }

  openCartModal(target: ParentInventory): void {
    if (!this.selectedRows().length) return;
    this.cartTarget.set(target);
    this.cartModalOpen.set(true);
  }

  closeCartModal(): void {
    this.cartModalOpen.set(false);
  }

  async confirmSendToCart(): Promise<void> {
    this.saving.set(true);
    try {
      const raw = this.cartForm.getRawValue();
      await firstValueFrom(
        this.api.sendRequisitionsToCart(this.kind, {
          ids: this.selectedRows().map((r) => r.id),
          parentInventory: this.cartTarget(),
          ...raw,
        }),
      );
      this.closeCartModal();
      void this.load();
    } catch (error) {
      // `sendRequisitionsToCart` is a client-side stub (no backend endpoint yet) — it never
      // reaches the HTTP interceptor, so this is the only feedback surface for it.
      this.notifications.error(getErrorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }
}
