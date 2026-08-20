import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { ColDef, RowData } from "ag-grid-community";
import { DataGrid } from "../../../../../shared/components/data-grid/data-grid";
import { ModalComponent } from "../../../../../shared/components/modal/modal.component";
import { InputField } from "../../../../../shared/components/input-field/input-field";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { TextareaInput } from "../../../../../shared/components/textarea-input/textarea-input";
import { ExportKind, ExportToolbar } from "../../../../../shared/components/export-toolbar/export-toolbar";
import { ToolbarSearch } from "../../../../../shared/components/toolbar-search/toolbar-search";
import { IconComponent } from "../../../../../shared/components/icon/icon.component";
import { HelpGuidance } from "../../../shared/components/help-guidance/help-guidance";
import { PrintColumn, ReportExportService } from "../../../../../Core/services/generic-export-service/generic-export.service";
import { ObsApiService } from "../../services/obs-api.service";
import { NotificationService } from "../../../../../Core/services/notification/notification.service";
import { IssueListEntry, ReturnedItemStatus } from "../../models/issue.model";

type SpareCategoryFilter = "PERMANENT" | "RETURNABLE" | "CONSUMABLE";
const CATEGORY_FILTER_OPTIONS: { key: SpareCategoryFilter; label: string }[] = [
  { key: "PERMANENT", label: "Permanent" },
  { key: "RETURNABLE", label: "Returnable" },
  { key: "CONSUMABLE", label: "Consumable" },
];

const HELP_HTML = `
  <h6 class="fw-bold mb-1">What this page is for</h6>
  <p class="mb-2">Lists every spare you have issued that is still waiting to be taken back
     on charge. Use the <strong>Return</strong> action on a row to return that spare.</p>
  <h6 class="fw-bold mb-1">What the columns mean</h6>
  <ul class="mb-2">
    <li><strong>Issued To</strong> — the user or ship the spare went to.</li>
    <li><strong>Reason of Issue</strong> — why it was issued (e.g. Defect, Ty Loan).</li>
    <li><strong>Defect in Eqpt Nomenclature</strong> — the equipment the defect was against.</li>
    <li><strong>Authority</strong> — the scale the spare is held on (e.g. D787J).</li>
  </ul>
  <h6 class="fw-bold mb-1">When a row is disabled</h6>
  <p class="mb-2">A row you can act on is still in the <strong>Internal Transactions</strong> cart. If
     you have forwarded a spare to <strong>MO Inventory / WED Inventory</strong> for replenishment
     through MOs, its row here is <strong>disabled</strong> until MO/WED delivers the item onboard and
     the stock is replenished.</p>
  <h6 class="fw-bold mb-1">Return action</h6>
  <p class="mb-0">Opens the return form/dialog where you set <strong>Qty Returned</strong>,
     <strong>Returned By</strong>, <strong>Returned Item Status</strong> (Same as Issued / New Item)
     and <strong>Return Remarks</strong>, then Submit.</p>
`;

const ITEM_STATUS_OPTIONS: { label: string; value: ReturnedItemStatus }[] = [
  { label: "Same as Issued", value: "same" },
  { label: "New Item", value: "new" },
];

