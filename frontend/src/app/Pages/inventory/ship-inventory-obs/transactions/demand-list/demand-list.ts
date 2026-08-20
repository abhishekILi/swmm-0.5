import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { ColDef, RowData } from "ag-grid-community";
import { DataGrid } from "../../../../../shared/components/data-grid/data-grid";
import { ModalComponent } from "../../../../../shared/components/modal/modal.component";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { ExportKind, ExportToolbar } from "../../../../../shared/components/export-toolbar/export-toolbar";
import { ToolbarSearch } from "../../../../../shared/components/toolbar-search/toolbar-search";
import { IconComponent } from "../../../../../shared/components/icon/icon.component";
import { HelpGuidance } from "../../../shared/components/help-guidance/help-guidance";
import { PrintColumn, ReportExportService } from "../../../../../Core/services/generic-export-service/generic-export.service";
import { ObsApiService } from "../../services/obs-api.service";
import { NotificationService } from "../../../../../Core/services/notification/notification.service";
import { getErrorMessage } from "../../../../../Core/services/common/http-feedback";
import { ParentInventory } from "../../models/requisition.model";
import { DemandEntry } from "../../models/transaction.model";

const PARENT_INVENTORY_OPTIONS: { label: string; value: ParentInventory }[] = [
  { label: "ILMS (MO)", value: "ILMS" },
  { label: "WLMS (WED)", value: "WLMS" },
];

type SpareCategoryFilter = "PERMANENT" | "RETURNABLE" | "CONSUMABLE";
const CATEGORY_FILTER_OPTIONS: { key: SpareCategoryFilter; label: string }[] = [
  { key: "PERMANENT", label: "Permanent" },
  { key: "RETURNABLE", label: "Returnable" },
  { key: "CONSUMABLE", label: "Consumable" },
];

const HELP_HTML = `
  <h6 class="fw-bold mb-1">What this page is for</h6>
  <p class="mb-2">Only <strong>Consumable (C)</strong> items that you have issued are listed here —
     temporarily — as a reminder that they need to be demanded at harbour through ILMS / WLMS. To do
     that, move them to the Demand cart in the MO Inventory / WED Inventory module first, which then
     sends the information to ILMS/WLMS over the API.</p>
  <h6 class="fw-bold mb-1">Permanent & Returnable items do not appear here</h6>
  <p class="mb-2">P/R items never enter this internal cart. After their survey number is received back
     from ILMS/WLMS (as per the type of spare), they show up in the Demand cart inside the MO Inventory
     / WED Inventory module instead.</p>
  <h6 class="fw-bold mb-1">Before you can forward an item</h6>
  <p class="mb-2">Every item needs a <strong>DART number</strong> — no DART, it cannot move. Tick the
     rows and use <strong>Raise DART – Multiple</strong> to raise DARTs for the selected items.</p>
  <h6 class="fw-bold mb-1">Sending to MO / WED</h6>
  <p class="mb-2">Tick the rows and use <strong>Send to Cart (MO/WED) – Multiple</strong>. In the pop-up
     pick the Parent Inventory — ILMS (MO) or WLMS (WED). The item then moves to that module's Demand
     cart, and the demand is raised over the API.</p>
  <h6 class="fw-bold mb-1">What the columns mean</h6>
  <ul class="mb-0">
    <li><strong>Parent Inventory</strong> — which MO/WED system the item is routed to.</li>
    <li><strong>INcatting status</strong> — whether the item is catalogued.</li>
    <li><strong>DART No</strong> — the item's DART; must be present to move on.</li>
    <li><strong>Authority</strong> — the scale the item is held on (e.g. D787J).</li>
  </ul>
`;

