/**
 * Raw wire-shape DTOs returned by `backend/wlms` (see `backend/wlms/serializers.py` /
 * `backend/wlms/views.py`). snake_case, FK fields are plain numeric ids unless noted.
 * The service adapts these into the camelCase UI models in `wed.model.ts`.
 */

export interface BackendWlmsSyncResponse {
  status: "success" | "warning";
  message: string;
  updated: number;
  created: number;
  counts: { survey: number; pts: number; demand: number; iif: number };
}

export interface BackendWedExternalSyncResponse {
  status: "success" | "warning";
  message: string;
  created: number;
  updated: number;
}

export interface BackendWlmsEquipment {
  id: number;
  eqpt_id: string | null;
  eqpt_name: string | null;
  remarks: string | null;
  is_active: boolean;
  control_cell_id: string | null;
  sco_id: string | null;
  depot_id: string | null;
  created_by: string | null;
  created_date: string | null;
  updated_by: string | null;
  updated_date: string | null;
}

export interface BackendWlmsSpare {
  id: number;
  wlms_inventory: string | null;
  item_code: string | null;
  item_desc: string | null;
  category: string | null;
  eqpt: number | null;
  denom_id: string | null;
  denomination: number | null;
  sh_name: string | null;
  latest_qty: number | null;
  is_active: boolean;
  typeofspare: string | null;
}

export interface BackendWlmsDashboard {
  equipment: number;
  active_spares: number;
  available_quantity: number;
  pending_surveys: number;
  pending_pts: number;
  pending_demands: number;
  pending_iif: number;
}

/** Common base fields shared by Survey/PTS/Demand workflow entries
 * (`ApprovalWorkflowMixin`-backed models). */
export interface BackendWorkflowEntryBase {
  id: number;
  user_id: number;
  wed_spares_id: number | null;
  obs_spare_id: number | null;
  wed_routine_plan: number | null;
  wed_dart: number | null;
  spare_cart_name: string;
  is_save?: boolean;
  is_hod: boolean;
  is_approval: boolean;
  is_sync: boolean;
  sync_date: string | null;
}

export interface BackendSurveyEntry extends BackendWorkflowEntryBase {
  is_survey: boolean;
  wlms_status: string | null;
  wlms_survey_status: string;
}

export interface BackendPtsEntry extends BackendWorkflowEntryBase {
  survey_no: string | null;
  PTS_demand_no: string | null;
  demand_no: string | null;
  demand_qty: string | null;
  remarks: string | null;
  is_pts: boolean;
  is_rejected: boolean;
  wlms_pts_status: string;
  wed_demandno: string | null;
}

export interface BackendDemandEntry extends BackendWorkflowEntryBase {
  survey_no: string | null;
  PTS_no: string | null;
  demand_no: string | null;
  demand_qty: string | null;
  remarks: string | null;
  is_demand: boolean;
  is_rejected: boolean;
  is_delete: boolean;
  demand_pdf: string | null;
  wlms_demand_status: string;
  wed_demandno: string | null;
}

/** Extra annotated fields `_pending_annotated_entries`/`_serialize_pending` attach on top of
 * the base serializer fields for `*_pending_list` responses (survey/pts/demand "to do" queues). */
export interface BackendPendingAnnotations {
  scrap_qty: number | string;
  equipment_nomenclature: string;
  dart_number: string;
  dart_description: string;
  equipment_class: string;
}

export type BackendPendingSurvey = BackendSurveyEntry & BackendPendingAnnotations;
export type BackendPendingPts = BackendPtsEntry & BackendPendingAnnotations;
export type BackendPendingDemand = BackendDemandEntry & BackendPendingAnnotations;

export interface BackendSurveyPendingListResponse {
  pending_surveys: BackendPendingSurvey[];
  completed_surveys: BackendSurveyEntry[];
}

export interface BackendPtsPendingListResponse {
  pending_pts: BackendPendingPts[];
}

export interface BackendDemandPendingListResponse {
  pending_demands: BackendPendingDemand[];
}

export interface BackendReceiveDemand {
  id: number;
  demand_details: number | null;
  pts_details: number | null;
  demand_number: string | null;
  demand_date: string | null;
  demand_quantity: number;
  original_demand_qty: number | null;
  demand_status: string | null;
  swmm_demandno: string | null;
  dart_no: string | null;
  created_at: string;
  updated_at: string;
  gate_pass_no: string | null;
  gate_pass_date: string | null;
  received_qty: number | null;
  received_date: string | null;
}

export interface BackendWedIif {
  id: number;
  user_id: number;
  spare_id: number | null;
  is_sync: boolean;
  is_hod: boolean;
  is_approval: boolean;
  sync_response: boolean;
  is_delete: boolean;
  sync_date: string | null;
  wlms_iif_status: string;
}

/** Extra fields `wlms_combined_outbox` attaches to every row it merges in, regardless of
 * originating model — `spare_cart_name` is the one field that tells you which workflow (and
 * therefore which backend table / which mark-synced endpoint) a given row's `id` belongs to. */
export interface BackendCombinedOutboxExtra {
  dart_number: string;
  equipment_name: string;
  routine_description: string;
  equipment_nomenclature: string;
  quantity_required: number | string;
  item_serial_no: string;
  spare_cart_name: "Survey" | "PTS" | "Demand" | "IIF" | string;
}

export type BackendCombinedOutboxEntry = { id: number } & Partial<BackendWorkflowEntryBase> &
  Partial<BackendWedIif> &
  BackendCombinedOutboxExtra;

export interface BackendCombinedOutboxResponse {
  pts_entries: BackendCombinedOutboxEntry[];
}

export interface BackendReceiveQueueDemand extends BackendDemandEntry {
  demand_no: string;
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
