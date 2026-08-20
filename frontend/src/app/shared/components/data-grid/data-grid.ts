import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnChanges,
  SimpleChanges,
  ChangeDetectionStrategy,
  signal
} from "@angular/core";

import { ColDef, GridApi, GridReadyEvent, RowNode, RowData, CellCallbackParams } from "ag-grid-community";
import { AgGridAngular } from "ag-grid-angular";
import { IconComponent } from '../icon/icon.component';

/** Minimal shape of ag-grid's row-clicked event consumed by this wrapper. */
interface DataGridRowClickEvent {
  data: RowData;
}

@Component({
  selector: "app-data-grid",
  standalone: true,
  imports: [
    AgGridAngular,
    IconComponent
  ],
  templateUrl: "./data-grid.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrls: ["./data-grid.css"],
})
export class DataGrid implements OnChanges {
  @Input() rowData: RowData[] = [];
  @Input() columnDefs: ColDef[] = [];
  @Input() totalRowCount?: number | null;
  // internal page when using server-side pagination (1-based)
  private internalPage = 1;
  @Input() pagination = true;
  @Input() pageSize = 10;
  /** Optional identity for whatever dataset `rowData`/`totalRowCount` currently represent (e.g.
   * a report id). This component is long-lived across dataset switches within the same page —
   * neither `internalPage` (server-side page tracker) nor ag-grid's own `paginationPageSize`
   * grid option ever reset on their own, so without this, switching to a different report keeps
   * showing whatever page/page-size the user last picked on the PREVIOUS one, even though fresh
   * page-1 data already loaded. Pass a value that changes exactly when the dataset does. */
  @Input() resetKey?: string | number | null;
  @Input() height = "100%";
  @Input() maxHeight = "";
  @Input() autoHeight = false;
  @Input() checkboxSelection = false;
  @Input() headerCheckboxSelection = false;
  @Input() suppressRowClickSelection = false;
  @Input() selectable = false;
  /** Opt-in: allow dragging column headers to reorder them (off by default). */
  @Input() enableColumnReorder = false;

  @Output() selectionChanged = new EventEmitter<RowData[]>();
  @Output() rowClicked = new EventEmitter<RowData>();
  @Output() gridReady = new EventEmitter<GridReadyEvent>();
  @Output() pageRequested = new EventEmitter<{ page: number; pageSize: number }>();
  /** Emits the new column order (colId/field list) after a header drag completes. */
  @Output() columnMoved = new EventEmitter<string[]>();
  // Datagrid
  @Input() showCheckboxes = false;
  @Input() showHeaderCheckbox = true;
  /** Optional per-row gate for `showCheckboxes` — rows it returns `false` for render
   * their checkbox disabled/unselectable (e.g. a draft record that can't join a batch
   * action yet). Left `undefined`, every row is selectable. */
  @Input() isRowSelectable?: (row: RowData) => boolean;
  @Output() cellClicked = new EventEmitter<CellCallbackParams>();
  gridApi!: GridApi;
  // totalRows = 0;
  // totalPages = 0;
  // currentPage = 1;
  // startRow = 0;
  // endRow = 0;

  readonly totalRows = signal(0);
  readonly totalPages = signal(0);
  readonly currentPage = signal(1);
  readonly startRow = signal(0);
  readonly endRow = signal(0);

  /** Captured from the first `pageSize` input the caller ever bound — what `resetKey` changes
   * restore `pageSize` back to, instead of a hardcoded 10 that would ignore a caller passing e.g.
   * `[pageSize]="25"`. */
  private defaultPageSize: number | null = null;
  defaultColDef: ColDef = {
    sortable: true,
    filter: false,
    resizable: true,
    unSortIcon: true,
    suppressHeaderMenuButton: true,
    minWidth: 120,
    cellStyle: {
      display: "flex",
      cursor: "pointer",
      alignItems: "center",
      justifyContent: "flex-start",
      overflow: "hidden",
    },
  };