@Component({
  selector: "app-obs-return-list",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    DataGrid,
    ModalComponent,
    InputField,
    SelectInput,
    TextareaInput,
    ExportToolbar,
    ToolbarSearch,
    IconComponent,
    HelpGuidance,
  ],
  templateUrl: "./return-list.html",
  styleUrl: "./return-list.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReturnList implements OnInit {
  private readonly api = inject(ObsApiService);
  private readonly fb = inject(FormBuilder);
  private readonly notifications = inject(NotificationService);
  private readonly exportService = inject(ReportExportService);

  readonly helpHtml = HELP_HTML;
  readonly itemStatusOptions = ITEM_STATUS_OPTIONS;
  readonly categoryFilterOptions = CATEGORY_FILTER_OPTIONS;
  readonly entries = signal<IssueListEntry[]>([]);
  readonly activeEntry = signal<IssueListEntry | null>(null);
  readonly saving = signal(false);
  readonly exportBusy = signal<ExportKind | null>(null);
  readonly searchText = signal("");
  readonly criticalOnly = signal(false);
  readonly categoryFilters = signal<Record<SpareCategoryFilter, boolean>>({
    PERMANENT: true,
    RETURNABLE: true,
    CONSUMABLE: true,
  });

  readonly columnDefs: ColDef[] = [
    { field: "patternNumber", headerName: "Pattern Number", flex: 1 },
    { field: "description", headerName: "Spare Description", flex: 1.4 },
    { field: "issueDate", headerName: "Issue Date", width: 130 },
    { field: "issuedQty", headerName: "Issued Qty", width: 110 },
    { field: "username", headerName: "Issued To", flex: 1 },
    { field: "authority", headerName: "Authority", width: 110 },
    { field: "reason", headerName: "Reason of Issue", flex: 1 },
    { field: "equipmentNomenclature", headerName: "Defect in Eqpt Nomenclature", flex: 1.2 },
    { field: "equipmentClass", headerName: "Equipment Class", flex: 1 },
    { field: "spareClass", headerName: "Spare Class", flex: 1 },
    {
      headerName: "Actions",
      width: 170,
      sortable: false,
      valueGetter: (p) =>
        (p.data as IssueListEntry).isWedMo ? "Pending Replenishment" : "Click row to Return",
    },
  ];

  readonly printColumns: PrintColumn[] = this.columnDefs
    .filter((c): c is ColDef & { field: string } => !!c.field)
    .map((c) => ({ header: String(c.headerName ?? c.field), field: c.field }));

  readonly filteredEntries = computed(() => {
    const critical = this.criticalOnly();
    const categories = this.categoryFilters();
    const query = this.searchText().trim().toLowerCase();
    return this.entries().filter((entry) => {
      if (critical && !entry.critical) return false;
      const categoryKey = entry.category?.toUpperCase() as SpareCategoryFilter | undefined;
      if (categoryKey && categoryKey in categories && !categories[categoryKey]) return false;
      if (
        query &&
        ![entry.patternNumber, entry.description, entry.username, entry.authority, entry.equipmentClass, entry.spareClass].some(
          (value) => (value ?? "").toLowerCase().includes(query),
        )
      ) {
        return false;
      }
      return true;
    });
  });

  readonly form = this.fb.nonNullable.group({
    quantityReturned: [1, [Validators.required, Validators.min(1)]],
    returnedBy: ["", Validators.required],
    itemStatus: ["same" as ReturnedItemStatus, Validators.required],
    remarks: ["", Validators.required],
  });

  ngOnInit(): void {
    void this.load();
  }

  private async load(): Promise<void> {
    const entries = await firstValueFrom(this.api.getReturnList());
    this.entries.set(entries);
  }

  toggleCategory(key: SpareCategoryFilter): void {
    this.categoryFilters.update((current) => ({ ...current, [key]: !current[key] }));
  }

  onExport(kind: ExportKind): void {
    const rows = this.filteredEntries() as unknown as Record<string, unknown>[];
    if (kind === "excel") {
      this.exportService.downloadCsv(this.printColumns, rows, "return-spares.csv");
      return;
    }
    this.exportService.printRows("Return Spares", this.printColumns, rows);
  }

  copyRows(): void {
    void this.exportService.copyRows(this.printColumns, this.filteredEntries() as unknown as Record<string, unknown>[]);
    this.notifications.success("Copied to clipboard.");
  }

  onRowClicked(row: RowData): void {
    const entry = row as unknown as IssueListEntry;
    if (entry.isWedMo) {
      this.notifications.info("This item is pending MO/WED replenishment and cannot be returned yet.");
      return;
    }
    this.activeEntry.set(entry);
    this.form.reset({ quantityReturned: entry.issuedQty, returnedBy: "", itemStatus: "same", remarks: "" });
  }

  closeModal(): void {
    this.activeEntry.set(null);
  }

  async submitReturn(): Promise<void> {
    const entry = this.activeEntry();
    if (!entry || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    try {
      const raw = this.form.getRawValue();
      await firstValueFrom(
        this.api.returnSpare(entry.issuePk, { ...raw, quantityReturned: Number(raw.quantityReturned) }),
      );
      this.entries.update((current) => current.filter((e) => e.issuePk !== entry.issuePk));
      this.closeModal();
    } finally {
      this.saving.set(false);
    }
  }
}
