export type ParentInventory = "ILMS" | "WLMS";
export type RequisitionCartType = "Survey" | "PTS";

export interface RequisitionEntry {
  id: string;
  requestedFrom: string;
  patternNumber: string;
  description: string;
  equipmentClass: string;
  equipmentName: string;
  category: string;
  denomination: string;
  quantityAuthorised: number;
  quantityAvailable: number;
  quantityRequired: number;
  availableWithMo: string;
  critical: boolean;
  authority: string;
  boxNo: string;
  remarks: string;
  dartNumber?: string;
  routineName?: string;
  routineNo?: string;
  routineDescription?: string;
}

export interface SendToCartPayload {
  ids: string[];
  parentInventory: ParentInventory;
  cartType: RequisitionCartType;
}

export interface IssueRequisitionRow {
  entryId: string;
  patternNumber: string;
  description: string;
  quantityAuthorised: number;
  quantityAvailable: number;
  quantityIssued: number;
  dartNumber?: string;
}

export interface IssueRequisitionPayload {
  username: string;
  remarks: string;
  rows: IssueRequisitionRow[];
}
