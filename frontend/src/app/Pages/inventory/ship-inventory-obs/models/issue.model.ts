export type IssueReason = "Defect" | "Ty Loan - Other Ship";

export interface IssueSparePayload {
  reason: IssueReason;
  remarks: string;
  quantityIssued: number;
  /** Defect branch */
  username?: string;
  section?: string;
  equipmentName?: string;
  /** Ty Loan branch */
  command?: string;
  shipId?: string;
  customShip?: string;
  issuedTo?: string;
  dartNo?: string;
}

export interface MultiIssueRow {
  spareId: string;
  patternNumber: string;
  description: string;
  quantityAuthorised: number;
  quantityAvailable: number;
  quantityIssued: number;
}

export interface MultiIssuePayload {
  reason: IssueReason;
  remarks: string;
  username?: string;
  section?: string;
  equipmentName?: string;
  command?: string;
  shipId?: string;
  customShip?: string;
  rows: MultiIssueRow[];
}

export interface MultiIssueResult {
  issued: string[];
  errors: { patternNumber: string; error: string }[];
}

export type ReturnedItemStatus = "same" | "new";

export interface ReturnSparePayload {
  quantityReturned: number;
  returnedBy: string;
  itemStatus: ReturnedItemStatus;
  remarks: string;
}

export interface IssueListEntry {
  issuePk: string;
  spareId: string;
  patternNumber: string;
  description: string;
  issueDate: string;
  username: string;
  issuedQty: number;
  authority: string;
  reason: IssueReason;
  equipmentNomenclature: string;
  equipmentClass: string;
  spareClass: string;
  category: string;
  denomination: string;
  critical: boolean;
  /** Row is disabled (forwarded to MO/WED for replenishment) until stock is replenished. */
  isWedMo: boolean;
}

export interface ObsDashboardCounts {
  sparesIssuedToMaintainers: number;
  sparesIssuedOnTyLoan: number;
  sparesReturned: number;
  sparesLessThan50Percent: number;
  d787jDeficiency: number;
  criticalSpareList: number;
}

export interface IssuedReturnedTrend {
  months: string[];
  defect: { issued: number[]; returned: number[] };
  tyLoan: { issued: number[]; returned: number[] };
}
