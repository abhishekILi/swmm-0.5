export type SpareCategory = "CONSUMABLE" | "PERMANENT" | "RETURNABLE" | "IM";

export const SPARE_CATEGORY_LABEL: Record<SpareCategory, string> = {
  CONSUMABLE: "C",
  PERMANENT: "P",
  RETURNABLE: "R",
  IM: "IM",
};

export interface Spare {
  id: string;
  spareClass: string;
  equipmentClass: string;
  patternNumber: string;
  description: string;
  compartment: string;
  rackPosition: string;
  rackNumber: string;
  location: string;
  category: SpareCategory;
  critical: boolean;
  denomination: string;
  authority: string;
  quantityAuthorised: number;
  quantityAvailable: number;
  page: string;
  line: string;
  remarks: string;
  imageUrl?: string;
}

export interface SpareSearchFilters {
  department?: string;
  spareClass?: string;
  equipmentClass?: string;
  equipmentClassText?: string;
  patternNumber?: string;
  description?: string;
  remarksText?: string;
  q?: string;
}

export interface SpareFormPayload {
  spareClass: string;
  equipmentClass: string;
  patternNumber: string;
  description: string;
  compartment: string;
  rackPosition: string;
  rackNumber: string;
  location: string;
  category: SpareCategory;
  critical: boolean;
  denomination: string;
  authority: string;
  quantityAuthorised: number;
  quantityAvailable: number;
  page?: string;
  line?: string;
  remarks?: string;
  image?: File | null;
}

export interface DropdownOptionDto {
  label: string;
  value: string;
}
