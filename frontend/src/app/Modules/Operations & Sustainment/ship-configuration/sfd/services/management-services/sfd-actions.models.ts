export type SfdTransactionType = "equipment" | "system";

/**
 * Shared by CAT1/CAT2/CAT3/Survey & Demand/Local Purchase create payloads — mirrors
 * `SFDTransactionBaseSerializer.Meta.fields` (sfd/serializers.py) field-for-field. Local Purchase
 * now shares the Survey & Demand field set exactly (explicit product direction), so it shares this
 * base + SurveyDemandTransactionPayload's extra fields too — see buildCreatePayload.
 *
 * Also the exact payload shape for `PUT sfd-list/{id}/` (Update): `SFDTransactionViewSet.
 * get_serializer_class` resolves `update` to `SFDTransactionBaseSerializer` regardless of the
 * record's own category (its `serializer_map` is keyed by uppercase "CAT1" etc., which never
 * matches the lowercase category values actually stored, so it always falls through to the base
 * serializer) — so Update accepts exactly this field set, no per-category "new_*" fields.
 */
export interface TransactionCreateCommonFields {
  type: SfdTransactionType;
  /** Backend enum value ("CAT1"/"CAT2"/"CAT3"/"SURVEY"/"OTHER") — see CATEGORY_TO_BODY_VALUE. Distinct from the URL slug ("cat1", "survey-demand", ...) used for routing. */
  category: string;
  equipment_universal_id?: string;
  system_universal_id?: string;
  model_universal_id?: string;
  nomenclature?: string;
  manufacturer_universal_id?: string;
  supplier_universal_id?: string;
  oem_part_no?: string;
  serial_no?: string;
  deck_no?: string;
  /** EquipmentTransaction.Location choice code ("1"-"4"). */
  location?: string;
  compartment_name?: string;
  frame_station_from?: string;
  frame_station_to?: string;
  installation_date?: string;
  authority_of_installation?: string;
  authority_date?: string;
  qty_fitted?: number | null;
  /** Sic — the backend's own field name is misspelled ("shell_life", not "shelf_life"). */
  shell_life?: number | null;
  rh_at_installation?: number | null;
  equipment_section?: string;
}

/** CAT I / CAT II create payload — identical shape, only `category` differs. */
export type Cat1Cat2TransactionPayload = TransactionCreateCommonFields;

/** CAT III (New Induction) — CAT I/2 fields plus manually-entered "new_*" fields for not-yet-in-CMMS data. */
export interface Cat3TransactionPayload extends TransactionCreateCommonFields {
  new_equipment_name?: string;
  new_system_name?: string;
  new_nomenclature?: string;
  new_oem_name?: string;
  new_supplier_name?: string;
  new_oem_part_no?: string;
  new_serial_no?: string;
}

/**
 * Survey & Demand (Serial Number Change) — CAT I/2 fields plus removal + new-installation-date
 * fields. Local Purchase shares this same payload shape (see FIELD_SPECS/buildCreatePayload) since
 * its form now collects the identical field set.
 */
export interface SurveyDemandTransactionPayload extends TransactionCreateCommonFields {
  removal_date?: string;
  authority_of_removal?: string;
  new_installation_date?: string;
  new_serial_no?: string;
  /** Backend field is named `installation_remark` (singular) — `SurveySerializer.installation_remark`, source="installation_remarks". */
  installation_remark?: string;
  /** The NEW equipment's shelf life ("Shelf Life (New Eqpt)") — distinct from `shell_life` (the
   *  existing equipment's own last-recorded value, read-only CMMS display for this category). */
  new_service_life?: number | null;
}

export type TransactionCreatePayload =
  | Cat1Cat2TransactionPayload
  | Cat3TransactionPayload
  | SurveyDemandTransactionPayload;

export interface SfdActionSubmitResult {
  ok: boolean;
  error?: string;
}

/** One `open_defects` entry from `GET sfd-list/{id}/open-dependencies/` — currently always `[]` server-side (a stubbed placeholder), but the shape is real. */
export interface RawOpenDefect {
  id: number;
  defect_no: string;
  title: string;
  status: string;
  severity?: string;
}

/** One `maintenance_routines` entry from `GET sfd-list/{id}/open-dependencies/` — same stub caveat as RawOpenDefect. */
export interface RawMaintenanceRoutine {
  id: number;
  routine_no: string;
  title: string;
  due_date?: string | null;
  status: string;
}

