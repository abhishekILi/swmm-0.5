export interface SpareItem {
  pk?: string | number;
  item_code?: string;
  item_desc?: string;
  qtyRequired?: number;
  inventoryType?: string;
  crp_category?: string;
  sourceTab?: string;
  partNumber?: string;
  [key: string]: unknown;
}

export interface ConfirmModalData {
  dartForMaintenance?: string;
  dartOccasion?: string;
  startDate?: string;
  endDate?: string;
  existingRefit?: string;
  [key: string]: unknown;
}

export interface MasterEquipmentItem {
  id?: string | number;
  equipment_name?: string;
  equipment_code?: string;
  [key: string]: unknown;
}

export interface SelectOption {
  label: string;
  value: string | number;
}
