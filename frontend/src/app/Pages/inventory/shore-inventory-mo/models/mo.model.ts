export interface Vendor {
  id: string;
  /** Row position in the loaded list (1-based) — the "SER" column. */
  ser: number;
  vendorCode: string;
  vendorName: string;
  vendorClass: string;
  addressee: string;
  addressLine1: string;
  addressLine2: string;
  addressLine3: string;
  city: string;
  state: string;
  pincode: string;
  countryCode: string;
  remarks: string;
  gstNo: string;
  pan: string;
  approvedBy: string;
  dateApproved: string;
  dateBannedUpto: string;
}

export interface MoItem {
  itemCode: string;
  itemDescription: string;
  crpCategory: string;
  denomination: string;
  shipInventoryStatus: string;
  vendorName: string;
  ilmsEquipmentDescription: string;
  equipmentCode?: string;
}

export interface MoDashboardCounts {
  surveyInProgress: number;
  demandInProgress: number;
  ptsDemandInProgress: number;
  outstandingDemands: number;
  iifInProgress: number;
  ptsRioSurveyPending: number;
}

/**
 * Shared shape for the 5 "Spares Transaction Cart" list pages (Survey, PTS,
 * Demand, Receive, PTS/RIO Survey-Pending). The Django source has a slightly
 * different column set per cart — rather than 5 near-duplicate interfaces,
 * each list page's ColDef[] just picks the fields relevant to it.
 */
export interface MoCartEntry {
  id: string;
  syncStatus: "Synced" | "Not Synced";
  itemCode: string;
  itemDescription: string;
  denomination: string;
  qty: number;
  category: string;
  hodApprovalStatus?: "Approved" | "Pending";
  dartNo?: string;
  ilmsDemandNo?: string;
  surveyNo?: string;
  demandNo?: string;
  demandType?: string;
  moVettingRemarks?: string;
  moIssueStatus?: string;
  equipmentClass?: string;
  equipmentNomenclature?: string;
  incattingStatus?: string;
  /** BACKEND GAP: `merged-receive-list/`'s `qty_issued_by_mo` is hardcoded to `"—"` server-side
   * (`ilms/views.py` `_receive_row()`) — no model field tracks it yet, so this always reads empty
   * for now even though the column/mapping is real. */
  moIssueQty?: string;
}

export interface ApprovalEntry {
  id: string;
  spareCartName: string;
  patternNo: string;
  spareDescription: string;
  dartNo: string;
  equipmentClass: string;
  category: string;
  critical: boolean;
  qty: number;
}

export interface NormalDemandHistoryEntry {
  id: string;
  moItemCode: string;
  itemDescription: string;
  category: string;
  surveyNo: string;
  surveyDate: string;
  demandNo: string;
  demandedQty: number;
  demandDate: string;
  moIssuedQty: number;
  dartNo: string;
}

export interface RioHistoryEntry {
  id: string;
  rioType: string;
  moItemCode: string;
  itemDescription: string;
  rioDemandNo: string;
  demandDate: string;
  dartNo: string;
  qtyDemanded: number;
  moIssueQty: number;
  onboardReceiptDate: string;
  equipmentClass: string;
}

export interface IifHistoryEntry {
  id: string;
  iifRequisitionNo: string;
  iifRequisitionDate: string;
  ilmsSyncDate: string;
  swmmItemCode: string;
  moItemCode: string;
  incattingCompletionDate: string;
  equipmentClass: string;
  equipmentNomenclature: string;
}
