import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormBuilder, ReactiveFormsModule } from "@angular/forms";
import { Router } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { ColDef, RowData } from "ag-grid-community";
import { DataGrid } from "../../../../../shared/components/data-grid/data-grid";
import { ActionRendererComponent } from "../../../../../shared/components/data-grid/grid-action-icons";
import { DetailDrawer } from "../../../../../shared/components/detail-drawer/detail-drawer";
import { IconComponent } from "../../../../../shared/components/icon/icon.component";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { ToolbarSearch } from "../../../../../shared/components/toolbar-search/toolbar-search";
import { HelpGuidance } from "../../../shared/components/help-guidance/help-guidance";
import {
  PrintColumn,
  ReportExportService,
} from "../../../../../Core/services/generic-export-service/generic-export.service";
import { NotificationService } from "../../../../../Core/services/notification/notification.service";
import { ObsApiService } from "../../services/obs-api.service";
import { ObsSelectionStore } from "../../services/obs-selection-store";
import { DropdownOptionDto, SPARE_CATEGORY_LABEL, Spare } from "../../models/spare.model";

const HELP_HTML = `
  <h6 class="fw-bold mb-1">What this page is for</h6>
  <p class="mb-2">Find spares held in your ship's store. Use the filters to shrink the
     list, then click a row to see its full details on the right.</p>
  <h6 class="fw-bold mb-1">Important to remember</h6>
  <ul class="mb-2">
    <li>You see only your own department's spares — SWMM does not show one department's spares to another.</li>
    <li>Always <strong>issue</strong> a spare in SWMM whenever you take it out of its SPTA box or stowed location, so SWMM can track and plan its replenishment.</li>
    <li>Click any row to open a spare's <strong>detail view</strong>, where you can also add or change its photo.</li>
  </ul>
  <h6 class="fw-bold mb-1">How to filter</h6>
  <ul class="mb-2">
    <li><strong>Spare Type</strong> and <strong>Class of Spares</strong> — pick these to narrow the list to the kind of spare you want.</li>
    <li><strong>Clear</strong> — empties the filters and shows the full list again.</li>
  </ul>
  <h6 class="fw-bold mb-1">What the columns mean</h6>
  <ul class="mb-2">
    <li><strong>Pattern Number</strong> — the spare's unique ID.</li>
    <li><strong>Category</strong> — P = Permanent, R = Returnable, C = Consumable.</li>
    <li><strong>Qty Authorised</strong> vs <strong>Qty Available</strong> — how many you are allowed to hold vs how many are on board right now.</li>
    <li><strong>Critical</strong> — marks a spare the ship cannot do without.</li>
    <li><strong>Authority</strong> — the scale the holding is based on (e.g. D787J).</li>
    <li><strong>Location</strong> — where the spare is stowed on board.</li>
  </ul>
  <h6 class="fw-bold mb-1">Buttons</h6>
  <ul class="mb-0">
    <li><strong>Add Spare</strong> — register a brand-new spare in the store.</li>
    <li><strong>Issue Multiple Spares</strong> — tick the boxes on several rows, then use this to issue them all together.</li>
    <li>Click any row to open the <strong>Spare Detail</strong> panel (stock, onboard location, box/rack).</li>
  </ul>
`;

const PRINT_COLUMNS: PrintColumn[] = [
  { header: "Pattern Number", field: "patternNumber" },
  { header: "Equipment Class", field: "equipmentClass" },
  { header: "Description", field: "description" },
  { header: "Category", field: "category", format: (v) => SPARE_CATEGORY_LABEL[v as Spare["category"]] ?? "" },
  { header: "Denomination", field: "denomination" },
  { header: "Qty Authorised", field: "quantityAuthorised" },
  { header: "Qty Held", field: "quantityAvailable" },
  { header: "Critical", field: "critical", format: (v) => (v ? "YES" : "NO") },
  { header: "Authority", field: "authority" },
  { header: "Location", field: "location" },
];

