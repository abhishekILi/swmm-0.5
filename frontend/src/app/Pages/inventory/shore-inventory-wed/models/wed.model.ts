export interface WedItem {
  equipmentName: string;
  patternNo: string;
  itemDescription: string;
  denomination: string;
  itemCategory: string;
  inventoryType: string;
}

export interface WedDashboardCounts {
  surveyInProgress: number;
  demandInProgress: number;
  ptsDemandInProgress: number;
  outstandingDemands: number;
  iifInProgress: number;
  ptsRioSurveyPending: number;
}

/**
 * Shared shape for the 6 "Spares Transaction Cart" list pages (Survey, PTS,
 * Demand, Receive, IIF, PTS/RIO Survey-Pending). Each Django source template
 * has a slightly different column set — rather than 6 near-duplicate
 * interfaces, each list page's ColDef[] just picks the fields it needs.
 */
export interface WedCartEntry {
  id: string;
  syncStatus: "Synced" | "Not Synced";
  itemCode: string;
  itemDescription: string;
  denomination?: string;
  qty?: number;
  category?: string;
  hodApprovalStatus?: "Approved" | "Pending";
  dartNo?: string;
  demandNo?: string;
  surveyNo?: string;
  demandType?: string;
  issueStatus?: string;
  vettingRemarks?: string;
  receivedQty?: number;
  wedIssueQty?: number;
  receiptStatus?: string;
  equipmentNomenclature?: string;
  incattingStatus?: string;
  equipmentClass?: string;
  swmmPatternNo?: string;
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
  itemCode: string;
  itemDescription: string;
  category: string;
  surveyNo: string;
  surveyDate: string;
  demandNo: string;
  demandedQty: number;
  demandDate: string;
  wedIssuedQty: number;
  gatePassNo: string;
  dartNo: string;
  equipmentClass: string;
  equipmentNomenclature: string;
}

export interface RioHistoryEntry {
  id: string;
  rioType: string;
  itemCode: string;
  itemDescription: string;
  rioDemandNo: string;
  demandDate: string;
  dtg: string;
  year: string;
  dartNo: string;
  qtyDemanded: number;
  wedIssueQty: number;
  onboardReceiptDate: string;
  gatePassNo: string;
  equipmentClass: string;
}

export interface IifHistoryEntry {
  id: string;
  iifRequisitionNo: string;
  iifRequisitionDate: string;
  wlmsSyncDate: string;
  swmmItemCode: string;
  wedItemCode: string;
  incattingCompletionDate: string;
}
