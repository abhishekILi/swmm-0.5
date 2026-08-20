import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { ColDef, RowData } from "ag-grid-community";
import { DataGrid } from "../../../../../shared/components/data-grid/data-grid";
import { ActionRendererComponent } from "../../../../../shared/components/data-grid/grid-action-icons";
import { ToolbarSearch } from "../../../../../shared/components/toolbar-search/toolbar-search";
import { ExportKind, ExportToolbar } from "../../../../../shared/components/export-toolbar/export-toolbar";
import { IconComponent } from "../../../../../shared/components/icon/icon.component";
import { HelpGuidance } from "../../../shared/components/help-guidance/help-guidance";
import { PrintColumn, ReportExportService } from "../../../../../Core/services/generic-export-service/generic-export.service";
import { ObsApiService } from "../../services/obs-api.service";
import { SPARE_CATEGORY_LABEL, Spare } from "../../models/spare.model";

export type SpareStatusKind = "less-than-50" | "d787j-deficiency" | "critical";

interface SpareStatusRouteData {
  kind: SpareStatusKind;
  title: string;
  helpHtml?: string;
}

const COLUMNS: ColDef[] = [
  { field: "patternNumber", headerName: "Pattern Number", flex: 1, filter: "agTextColumnFilter", floatingFilter: true },
  { field: "description", headerName: "Spare Description", flex: 1.4, filter: "agTextColumnFilter", floatingFilter: true },
  {
    field: "category",
    headerName: "Category",
    width: 110,
    filter: "agTextColumnFilter",
    floatingFilter: true,
    valueGetter: (p) => SPARE_CATEGORY_LABEL[(p.data as Spare).category],
  },
  { field: "quantityAuthorised", headerName: "Qty Authorised", width: 130, filter: "agTextColumnFilter", floatingFilter: true },
  { field: "quantityAvailable", headerName: "Qty Held", width: 110, filter: "agTextColumnFilter", floatingFilter: true },
  {
    field: "critical",
    headerName: "Critical",
    width: 100,
    filter: "agTextColumnFilter",
    floatingFilter: true,
    valueGetter: (p) => ((p.data as Spare).critical ? "YES" : "NO"),
  },
  { field: "authority", headerName: "Authority", width: 120, filter: "agTextColumnFilter", floatingFilter: true },
  { field: "equipmentClass", headerName: "Equipment Class", flex: 1, filter: "agTextColumnFilter", floatingFilter: true },
  { field: "spareClass", headerName: "Spare Class", flex: 1, filter: "agTextColumnFilter", floatingFilter: true },
];

const PRINT_COLUMNS: PrintColumn[] = [
  { header: "Pattern Number", field: "patternNumber" },
  { header: "Spare Description", field: "description" },
  { header: "Category", field: "category", format: (v) => SPARE_CATEGORY_LABEL[v as Spare["category"]] ?? "" },
  { header: "Qty Authorised", field: "quantityAuthorised" },
  { header: "Qty Held", field: "quantityAvailable" },
  { header: "Critical", field: "critical", format: (v) => (v ? "YES" : "NO") },
  { header: "Authority", field: "authority" },
  { header: "Equipment Class", field: "equipmentClass" },
  { header: "Spare Class", field: "spareClass" },
];

/**
 * Generic list reused for the 3 Spare-based dashboard "View more" drill-downs
 * (Spares < 50% in Inventory, D787J Deficiency, Critical Spare List) — same
 * column set as Item Search, parametrized entirely via route data. Critical
 * Spare List additionally gets Spare Class / Equipment Class filters, matching
 * its reference design.
 */
@Component({
  selector: "app-obs-spare-status-list",
  standalone: true,
  imports: [DataGrid, ToolbarSearch, ExportToolbar, IconComponent, HelpGuidance],
  templateUrl: "./spare-status-list.html",
  styleUrl: "./spare-status-list.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpareStatusList implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly exportService = inject(ReportExportService);

  title = "";
  helpHtml = "";
  kind: SpareStatusKind = "less-than-50";
  readonly spares = signal<Spare[]>([]);
  readonly searchText = signal("");
  readonly spareClassFilter = signal("");
  readonly equipmentClassFilter = signal("");
  readonly exportBusy = signal<ExportKind | null>(null);

  readonly spareClassOptions = computed(() => [...new Set(this.spares().map((s) => s.spareClass))].filter(Boolean).sort());
  readonly equipmentClassOptions = computed(() =>
    [...new Set(this.spares().map((s) => s.equipmentClass))].filter(Boolean).sort(),
  );

  readonly filteredSpares = computed(() => {
    const query = this.searchText().trim().toLowerCase();
    const spareClass = this.spareClassFilter();
    const equipmentClass = this.equipmentClassFilter();
    return this.spares().filter((s) => {
      if (spareClass && s.spareClass !== spareClass) return false;
      if (equipmentClass && s.equipmentClass !== equipmentClass) return false;
      if (query && ![s.patternNumber, s.description, s.equipmentClass, s.spareClass].some((v) => v.toLowerCase().includes(query))) {
        return false;
      }
      return true;
    });
  });

  readonly columnDefs: ColDef[] = [
    ...COLUMNS,
    {
      headerName: "Actions",
      width: 100,
      sortable: false,
      filter: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: RowData) => [
          { icon: "edit", label: "Issue", color: "#1d96e9", action: () => this.issueSpare(row as unknown as Spare) },
        ],
      },
    },
  ];

  ngOnInit(): void {
    const data = this.route.snapshot.data as SpareStatusRouteData;
    this.title = data.title;
    this.helpHtml = data.helpHtml ?? "";
    this.kind = data.kind;
    void this.load(data.kind);
  }

  private async load(kind: SpareStatusKind): Promise<void> {
    let source;
    if (kind === "less-than-50") {
      source = this.api.getSparesLessThan50Percent();
    } else if (kind === "d787j-deficiency") {
      source = this.api.getD787jDeficiency();
    } else {
      source = this.api.getCriticalSpareList();
    }
    this.spares.set(await firstValueFrom(source));
  }

  clearFilters(): void {
    this.spareClassFilter.set("");
    this.equipmentClassFilter.set("");
    this.searchText.set("");
  }

  issueSpare(spare: Spare): void {
    this.router.navigate(["/afterAuth/inventory/ship-inventory-obs/search", spare.id, "issue"]);
  }

  onExport(kind: ExportKind): void {
    const rows = this.filteredSpares() as unknown as Record<string, unknown>[];
    if (kind === "excel") {
      this.exportService.downloadCsv(PRINT_COLUMNS, rows, `${this.title.toLowerCase().replace(/\s+/g, "-")}.csv`);
      return;
    }
    this.exportService.printRows(this.title, PRINT_COLUMNS, rows);
  }

  copyRows(): void {
    void this.exportService.copyRows(PRINT_COLUMNS, this.filteredSpares() as unknown as Record<string, unknown>[]);
  }
}
