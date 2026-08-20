/**
 * Raw wire-shape DTOs returned by `backend/obs` (see `backend/obs/serializers.py` /
 * `backend/obs/views.py`). snake_case, FK fields are plain numeric ids unless noted.
 * The service adapts these into the camelCase UI models in `spare.model.ts` and friends.
 */

export interface BackendLookup {
  id: number;
  name: string;
}

export interface BackendSpareClass extends BackendLookup {
  department: number | null;
}

export interface BackendMasterDropdown {
  departments: BackendLookup[];
}

export interface BackendRoutineRequisitionRow {
  planned_spare_id: number;
  pattern_number: string;
  quantity_required: number;
  onboard_spare: number | null;
  description: string;
  quantity_available: number;
  available_onboard: boolean;
}

export interface BackendDefectRequisitionRow {
  dart_spare_id: number;
  dart: number;
  dart_number: string;
  pattern_number: string;
  description: string;
  quantity_required: number;
  onboard_spare: number | null;
  quantity_available: number;
  available_onboard: boolean;
}

export interface BackendEquipmentClass extends BackendLookup {
  spare_class: number;
}

export interface BackendDenomination extends BackendLookup {
  department: number | null;
}

export type BackendAuthority = BackendLookup;

export interface BackendSpare {
  id: number;
  equipment_class: number;
  pattern_number: string;
  description: string;
  category: string;
  critical: boolean;
  compartment: string | null;
  location: string | null;
  rack_position: string | null;
  rack_number: string | null;
  denomination: number | null;
  quantity_authorised: number;
  quantity_available: number;
  authority: number;
  page: string | null;
  line: string | null;
  remarks: string | null;
  mo_demand_number: string | null;
  image: string | null;
  is_obs: boolean | null;
}

export interface BackendSpareDetailSummary {
  success: boolean;
  data: {
    id: number;
    pattern_number: string;
    description: string;
    category: string;
    equipment_class: string;
    spare_class: string;
    department: string;
    authority: string;
    compartment: string;
    location: string;
    rack_position: string;
    rack_number: string;
    denomination: string;
    quantity_authorised: number;
    quantity_available: number;
    images: string[];
    is_critical: boolean;
  };
}

export interface BackendIssue {
  id: number;
  spare: number;
  equipment: number | null;
  date_of_issue: string;
  username: number;
  quantity_issued: number;
  issue_time: string | null;
  remarks: string;
  dart_number: string;
}

export interface BackendIssueListEntry {
  id: number;
  issue_entry: number;
  quantity_toreturn: number;
  dart_number: string;
}

export interface BackendReturn {
  id: number;
  spare_id: number | null;
  command_id: number | null;
  ship_id: number | null;
  username: string;
  returned_by: number | null;
  remarks: string | null;
  quantity_returned: number;
  return_time: string | null;
}

export interface BackendTyLoanPair {
  issue: BackendIssue;
  return: BackendReturn | null;
}

export interface BackendSurvey {
  id: number;
  issue_entry: number | null;
  spare: number;
  quantity_tosurvey: number;
  dart_number: string | null;
  is_iif: boolean;
  is_iif_sync: boolean;
}

export interface BackendDemand {
  id: number;
  issue_entry: number | null;
  spare: number;
  quantity_todemand: number;
  survey_entry: number | null;
  dart_number: string | null;
  is_iif: boolean;
  is_iif_sync: boolean;
}

export interface BackendNotInCattedItem {
  id: number;
  spare_id: number | null;
  incatted_status: boolean;
  is_deleted: boolean;
}

export interface BackendVerifyPatternResult {
  valid: boolean;
  source?: string;
  pattern_number: string;
  item_code?: string;
  description?: string;
  item_desc?: string;
  category?: string;
  crp_category?: string;
  expected_category?: string;
  category_mismatch?: boolean;
  denomination?: string;
  error?: string;
}

export interface BackendMultiIssueResult {
  status: string;
  issued: string[];
  errors: { pattern_number: string; error: string }[];
  dart_number: string;
  issues: BackendIssue[];
}

/** Master lookup maps built once from the four master-data endpoints and reused
 * to join names onto the id-only fields returned by the Spares/transaction endpoints. */
export interface ObsMasterMaps {
  spareClassNameById: Map<number, string>;
  equipmentClassById: Map<number, { name: string; spareClassId: number }>;
  denominationNameById: Map<number, string>;
  authorityNameById: Map<number, string>;
}
