import { ParentInventory } from "./requisition.model";

export interface SurveyEntry {
  id: string;
  patternNumber: string;
  dartNumber: string;
  description: string;
  quantity: number;
  category: string;
  equipmentClass: string;
  critical: boolean;
  authority: string;
  parentInventory: ParentInventory;
  incattingStatus: string;
}

export interface SurveyDetailsPayload {
  surveyNumber: string;
  quantitySurveyed: number;
  surveyReportDate: string;
  remarks: string;
}

export interface DemandEntry {
  id: string;
  patternNumber: string;
  description: string;
  quantity: number;
  category: string;
  equipmentClass: string;
  critical: boolean;
  authority: string;
  parentInventory: ParentInventory;
  incattingStatus: string;
  dartNumber: string;
}

export interface DemandDetailsPayload {
  quantityDemanded: number;
  demandNumber: string;
  demandDate: string;
  remarks: string;
}

export interface IifEntry {
  id: string;
  patternNumber: string;
  description: string;
  quantity: number;
  category: string;
  equipmentClass: string;
  critical: boolean;
  authority: string;
  parentInventory: ParentInventory;
}

export interface VerifyPatternResult {
  matched: boolean;
  itemCode?: string;
  description?: string;
  category?: string;
}
