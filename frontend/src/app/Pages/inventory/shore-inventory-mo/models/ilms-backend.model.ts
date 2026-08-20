/**
 * Raw wire-shape DTOs returned by `backend/ilms` (see `backend/ilms/serializers.py` /
 * `backend/ilms/views.py`). snake_case, FK fields are plain ids unless noted. The service adapts
 * these into the camelCase UI models in `../models/mo.model.ts`.
 */

export interface BackendIlmsSyncResponse {
  status: "success" | "warning";
  message: string;
  updated: number;
  count: number;
}

/** `VendorSerializer` (`ilms/serializers.py`) — returned by `search_list` (`vendor-search-list/`,
 * used by `getVendors()`). No dedicated bank-details fields exist anywhere on the `Vendor` model. */
export interface BackendVendor {
  vendor_code: string;
  name: string;
  vendor_class: string | null;
  addressee: string | null;
  address_line1: string | null;
  address_line2: string | null;
  address_line3: string | null;
  city: string | null;
  state: string | null;
  pin_code: string | null;
  country_code: string | null;
  remarks: string | null;
  gst_no: string | null;
  pan: string | null;
  approved_by: string | null;
  datetime_approved: string | null;
  date_banned_upto: string | null;
}

export interface BackendItemStation {
  station_code: string;
  sh_no: string;
  available: boolean;
  datetime_added: string | null;
}

export interface BackendItem {
  item_code: string;
  section_head: string | null;
  item_desc: string | null;
  country_code: string | null;
  item_deno: string | null;
  months_shelf_life: number | null;
  crp_category: string | null;
  ved_category: string | null;
  abc_category: string | null;
  incat_yn: boolean;
  // Only present on `item_search/` (search_enriched), not on `item-search-list/` (search_list).
  stations?: BackendItemStation[];
  equipment_code?: string | null;
  equipment_id?: number | null;
  nomenclature?: string | null;
}

export interface BackendItemSearchResponse {
  items: BackendItem[];
  routine_list: unknown[];
}

export interface BackendIlmsDashboard {
  items: number;
  vendors: number;
  mapped_items: number;
  pending_surveys: number;
  pending_pts: number;
  pending_demands: number;
  hod_inbox: number;
  approved_actions: number;
  pending_iif: number;
}

/** Common base fields shared by Survey/PTS/Demand workflow entries
 * (`ApprovalWorkflowMixin`-backed models). */
export interface BackendWorkflowEntryBase {
  id: number;
  custom_user: number;
  vendor_id: number | null;
  ilms_spare_id: string | null;
  obs_spare_id: number | null;
  mo_routine_plan: number | null;
  mo_dart: number | null;
  in_progress_status: string;
  is_sync: boolean;
  is_hod: boolean;
  is_hod_approval: boolean;
}

export interface BackendSurveyEntry extends BackendWorkflowEntryBase {
  demand_number: string;
  is_survey: boolean;
  mo_survey_status: string;
}

export interface BackendPtsEntry extends BackendWorkflowEntryBase {
  pts_number: string;
  is_pts: boolean;
  mo_pts_status: string;
}

export interface BackendDemandEntry extends BackendWorkflowEntryBase {
  demand_number: string;
  is_demand: boolean;
  mo_status: string;
}

/** Extra display fields `pending_list`/`ilms_combined_inbox` splice onto each serialized row —
 * not part of the declared serializer `fields`, so only present on those two actions. `"—"` is
 * the backend's own sentinel for "not resolvable". */
export interface BackendWorkflowDisplayFields {
  dart_number: string;
  equipment_name: string;
  equipment_nomenclature: string;
  dart_description: string;
  quantity_required: number | string;
  equipment_class: string;
}

export type BackendPendingSurvey = BackendSurveyEntry & BackendWorkflowDisplayFields;
export type BackendPendingPts = BackendPtsEntry & BackendWorkflowDisplayFields;
export type BackendPendingDemand = BackendDemandEntry & BackendWorkflowDisplayFields;

export interface BackendIif {
  id: number;
  spare_id: number | null;
  is_sync: boolean;
  sync_response: boolean;
  is_delete: boolean;
}

export interface BackendReceiveRow {
  source: "Demand" | "Survey";
  mo_item_code: string;
  item_description: string;
  crp_category: string;
  denomination: string;
  dart_number: string;
  demand_qty: number | string;
  survey_number: string;
  qty_issued_by_mo: number | string;
  demand_number: string;
  in_progress_status: string;
}

export interface BackendMergedReceiveListResponse {
  entries: BackendReceiveRow[];
  inventory_type: string;
}

export interface ObsSpareLookup {
  id: number;
  pattern_number: string;
  description: string;
  category: string;
  critical: boolean;
  equipment_class: number;
}

export interface ObsEquipmentClassLookup {
  id: number;
  name: string;
}