/** `GET sfd-list/{id}/open-dependencies/` — checked before Remove to decide whether the "choose how to proceed" step is needed. */
export interface EquipmentDependencies {
  open_defects: RawOpenDefect[];
  maintenance_routines: RawMaintenanceRoutine[];
}

/**
 * `POST sfd-list/{id}/remove/` request body (`EquipmentRemoveSerializer`) — creates a
 * `RemoveEquipmentRequest` (`request_type: 1`), surfaced later on `GET approval-tracking/`. All
 * fields are required by the serializer, but only `removal_date`/`removal_authority`/
 * `removal_remark` are actually persisted; the rest are echoed context.
 */
export interface RemovalRequestPayload {
  equipment_nomenclature: string;
  equipment_sr_no: string;
  sub_dept: string;
  compartment_name: string;
  removal_date: string;
  removal_authority: string;
  removal_remark: string;
}

/** `GET sfd-list/{id}/remove-details/` — prefills the read-only equipment summary shown at the
 * top of the Removal Details form. Same shape as `RemovalRequestPayload`, since it's the current
 * state of the same fields that `remove/` later writes. */
export type RawRemovalDetails = RemovalRequestPayload;

/**
 * `POST sfd-list/{id}/update_sr_no/` request body (`EquipmentSChangeSerializer`, backend
 * `sfd/serializers.py`) — the real Change Serial endpoint; creates a `RemoveEquipmentRequest`
 * (`request_type: 2`). All 8 fields are plain (non-blank) `CharField`/`DateTimeField`s on the
 * serializer, so every one of them must be sent with a real value or the request 400s.
 */
export interface UpdateSerialNoPayload {
  equipment_nomenclature: string;
  current_sr_no: string;
  sub_dept: string;
  maintop_no: string;
  new_sr_no: string;
  removal_authority: string;
  removal_date: string;
  installation_date: string;
}

/** `GET sfd-list/{id}/update_sr_no_details/` — prefills the Change Serial Number form. Same shape
 * as `UpdateSerialNoPayload` (backend echoes the full `EquipmentSChangeSerializer`, including an
 * always-blank `new_sr_no`). */
export type RawUpdateSrNoDetails = UpdateSerialNoPayload;

/** Partial update of `EquipmentTransaction` via `PATCH sfd-list/{id}/` — raw model field names (`SFDTransactionListSerializer`, `fields = "__all__"`), used by the Record Edit (qty/serial) modal. */
export interface EquipmentTransactionPatchPayload {
  no_of_fits?: number | null;
  equipment_sr_no?: string;
}

/** One row of `GET approval-tracking/` — a flat, unpaginated array combining Remove (`request_type: 1`) and Change Sr. No. (`request_type: 2`) requests; both surface under `category: "Remove"`/`"Change"` only. */
export interface RawApprovalTrackingRow {
  request_id: string;
  equipment: string;
  /** The request TYPE the backend groups by — "Remove" or "Change" — not the equipment's own SFD category (see `transaction_category` for that). */
  category: "Remove" | "Change";
  /** `SFDTransaction.category` on the underlying equipment transaction ("cat1"/"cat2"/"cat3"/"survey"/"other") — read back via `categoryFromBodyValue()`, NOT `categoryFromSlug()`. */
  transaction_category: string;
  submitted_by: string | null;
  submitted: string | null;
  status: "Pending" | "Approved";
  insma_officer: string;
  insma_remarks: string;
  approve_date: string | null;
  updated_date: string | null;
  amendment_note: string | null;
}

/**
 * `PUT approval-tracking/?request_id=...` body — resubmits a "Returned" request with corrected
 * details. Field names here match what `ApprovalTrackingAPIView.put()` (`sfd/views.py`) actually
 * reads off `request.data`, NOT the OpenAPI-documented `ApprovalTrackingUpdateSerializer` (that
 * serializer is wired for schema/docs only — `equipment_name`/`submitted_date` in its declared
 * fields are never read; the view reads `equipment`/`submitted` instead).
 *
 * `category` here is the request TYPE ("remove"/"change", case-insensitive) that selects which
 * table (`RemoveEquipmentRequest`/`ChangeEquipmentRequest`) to update — NOT the equipment's SFD
 * category (that's `transaction_category`). Any other value 400s.
 *
 * `insma_remarks` is written unconditionally (`insma_remarks or ""` if omitted) — omitting it
 * blanks out the reviewer's existing remarks, so always send the current value back to preserve it.
 */
