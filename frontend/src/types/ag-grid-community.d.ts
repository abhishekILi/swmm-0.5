declare module 'ag-grid-community' {
  /** Grid row data is dynamic; default to unknown. Kept as a named alias (not inlined as
   *  plain `unknown`) purely for self-documentation across the generics below. */
  // eslint-disable-next-line sonarjs/redundant-type-aliases
  export type RowData = unknown;

  export interface RowNode<TData = RowData> {
    data?: TData;
    setDataValue(field: string, value: unknown): void;
    [key: string]: unknown;
  }

  export interface CellCallbackParams<TData = RowData> {
    data: TData;
    colDef: ColDef<TData>;
    node?: RowNode<TData>;
    api?: GridApi<TData>;
    context?: unknown;
    [key: string]: unknown;
  }

  export interface ColDef<TData = RowData> {
    field?: string;
    headerName?: string;
    valueGetter?: string | ((params: CellCallbackParams<TData>) => unknown);
    valueSetter?: string | ((params: CellCallbackParams<TData>) => boolean);
    valueFormatter?: string | ((params: CellCallbackParams<TData>) => string);
    onCellClicked?: (params: CellCallbackParams<TData>) => void;
    cellRenderer?: unknown;
    cellRendererParams?: Record<string, unknown>;
    editable?: boolean;
    sortable?: boolean;
    filter?: boolean | string;
    resizable?: boolean;
    width?: number;
    minWidth?: number;
    maxWidth?: number;
    pinned?: string | boolean;
    flex?: number;
    hide?: boolean;
    rowGroup?: boolean;
    sort?: 'asc' | 'desc';
    comparator?: (valueA: unknown, valueB: unknown, nodeA?: RowNode<TData>, nodeB?: RowNode<TData>, isDescending?: boolean) => number;
    [key: string]: unknown;
  }

  export interface GridApi<TData = RowData> {
    refreshCells(params?: Record<string, unknown>): void;
    setGridOption(key: string, value: unknown): void;
    applyTransaction(transaction: Record<string, unknown>): unknown;
    forEachNode(callback: (node: RowNode<TData>) => void): void;
    getSelectedRows(): TData[];
    paginationGetCurrentPage(): number;
    paginationGetPageSize(): number;
    paginationGetTotalPages(): number;
    paginationGoToNextPage(): void;
    paginationGoToPreviousPage(): void;
    paginationGoToFirstPage(): void;
    paginationGoToLastPage(): void;
    [key: string]: unknown;
  }

  export interface GridReadyEvent<TData = RowData> {
    api: GridApi<TData>;
    columnApi?: unknown;
    [key: string]: unknown;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export interface ICellRendererParams<TData = RowData, TValue = any, TContext = unknown> {
    value?: TValue;
    valueFormatted?: string | null;
    data: TData;
    node: RowNode<TData>;
    colDef: ColDef<TData>;
    api?: GridApi<TData>;
    context?: TContext;
    [key: string]: unknown;
  }

  export class ModuleRegistry {
    static registerModules(modules: unknown[]): void;
  }

  export const AllCommunityModule: unknown;
}