@Component({
  selector: "app-obs-item-search",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    DataGrid,
    DetailDrawer,
    IconComponent,
    SelectInput,
    ToolbarSearch,
    HelpGuidance,
  ],
  templateUrl: "./item-search.html",
  styleUrl: "./item-search.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ItemSearch implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly router = inject(Router);
  private readonly selectionStore = inject(ObsSelectionStore);
  private readonly fb = inject(FormBuilder);
  private readonly exportService = inject(ReportExportService);
  private readonly notifications = inject(NotificationService);

  readonly helpHtml = HELP_HTML;
  readonly spareClasses = signal<DropdownOptionDto[]>([]);
  readonly equipmentClasses = signal<DropdownOptionDto[]>([]);
  readonly spares = signal<Spare[]>([]);
  readonly selectedRows = signal<Spare[]>([]);
  readonly drawerSpare = signal<Spare | null>(null);

  readonly filtersForm = this.fb.nonNullable.group({
    spareClass: "",
    equipmentClass: "",
    q: "",
  });

  readonly columnDefs: ColDef[] = [
    { field: "patternNumber", headerName: "Pattern Number", flex: 1 },
    { field: "equipmentClass", headerName: "Equipment Class", flex: 1.4 },
    { field: "description", headerName: "Spare Description", flex: 1.4 },
    {
      field: "category",
      headerName: "Category",
      width: 110,
      valueGetter: (p) => SPARE_CATEGORY_LABEL[(p.data as Spare).category],
    },
    { field: "denomination", headerName: "Denomination", width: 130 },
    { field: "quantityAuthorised", headerName: "Qty Authorised", width: 130 },
    { field: "quantityAvailable", headerName: "Qty Held", width: 110 },
    {
      field: "critical",
      headerName: "Critical",
      width: 100,
      valueGetter: (p) => ((p.data as Spare).critical ? "YES" : "NO"),
    },
    { field: "authority", headerName: "Authority", width: 120 },
    { field: "location", headerName: "Location", width: 110 },
    {
      headerName: "Actions",
      width: 110,
      sortable: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: RowData) => [
          { icon: "view", label: "View", action: () => this.viewSpare(row as unknown as Spare) },
          { icon: "edit", label: "Issue", action: () => this.issueSpare(row as unknown as Spare) },
        ],
      },
    },
  ];

  ngOnInit(): void {
    void this.loadDropdowns();
    void this.search();
  }

  private async loadDropdowns(): Promise<void> {
    const [spareClasses, equipmentClasses] = await Promise.all([
      firstValueFrom(this.api.getSpareClasses()),
      firstValueFrom(this.api.getEquipmentClasses()),
    ]);
    this.spareClasses.set(spareClasses);
    this.equipmentClasses.set(equipmentClasses);
  }

  private currentFilters() {
    const raw = this.filtersForm.getRawValue();
    return {
      spareClass: raw.spareClass || undefined,
      equipmentClass: raw.equipmentClass || undefined,
      q: raw.q || undefined,
    };
  }

  async search(): Promise<void> {
    const results = await firstValueFrom(this.api.searchSpares(this.currentFilters()));
    this.spares.set(results);
  }

  onGlobalSearchChange(value: string): void {
    this.filtersForm.controls.q.setValue(value);
    void this.search();
  }

  clearFilters(): void {
    this.filtersForm.reset({ spareClass: "", equipmentClass: "", q: "" });
    void this.search();
  }

  printGrid(): void {
    const rows = this.spares();
    const win = this.exportService.openLoadingWindow("Search Spare", PRINT_COLUMNS.length, rows.length);
    if (!win) return;
    this.exportService.renderPreviewWindow(win, "Search Spare", PRINT_COLUMNS, rows as unknown as Record<string, unknown>[], {
      print: true,
    });
  }

  async exportExcel(): Promise<void> {
    try {
      const blob = await firstValueFrom(this.api.exportSparesExcel(this.currentFilters()));
      this.exportService.downloadBlob(blob, "spares_export.xlsx");
    } catch {
      this.notifications.error("Failed to export spares to Excel.");
    }
  }

  copyRows(): void {
    void this.exportService.copyRows(PRINT_COLUMNS, this.spares() as unknown as Record<string, unknown>[]);
  }

  onSelectionChanged(rows: RowData[]): void {
    this.selectedRows.set(rows as unknown as Spare[]);
  }

  onRowClicked(row: RowData): void {
    this.drawerSpare.set(row as unknown as Spare);
  }

  closeDrawer(): void {
    this.drawerSpare.set(null);
  }

  addSpare(): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search/add"]);
  }

  viewSpare(spare: Spare): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search", spare.id]);
  }

  issueSpare(spare: Spare): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search", spare.id, "issue"]);
  }

  issueMultiple(): void {
    if (!this.selectedRows().length) return;
    this.selectionStore.setSelection(this.selectedRows());
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search/issue-multiple"]);
  }
}