export interface ApprovalTrackingUpdatePayload {
  category: string;
  equipment?: string;
  transaction_category?: string;
  submitted_by?: string;
  /** ISO date (`YYYY-MM-DD`) — overwrites the request's `created_date` outright. */
  submitted?: string;
  insma_remarks?: string;
  amendment_note?: string;
}

export interface ApprovalTrackingUpdateResult {
  message: string;
  data: unknown;
}

/** A `{universal_id, label}` pair from `add-sfd-equipement/dropdowns`'s reference lists — the CMMS join key, not a local PK. */
export interface UniversalIdOption {
  universalId: string;
  label: string;
}

/** One entry of `add-sfd-equipement/dropdowns`'s "Compartment Name" list — the one list that carries a real local PK (`compartment_id`). */
export interface CompartmentDropdownOption {
  id: number;
  name: string;
}

/** All dropdown data for the Add/Update form, sourced from the single `add-sfd-equipement/dropdowns` endpoint (unpaginated). */
export interface SfdActionReferenceData {
  equipment: UniversalIdOption[];
  systems: UniversalIdOption[];
  models: UniversalIdOption[];
  nomenclatures: UniversalIdOption[];
  suppliers: UniversalIdOption[];
  manufacturers: UniversalIdOption[];
  equipmentSections: UniversalIdOption[];
  equipmentTypes: UniversalIdOption[];
  compartments: CompartmentDropdownOption[];
  /** Keyed by `universal_id_m_equipment` too, like models/nomenclatures — lets OEM Part No auto-resolve from an Equipment Name pick. */
  oemPartNumbers: UniversalIdOption[];
  shelfLives: number[];
}

/** Query params for `GET /api/v1/sfd/get_equipment/` — equipment-mode cascade only; `EquipmentDropdownAPIView` has no compartment branch (see CompartmentDetail for that). */
export interface CascadingDropdownParams {
  universal_id_m_equipment: string;
  /** Narrows the match to the specific record the user picked, since one equipment can have
   * several distinct nomenclatures across its fitted history. */
  nomenclature?: string;
}

/**
 * Response of `GET get_equipment/` — confirmed field-for-field from `EquipmentDropdownAPIView`/
 * `EquipmentDropdownResponseSerializer`. The last 9 fields (`equipment_sr_no` through
 * `sub_department`) only feed Survey & Demand / Local Purchase's Auto-Fetch fields — CAT I/II/III
 * get their Deck No/Frame Station/Location/Compartment Name from the separate Compartment-pick
 * cascade instead (`loadCompartmentCascade`/`CompartmentDetail`), not from here.
 */
export interface CascadingDropdownValues {
  system_id?: string | null;
  model_id?: string | null;
  nomenclature_id?: string | null;
  oem_name_id?: string | null;
  supplier_id?: string | null;
  oem_part_no_id?: string | null;
  shelf_life_id?: number | null;
  equipment_sr_no?: string | null;
  deck_no?: string | null;
  frame_station?: string | null;
  /** `EquipmentTransaction.Location` choice code ("1"-"4") — same convention as `CompartmentDetail.location` / `LOCATION_OPTIONS`. */
  location?: string | null;
  /** Sic — misspelled "compartrment" on the wire (`sfd/serializers.py`'s actual field name), not a typo introduced here. */
  compartrment?: string | null;
  /** ISO date (`YYYY-MM-DD`). */
  installation_date?: string | null;
  installation_remarks?: string | null;
  qty_fitted?: number | null;
  sub_department?: string | null;
  new_shelf_life?: number | null;
  /** Whether this equipment (as previously installed) is already mapped to a parent system —
   * see System-Equipment Mapping in the Configuration tab. */
  is_mapped?: boolean;
  /** `universal_id_m_equipment` of the system it's mapped to, matching `ref.systems[].universalId` — only present when `is_mapped` is true. */
  mapped_system_id?: string | null;
}

/**
 * `GET api/v1/sfd/compartments/{id}/` — the real source of deck/frame/location data for a picked
 * Compartment Name (`sfd/source_contract.py::CompartmentSerializer`, backed by `CompartmentMaster`,
 * a plain `ModelSerializer` with no `to_representation()` override). `location` comes back as the
 * RAW `CompartmentMaster.Location` choice key ("port_aft", ...), NOT a display label — distinct
 * from `EquipmentTransaction.Location`'s "1"-"4" codes — see
 * COMPARTMENT_LOCATION_TO_TRANSACTION_LOCATION.
 */