@Component({
  selector: "app-obs-demand-list",
  standalone: true,
  imports: [ReactiveFormsModule, DataGrid, ModalComponent, SelectInput, ExportToolbar, ToolbarSearch, IconComponent, HelpGuidance],
  templateUrl: "./demand-list.html",
  styleUrl: "./demand-list.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DemandList implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly notifications = inject(NotificationService);
  private readonly exportService = inject(ReportExportService);

  readonly helpHtml = HELP_HTML;
  readonly parentInventoryOptions = PARENT_INVENTORY_OPTIONS;
  readonly categoryFilterOptions = CATEGORY_FILTER_OPTIONS;
  readonly entries = signal<DemandEntry[]>([]);
  readonly selectedRows = signal<DemandEntry[]>([]);
  readonly cartModalOpen = signal(false);
  readonly saving = signal(false);
  readonly exportBusy = signal<ExportKind | null>(null);
  readonly searchText = signal("");
  readonly criticalOnly = signal(false);
  readonly notIncattedOnly = signal(false);
  readonly categoryFilters = signal<Record<SpareCategoryFilter, boolean>>({
    PERMANENT: true,
    RETURNABLE: true,
    CONSUMABLE: true,
  });

  readonly columnDefs: ColDef[] = [
    { field: "parentInventory", headerName: "Parent Inventory", width: 140 },
    { field: "incattingStatus", headerName: "INcatting Status", width: 140 },
    { field: "patternNumber", headerName: "Pattern Number", flex: 1 },
    { field: "dartNumber", headerName: "DART No", width: 130 },
    { field: "description", headerName: "Spare Description", flex: 1.2 },
    { field: "quantity", headerName: "Qty", width: 90 },
    { field: "category", headerName: "Category", width: 100 },
    { field: "equipmentClass", headerName: "Equipment Class", flex: 1 },
    {
      field: "critical",
      headerName: "Critical",
      width: 100,
      valueGetter: (p) => ((p.data as DemandEntry).critical ? "YES" : "NO"),
    },
    { field: "authority", headerName: "Authority", width: 110 },
    {
      headerName: "Actions",
      width: 150,
      sortable: false,
      valueGetter: () => "Click row for details",
    },
  ];

  readonly printColumns: PrintColumn[] = this.columnDefs
    .filter((c): c is ColDef & { field: string } => !!c.field)
    .map((c) => ({
      header: String(c.headerName ?? c.field),
      field: c.field,
      format: c.field === "critical" ? (v: unknown) => (v ? "YES" : "NO") : undefined,
    }));

  readonly filteredEntries = computed(() => {
    const critical = this.criticalOnly();
    const notIncatted = this.notIncattedOnly();
    const categories = this.categoryFilters();
    const query = this.searchText().trim().toLowerCase();
    return this.entries().filter((entry) => {
      if (critical && !entry.critical) return false;
      if (notIncatted && entry.incattingStatus !== "IIF") return false;
      const categoryKey = entry.category?.toUpperCase() as SpareCategoryFilter | undefined;
      if (categoryKey && categoryKey in categories && !categories[categoryKey]) return false;
      if (
        query &&
        ![entry.patternNumber, entry.description, entry.dartNumber, entry.authority, entry.equipmentClass].some((value) =>
          (value ?? "").toLowerCase().includes(query),
        )
      ) {
        return false;
      }
      return true;
    });
  });

  readonly cartForm = this.fb.nonNullable.group({
    parentInventory: ["ILMS" as ParentInventory, Validators.required],
  });

  ngOnInit(): void {
    void this.load();
  }

  private async load(): Promise<void> {
    this.entries.set(await firstValueFrom(this.api.getDemandList()));
  }

  toggleCategory(key: SpareCategoryFilter): void {
    this.categoryFilters.update((current) => ({ ...current, [key]: !current[key] }));
  }

  onExport(kind: ExportKind): void {
    const rows = this.filteredEntries() as unknown as Record<string, unknown>[];
    if (kind === "excel") {
      this.exportService.downloadCsv(this.printColumns, rows, "demand-list.csv");
      return;
    }
    this.exportService.printRows("Results - To Be Demanded", this.printColumns, rows);
  }

  copyRows(): void {
    void this.exportService.copyRows(this.printColumns, this.filteredEntries() as unknown as Record<string, unknown>[]);
    this.notifications.success("Copied to clipboard.");
  }

  onSelectionChanged(rows: RowData[]): void {
    this.selectedRows.set(rows as unknown as DemandEntry[]);
  }

  onRowClicked(row: RowData): void {
    const entry = row as unknown as DemandEntry;
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/transactions/demand", entry.id]);
  }

  async raiseDart(): Promise<void> {
    if (!this.selectedRows().length) return;
    try {
      await firstValueFrom(this.api.raiseDartForDemand(this.selectedRows().map((r) => r.id)));
      void this.load();
    } catch (error) {
      // `raiseDartForDemand` is a client-side stub (no backend endpoint yet) — it never reaches
      // the HTTP interceptor, so this is the only feedback surface for it.
      this.notifications.error(getErrorMessage(error));
    }
  }

  get canSendToCart(): boolean {
    return this.selectedRows().length > 0 && this.selectedRows().every((r) => !!r.dartNumber);
  }

  openCartModal(): void {
    if (!this.canSendToCart) return;
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
        this.api.sendDemandToCart({ ids: this.selectedRows().map((r) => r.id), cartType: "Survey", ...raw }),
      );
      this.closeCartModal();
      void this.load();
    } catch (error) {
      // `sendDemandToCart` is a client-side stub (no backend endpoint yet) — it never reaches
      // the HTTP interceptor, so this is the only feedback surface for it.
      this.notifications.error(getErrorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }
}