  // ngOnChanges(changes: SimpleChanges): void {
  //   if (changes["rowData"] && this.gridApi) {
  //     setTimeout(() => {
  //       this.updatePaginationInfo();
  //     });
  //   }
  // }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['pageSize'] && this.defaultPageSize === null) {
      this.defaultPageSize = this.pageSize;
    }

    if (changes['resetKey'] && !changes['resetKey'].firstChange) {
      this.internalPage = 1;
      this.pageSize = this.defaultPageSize ?? this.pageSize;
      this.currentPage.set(1);
      if (this.gridApi) {
        this.gridApi.setGridOption("paginationPageSize", this.pageSize);
        this.gridApi.paginationGoToFirstPage();
      }
    }

    if ((changes['rowData'] || changes['totalRowCount']) && this.gridApi) {
      this.updatePaginationInfo();
    }
  }

  // get finalColumnDefs(): ColDef[] {
  //   return [...this.columnDefs];
  // }

  get finalColumnDefs(): ColDef[] {
    if (!this.showCheckboxes) {
      return [...this.columnDefs];
    }

    const isRowSelectable = this.isRowSelectable;
    return [
      {
        headerCheckboxSelection: this.showHeaderCheckbox,
        checkboxSelection: isRowSelectable ? (params: { data: RowData }) => isRowSelectable(params.data) : true,
        width: 48,
        minWidth: 48,
        maxWidth: 48,
        pinned: "left",
        sortable: false,
        filter: false,
        resizable: false,
        cellClass: "grid-select-cell",
        headerClass: "grid-select-cell",
      },
      ...this.columnDefs,
    ];
  }

  /** Grid-level `isRowSelectable` — keeps select-all and click-to-select in sync with
   * the same per-row gate the checkbox column itself uses. */
  rowSelectableFn = (node: RowNode): boolean => (this.isRowSelectable ? this.isRowSelectable(node.data as RowData) : true);

  onGridReady(params: GridReadyEvent): void {
    this.gridApi = params.api;
    this.gridReady.emit(params);
    this.updatePaginationInfo();
  }
  onCellClicked(event: CellCallbackParams): void {
    this.cellClicked.emit(event);
  }
  onSelectionChanged(): void {
    const rows = this.gridApi.getSelectedRows();
    this.selectionChanged.emit(rows);
  }

  onRowClicked(event: DataGridRowClickEvent): void {
    this.rowClicked.emit(event.data);
  }

  onColumnMoved(event: { finished: boolean }): void {
    // Emit only when the drag settles, and only the caller's own columns.
    if (!event.finished || !this.gridApi) return;
    const api = this.gridApi as unknown as { getColumnState(): { colId?: string }[] };
    const order = api
      .getColumnState()
      .map((s) => s.colId)
      .filter((id): id is string => !!id);
    this.columnMoved.emit(order);
  }

  updatePaginationInfo(): void {
    if (!this.gridApi) {
      return;
    }

    const pageSize = this.gridApi.paginationGetPageSize();

    if (this.totalRowCount != null) {
      this.totalRows.set(this.totalRowCount);

      this.totalPages.set(
        Math.max(1, Math.ceil(this.totalRowCount / pageSize))
      );

      this.currentPage.set(
        Math.min(Math.max(1, this.internalPage), this.totalPages())
      );

      this.startRow.set(
        this.totalRowCount === 0
          ? 0
          : (this.currentPage() - 1) * pageSize + 1
      );

      this.endRow.set(
        Math.min(this.currentPage() * pageSize, this.totalRowCount)
      );
      return;
    }

    // Client-side pagination — no `totalRowCount` was given, so ag-grid is paginating `rowData`
    // itself internally (its own panel is just hidden via `suppressPaginationPanel`). Read that
    // state back so our own footer ("X-Y of Z" + prev/next) reflects it instead of sitting at
    // the 0/0 default forever. `rowData.length` stands in for ag-grid's own row count since this
    // wrapper never enables grid-level filtering (`defaultColDef.filter = false`), so it's always accurate.
    const totalRows = this.rowData?.length ?? 0;
    const totalPages = Math.max(1, this.gridApi.paginationGetTotalPages());
    const current = this.gridApi.paginationGetCurrentPage() + 1; // ag-grid is 0-based

    this.totalRows.set(totalRows);
    this.totalPages.set(totalPages);
    this.currentPage.set(current);
    this.startRow.set(totalRows === 0 ? 0 : (current - 1) * pageSize + 1);
    this.endRow.set(Math.min(current * pageSize, totalRows));
  }

  nextPage(): void {
    if (!this.gridApi) return;
    if (this.totalRowCount != null) {
      const target = this.internalPage + 1;
      const pageSize = this.gridApi ? this.gridApi.paginationGetPageSize() : this.pageSize;
      const totalPages = Math.max(1, Math.ceil((this.totalRowCount || 0) / pageSize));
      if (target > totalPages) return;
      this.internalPage = target;
      this.pageRequested.emit({ page: this.internalPage, pageSize: pageSize });
      this.updatePaginationInfo();
      return;
    }

    const current = this.gridApi.paginationGetCurrentPage();
    const targetPage = current + 2; // convert zero-based to 1-based
    this.pageRequested.emit({ page: targetPage, pageSize: this.pageSize });
    this.gridApi.paginationGoToNextPage();
    this.updatePaginationInfo();
  }

  prevPage(): void {
    if (!this.gridApi) return;
    if (this.totalRowCount != null) {
      const target = Math.max(1, this.internalPage - 1);
      if (target === this.internalPage) return;
      this.internalPage = target;
      const pageSize = this.gridApi ? this.gridApi.paginationGetPageSize() : this.pageSize;
      this.pageRequested.emit({ page: this.internalPage, pageSize: pageSize });
      this.updatePaginationInfo();
      return;
    }

    const current = this.gridApi.paginationGetCurrentPage();
    const targetPage = Math.max(1, current); // previous page in 1-based
    this.pageRequested.emit({ page: targetPage, pageSize: this.pageSize });
    this.gridApi.paginationGoToPreviousPage();
    this.updatePaginationInfo();
  }

  firstPage(): void {
    if (!this.gridApi) return;
    if (this.totalRowCount != null) {
      this.internalPage = 1;
      const pageSize = this.gridApi ? this.gridApi.paginationGetPageSize() : this.pageSize;
      this.pageRequested.emit({ page: 1, pageSize });
      this.updatePaginationInfo();
      return;
    }

    this.pageRequested.emit({ page: 1, pageSize: this.pageSize });
    this.gridApi.paginationGoToFirstPage();
    this.updatePaginationInfo();
  }

  lastPage(): void {
    if (!this.gridApi) return;
    if (this.totalRowCount != null) {
      const pageSize = this.gridApi ? this.gridApi.paginationGetPageSize() : this.pageSize;
      const last = Math.max(1, Math.ceil((this.totalRowCount || 0) / pageSize));
      this.internalPage = last;
      this.pageRequested.emit({ page: last, pageSize });
      this.updatePaginationInfo();
      return;
    }

    const last = this.gridApi.paginationGetTotalPages();
    this.pageRequested.emit({ page: last, pageSize: this.pageSize });
    this.gridApi.paginationGoToLastPage();
    this.updatePaginationInfo();
  }

  onPageSizeChange(event: Event): void {
    if (!this.gridApi) return;
    const value = Number((event.target as HTMLSelectElement).value);
    this.pageSize = value;
    this.gridApi.setGridOption("paginationPageSize", value);
    this.gridApi.paginationGoToFirstPage();
    if (this.totalRowCount != null) {
      // switch to first page for server-side
      this.internalPage = 1;
      this.pageRequested.emit({ page: 1, pageSize: this.pageSize });
      setTimeout(() => this.updatePaginationInfo());
      return;
    }

    this.pageRequested.emit({ page: 1, pageSize: this.pageSize });
    setTimeout(() => {
      this.updatePaginationInfo();
    });
  }

  icons = {
    sortAscending: `
    <svg xmlns="http://www.w3.org/2000/svg"
         width="16"
         height="16"
         viewBox="0 0 24 24"
         fill="none"
         stroke="currentColor"
         stroke-width="2"
         stroke-linecap="round"
         stroke-linejoin="round">
      <path d="m5 12 7-7 7 7"/>
      <path d="M12 19V5"/>
    </svg>
  `,

    sortDescending: `
    <svg xmlns="http://www.w3.org/2000/svg"
         width="16"
         height="16"
         viewBox="0 0 24 24"
         fill="none"
         stroke="currentColor"
         stroke-width="2"
         stroke-linecap="round"
         stroke-linejoin="round">
      <path d="m19 12-7 7-7-7"/>
      <path d="M12 5v14"/>
    </svg>
  `,

    sortUnSort: `
    <svg xmlns="http://www.w3.org/2000/svg"
         width="16"
         height="16"
         viewBox="0 0 24 24"
         fill="none"
         stroke="currentColor"
         stroke-width="2"
         stroke-linecap="round"
         stroke-linejoin="round">
      <path d="m7 15 5 5 5-5"/>
      <path d="m7 9 5-5 5 5"/>
    </svg>
  `
  };



}