export interface CompartmentDetail {
  id: number;
  name: string;
  main_deck: boolean | null;
  upper_deck: string | null;
  lower_deck: string | null;
  frame_station_from: number | null;
  frame_station_to: number | null;
  location: string | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * One row of `GET sfd-list/` — confirmed shape from the live Swagger response example. FK fields
 * (`equipment`, `system`, `ship`, `supplier`, `manufacturer`, `equipment_type`, `equipment_section`)
 * are raw local PKs with no nested name, so the grid falls back to the `universal_id_*` sibling
 * CharFields to join against the dropdown data's lists for a display name. `category`/`type` are
 * real fields on this row — the category a record belongs to is no longer unresolvable.
 */
export interface RawEquipmentTransactionRow {
  equipment_ship_id: number;
  created_at: string | null;
  updated_at: string | null;
  new_equipment_name: string | null;
  new_system_name: string | null;
  location_code: string | null;
  location_on_board: string | null;
  no_of_fits: number | null;
  equipment_sr_no: string | null;
  new_equipment_sr_no: string | null;
  oem_part_no: string | null;
  new_oem_part_no: string | null;
  deck_no: string | null;
  installation_date: string | null;
  new_installation_date: string | null;
  removal_date: string | null;
  new_supplier_name: string | null;
  new_manufacturer_name: string | null;
  remark: string | null;
  srar_applicable: boolean | null;
  maintop_id: number | null;
  parent_equipment: number | null;
  active: boolean | null;
  nomenclature: string | null;
  new_nomenclature: string | null;
  service_life: number | null;
  status: number | null;
  removal_remark: string | null;
  authority_of_removal: string | null;
  authority_of_installation: string | null;
  authority_date: string | null;
  rh_at_installation: number | null;
  insma_remarks: string | null;
  universal_id_t_equipment_ship_detail: string | null;
  universal_id_m_ship: string | null;
  universal_id_m_equipment: string | null;
  universal_id_m_srar_type: string | null;
  universal_id_m_supplier: string | null;
  universal_id_m_manufacturer: string | null;
  universal_id_m_equipment_parent: string | null;
  universal_id_m_department: string | null;
  universal_id_t_maintop_header: string | null;
  universal_id_ch_master_equipment_type: string | null;
  universal_id_m_sub_department: string | null;
  is_synced: number | null;
  type: string | null;
  category: string | null;
  frame_station: string | null;
  created_by: number | null;
  updated_by: number | null;
  equipment: number | null;
  system: number | null;
  ship: number | null;
  supplier: number | null;
  manufacturer: number | null;
  equipment_type: number | null;
  equipment_section: number | null;
}

export interface GetTransactionListParams {
  page?: number;
  page_size?: number;
  search?: string;
  ordering?: string;
  /** Case-insensitive substring match across both the old and new equipment-name columns. */
  equipment_name?: string;
  /** Case-insensitive substring match across both the old and new nomenclature columns. */
  nomenclature?: string;
  /** Exact match against `universal_id_m_sub_department`. */
  sub_dept?: string;
  /** Exact integer match against `maintop_id`. */
  maintop_id?: string;
}

/** One `{value, label}` option, shared by every `GET .../filter-options/` response below. */
export interface FilterOption {
  value: string;
  label: string;
}

/** `GET sfd-list/filter-options/` — the distinct values for the 4 filter params `sfd-list/`
 * accepts (equipment_name, nomenclature, sub_dept, maintop_id), sourced from the full active
 * dataset rather than whatever page happens to be loaded in the Active list. */
export interface SfdListFilterOptions {
  equipment_name: FilterOption[];
  nomenclature: FilterOption[];
  sub_dept: FilterOption[];
  maintop_id: FilterOption[];
}

/**
 * `GET recent-activity/` query params. `ship_id` is required server-side and is matched against
 * `ShipMaster.universal_id_m_ship` (a string business ID), NOT the numeric `ShipMaster.ship_id`
 * PK — unlike every other SFD endpoint, which resolves "the ship" itself from a server-side
 * setting and takes no ship param at all. This deployment is single-ship, so the value is a fixed
 * constant (`DEFAULT_SHIP_ID` in `SfdActionsService.loadRecentActivity()`) rather than fetched.
 */
export interface RecentActivityParams {
  ship_id: string;
  days?: number;
  limit?: number;
}

/** One row of `GET recent-activity/` — confirmed shape from the endpoint contract. */
export interface RawRecentActivityRow {
  tag: string;
  date: string;
  equipment: string;
  createdby: string;
  code: string;
  others: string;
}
