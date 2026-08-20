import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";

import { getErrorMessage } from "../../../../../../Core/services/common/http-feedback";
import {
  ApprovalSfdRow,
  CATEGORY_TO_BODY_VALUE,
  categoryFromBodyValue,
  controlKey,
  DefectRecord,
  LOCATION_OPTIONS,
  RECENT_ACTIVITY_TAG_META,
  RecentActivityRow,
  SfdActionRow,
  SfdCategory,
  supplierFieldName,
} from "../../management/sfd-actions-fields.config";
import { RawAddSfdEquipmentOptions, SfdActionsApiService } from "./sfd-actions-api.service";
import {
  ApprovalTrackingUpdatePayload,
  Cat3TransactionPayload,
  CascadingDropdownValues,
  CompartmentDetail,
  GetTransactionListParams,
  PaginatedResponse,
  RawEquipmentTransactionRow,
  RawRecentActivityRow,
  RawRemovalDetails,
  RawUpdateSrNoDetails,
  RemovalRequestPayload,
  SfdActionReferenceData,
  SfdActionSubmitResult,
  SfdListFilterOptions,
  SfdTransactionType,
  SurveyDemandTransactionPayload,
  TransactionCreateCommonFields,
  TransactionCreatePayload,
  UpdateSerialNoPayload,
} from "./sfd-actions.models";

type CheckVals = Record<string, "Yes" | "No">;
interface FrameRange { from: string; to: string }
type RecordEditMode = "update" | "serial";

interface CompartmentCascadeValues {
  deck_no: string;
  frame_station_from: string;
  frame_station_to: string;
  location_code: string;
}

/**
 * `recent-activity/`'s `ship_id` param is matched against `ShipMaster.universal_id_m_ship`, which
 * has no frontend-facing endpoint (unlike every other SFD endpoint, which resolves "the ship"
 * server-side via a fixed deployment setting — see `get_configured_ship()`/`SWMM_SHIP_CODE` on the
 * backend). This deployment is single-ship, and "33" is that ship's id.
 */
const DEFAULT_SHIP_ID = "33";

/**
 * `CompartmentSerializer` (`sfd/source_contract.py`) is a plain `ModelSerializer` with no
 * `to_representation()` override — `location` comes back as `CompartmentMaster.location`'s RAW
 * `TextChoices` value ("port_aft", "port_forward", "starboard_forward", "starboard_aft"), not a
 * display label. Keyed here (normalized) so it lines up 1:1 with `EquipmentTransaction.Location`'s
 * "1"-"4" codes.
 */
const COMPARTMENT_LOCATION_TO_TRANSACTION_LOCATION: Record<string, string> = {
  port_aft: "1",
  port_forward: "2",
  starboard_forward: "3",
  starboard_aft: "4",
};

/** Case/punctuation-insensitive lookup key — `CompartmentMaster.location` is free enough (older
 * rows, manual CMMS imports) that a stored value like "PORT AFT" or "Port-Aft" shouldn't fail to
 * match "port_aft" and silently leave the Add SFD form's Location dropdown unmapped. */
function normalizeLocationKey(value: string): string {
  return value.trim().toLowerCase().replace(/[\s,_-]+/g, "_").trim();
}

const NORMALIZED_COMPARTMENT_LOCATION_TO_TRANSACTION_LOCATION: Record<string, string> = Object.fromEntries(
  Object.entries(COMPARTMENT_LOCATION_TO_TRANSACTION_LOCATION).map(([label, code]) => [
    normalizeLocationKey(label),
    code,
  ]),
);

/** `CompartmentMaster.upper_deck`/`lower_deck` codes ("deck01", "deck1", ...) → their Django choice label ("Deck 01", "Deck 1", ...). */
function deckLabel(code: string | null): string {
  return code ? code.replace(/^deck/i, "Deck ") : "";
}

function toId(value: unknown): number | null {
  const n = Number(value);
  return value !== "" && value != null && !Number.isNaN(n) ? n : null;
}

const CASCADE_DATE_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Survey & Demand / Local Purchase's "Location" field is Auto-Fetch (read-only text, not a
 * select) — `onEquipmentPicked`'s cascade (sfd-management.component.ts) deliberately stores the
 * human-readable label ("Port, Aft") in the control so it displays sensibly, since a raw "1"-"4"
 * code has nowhere else to become readable. That means the control's raw value is NOT always the
 * `EquipmentTransaction.Location` code the backend's `ChoiceField` requires — CAT I/II/III's own
 * Location dropdown DOES already store the code directly, so this must round-trip both cases.
 */
function toLocationCode(value: string): string | undefined {
  if (!value) return undefined;
  if (LOCATION_OPTIONS.some((o) => o.value === value)) return value;
  const match = LOCATION_OPTIONS.find((o) => o.label === value);
  return match ? String(match.value) : value;
}

/**
 * Mirror of `formatCascadeDate` (sfd-management.component.ts) — Survey & Demand / Local
 * Purchase's Auto-Fetch "Installation Date" stores that function's "DD-MMM-YYYY" DISPLAY string
 * in the control, not the ISO date the backend's `DateField` requires. CAT I/II/III's own
 * Installation Date (`<app-date-picker>`) already emits ISO `yyyy-MM-dd` directly, so this must
 * round-trip both cases.
 */
function toIsoDate(value: string): string | undefined {
  if (!value) return undefined;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const match = /^(\d{2})-([A-Za-z]{3})-(\d{4})$/.exec(value);
  if (match) {
    const [, dd, mmm, yyyy] = match;
    const monthIndex = CASCADE_DATE_MONTHS.findIndex((m) => m.toLowerCase() === mmm.toLowerCase());
    if (monthIndex >= 0) {
      return `${yyyy}-${String(monthIndex + 1).padStart(2, "0")}-${dd}`;
    }
  }
  return value;
}

/** `recent-activity/`'s `date` is a full ISO datetime — the Recent Activity popup only ever shows
 * a short `DD-MM-YY`, matching every other date in that popup/list. */
function formatActivityDate(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  const dd = String(parsed.getDate()).padStart(2, "0");
  const mm = String(parsed.getMonth() + 1).padStart(2, "0");
  const yy = String(parsed.getFullYear()).slice(-2);
  return `${dd}-${mm}-${yy}`;
}

/** A wired endpoint failed — surface the real error, never a simulated success. */
function toErrorResult(err: unknown): SfdActionSubmitResult {
  return { ok: false, error: getErrorMessage(err) };
}

/**
 * Business-logic layer for the SFD Actions tab: loads the real dropdown data from
 * `add-sfd-equipement/dropdowns`, turns the common dynamic form's raw values into either the
 * per-category create payload (`transaction/cat*`) or the Update payload (`sfd-list/{id}/`, whose
 * field names differ entirely from the create endpoints), and submits it via
 * `SfdActionsApiService`. Kept separate from that API service so payload-shaping logic doesn't
 * leak into HTTP plumbing.
 */
@Injectable({ providedIn: "root" })
export class SfdActionsService {
  private readonly api = inject(SfdActionsApiService);

  /** Loads the Add/Update form's dropdown data from the one consolidated, unpaginated endpoint. */
  async loadReferenceData(): Promise<SfdActionReferenceData> {
    const addSfd: RawAddSfdEquipmentOptions | null = await firstValueFrom(
      this.api.getAddSfdEquipmentDropdowns(),
    ).catch((err) => {
      // Previously swallowed silently — every dropdown (not just one) goes empty if this fails,
      // so a visible log is worth the noise for diagnosing exactly this kind of issue.
      console.error("[SfdActions] add-sfd-equipement/dropdowns/ failed — all Add/Update dropdowns will be empty", err);
      return null;
    });

    // `system_name` comes back double-nested (`[[...]]`) — a real bug in the backend's
    // AddSFDEquipementSerializer.to_representation, which hardcodes `[system_names]`. Flattened here.
    const systemRows = (addSfd?.system_name ?? []).flat();

    return {
      equipment: (addSfd?.equipment_name ?? []).map((e) => ({
        universalId: e.universal_id_m_equipment,
        label: e.equipment_name,
      })),
      systems: systemRows.map((s) => ({
        universalId: s.universal_id_m_equipment,
        label: s.system_name,
      })),
      models: (addSfd?.model ?? []).map((m) => ({ universalId: m.universal_id_m_equipment, label: m.model })),
      nomenclatures: (addSfd?.Nomenclature ?? []).map((n) => ({
        universalId: n.universal_id_m_equipment,
        label: n.Nomenclature,
      })),
      suppliers: (addSfd?.Supplier ?? []).map((s) => ({
        universalId: s.universal_id_M_supplier,
        label: s.supplier_name,
      })),
      manufacturers: (addSfd?.["OEM Name"] ?? []).map((m) => ({
        universalId: m.universal_id_M_supplier,
        label: m.manufacturer_name,
      })),
      equipmentSections: (addSfd?.["Equipment Section"] ?? []).map((s) => ({
        universalId: s.universal_id_m_sub_department,
        label: s.sub_department_name,
      })),
      equipmentTypes: (addSfd?.["Equipment Type"] ?? []).map((t) => ({
        universalId: t.universal_id_ch_master_equipment_type,
        label: t.name,
      })),
      compartments: (addSfd?.["Compartment Name"] ?? []).map((c) => ({
        id: c.compartment_id,
        name: c.compartment_name,
      })),
      oemPartNumbers: (addSfd?.["OEM Part No"] ?? [])
        .filter((p) => !!p.oem_part_no)
        .map((p) => ({ universalId: p.universal_id_m_equipment, label: p.oem_part_no })),
      shelfLives: Array.from(
        new Set((addSfd?.["Shelf Life"] ?? []).map((s) => s.shelf_lifes_name).filter((v) => v != null)),
      ),
    };
  }

  /** Equipment-mode cascade: pick an Equipment/System, get back the CMMS ids for its dependent fields. */
  async loadEquipmentCascade(
    universalIdMEquipment: string,
    nomenclature?: string,
  ): Promise<CascadingDropdownValues | null> {
    return firstValueFrom(
      this.api.getEquipmentCascade({ universal_id_m_equipment: universalIdMEquipment, nomenclature }),
    ).catch(() => null);
  }

  /**
   * Compartment pick cascade — `GET compartments/{id}/` is the real source (`get_equipment/` has no
   * compartment mode at all). Derives Deck No from `main_deck`/`upper_deck`/`lower_deck` (no direct
   * "deck_no" field exists on CompartmentMaster) and Location from its own port/starboard choice set.
   */
  async loadCompartmentCascade(compartmentId: number): Promise<CompartmentCascadeValues | null> {
    const compartment: CompartmentDetail | null = await firstValueFrom(
      this.api.getCompartment(compartmentId),
    ).catch((err) => {
      // Previously swallowed silently — Deck No/Frame Station/Location would just stay unmapped
      // with nothing in the console to explain why (e.g. a compartment picked from the dropdown
      // that 404s here — a stale/soft-deleted compartment still listed there).
      console.error(`[SfdActions] compartments/${compartmentId}/ failed — Deck No/Frame Station/Location won't map`, err);
      return null;
    });
    if (!compartment) return null;

    const deckNo = compartment.main_deck
      ? "Main Deck"
      : deckLabel(compartment.upper_deck) || deckLabel(compartment.lower_deck);

    return {
      deck_no: deckNo,
      frame_station_from: compartment.frame_station_from != null ? String(compartment.frame_station_from) : "",
      frame_station_to: compartment.frame_station_to != null ? String(compartment.frame_station_to) : "",
      location_code: compartment.location
        ? NORMALIZED_COMPARTMENT_LOCATION_TO_TRANSACTION_LOCATION[normalizeLocationKey(compartment.location)] ?? ""
        : "",
    };
  }

  /** Active list grid — real server-side pagination. */
  async loadTransactionList(
    params: GetTransactionListParams,
  ): Promise<PaginatedResponse<RawEquipmentTransactionRow>> {
    return firstValueFrom(this.api.getTransactionList(params));
  }

  /** Active list filter dropdowns (Equipment Name/Nomenclature/Sub Dept/Maintop) — loaded once,
   * independent of pagination/filtering, so the options always cover the full active dataset. */
  async loadSfdListFilterOptions(): Promise<SfdListFilterOptions | null> {
    return firstValueFrom(this.api.getSfdListFilterOptions()).catch((err) => {
      console.error("[SfdActions] sfd-list/filter-options/ failed — Active list filters will be empty", err);
      return null;
    });
  }

  /**
   * Recent Activity popup (SFD Management header). `recent-activity/` requires a `ship_id` param
   * with no fallback (unlike every other SFD endpoint, which resolves "the ship" server-side) —
   * see `DEFAULT_SHIP_ID`'s doc for why this is a fixed constant rather than fetched per request.
   */
  async loadRecentActivity(limit = 15): Promise<RecentActivityRow[]> {
    const rows = await firstValueFrom(
      this.api.getRecentActivity({ ship_id: DEFAULT_SHIP_ID, limit }),
    ).catch((err) => {
      console.error("[SfdActions] recent-activity/ failed", err);
      return null;
    });
    if (!rows) return [];

    return rows.map((row) => this.toRecentActivityRow(row));
  }

  private toRecentActivityRow(row: RawRecentActivityRow): RecentActivityRow {
    const meta = RECENT_ACTIVITY_TAG_META[row.tag] ?? { icon: "submitted", tone: "info" };
    return {
      icon: meta.icon,
      name: row.equipment || "—",
      tag: row.tag,
      tone: meta.tone,
      code: row.code || "—",
      detail: row.others || "",
      date: formatActivityDate(row.date),
      by: row.createdby || "—",
    };
  }

  /**
   * Builds the CAT I/II/III/Survey & Demand common field set — shared by `POST transaction/cat*`
   * (via buildCreatePayload) AND `PUT sfd-list/{id}/` (via buildUpdatePayload), since Update always
   * resolves to the same base serializer regardless of category (see the type doc on
   * TransactionCreateCommonFields). Field names confirmed against `sfd/serializers.py`.
   */
  private buildCommonFields(
    category: SfdCategory,
    sfdType: SfdTransactionType,
    formValue: Record<string, unknown>,
    serial: string,
    frame: FrameRange,
    checkVals: CheckVals,
    ref: SfdActionReferenceData,
  ): TransactionCreateCommonFields {
    const get = (name: string): string => (formValue[controlKey(name)] as string) ?? "";
    const rhKeys = Object.keys(checkVals);
    const rhKey = rhKeys[0];
    const rhApplicable = rhKey ? checkVals[rhKey] === "Yes" : false;
    const rhValue = get("R|H (Running Hours) as on date") || get("R/H of new eqpt at installation");
    const isSystem = sfdType === "system";

    const equipmentLabel = get("Equipment Name");
    const matchList = isSystem ? ref.systems : ref.equipment;
    const equipmentMatch = matchList.find((e) => e.label === equipmentLabel);
    const manufacturerName = get("OEM Name");
    const supplierName = get(supplierFieldName(category));
    const manufacturerMatch = ref.manufacturers.find((m) => m.label === manufacturerName);
    const supplierMatch = ref.suppliers.find((s) => s.label === supplierName);
    // The extra "System Name" field the component adds for Equipment-mode transactions (bound to
    // control key "sysName") is now a real CMMS system pick (options sourced from ref.systems, same
    // as Equipment Name) — so it resolves to a real universal_id. CAT1/CAT2/CAT3/Survey require
    // system_universal_id even in Equipment mode, so it needs this value rather than being left
    // blank whenever isSystem is false.
    const sysNameValue = (formValue["sysName"] as string) ?? "";
    const sysNameMatch = ref.systems.find((s) => s.label === sysNameValue);
    const modelMatch = ref.models.find((m) => m.label === get("Model"));

    return {
      type: sfdType,
      category: CATEGORY_TO_BODY_VALUE[category],
      equipment_universal_id: isSystem ? undefined : equipmentMatch?.universalId,
      system_universal_id: isSystem ? equipmentMatch?.universalId : sysNameMatch?.universalId,
      model_universal_id: modelMatch?.universalId,
      nomenclature: get("Nomenclature"),
      manufacturer_universal_id: manufacturerMatch?.universalId,
      supplier_universal_id: supplierMatch?.universalId,
      oem_part_no: get("OEM Part No") || undefined,
      serial_no: serial,
      deck_no: get("Deck No"),
      location: toLocationCode(get("Location")),
      compartment_name: get("Compartment Name"),
      frame_station_from: frame.from,
      frame_station_to: frame.to,
      installation_date: toIsoDate(get("Installation Date")),
      authority_of_installation: get("Authority for Installation") || get("Installation Authority"),
      authority_date: get("Authority Date") || undefined,
      qty_fitted: toId(get("Qty Fitted")),
      shell_life: toId(get("Shelf Life")),
      rh_at_installation: rhApplicable ? toId(rhValue) : null,
      equipment_section: get("Sub Department"),
      // No "Equipment Type" field on any category's form (removed by product direction) — matches
      // the backend, which excludes `equipment_type` from Meta.fields on every category serializer.
    };
  }

  /**
   * Builds the payload for `POST transaction/cat*`. Local Purchase now shares the Survey & Demand
   * field set (see FIELD_SPECS — explicit product direction), so it shares this same payload shape
   * too; `createCategoryTransaction` still routes each to its own category-specific endpoint.
   */
  buildCreatePayload(
    category: SfdCategory,
    sfdType: SfdTransactionType,
    formValue: Record<string, unknown>,
    serial: string,
    frame: FrameRange,
    checkVals: CheckVals,
    ref: SfdActionReferenceData,
  ): TransactionCreatePayload {
    const get = (name: string): string => (formValue[controlKey(name)] as string) ?? "";
    const isSystem = sfdType === "system";
    const equipmentLabel = get("Equipment Name");
    const sysNameValue = (formValue["sysName"] as string) ?? "";
    const common = this.buildCommonFields(category, sfdType, formValue, serial, frame, checkVals, ref);

    switch (category) {
      case "CAT III": {
        const payload: Cat3TransactionPayload = {
          ...common,
          new_equipment_name: isSystem ? undefined : equipmentLabel,
          new_system_name: isSystem ? equipmentLabel : sysNameValue || undefined,
          new_nomenclature: common.nomenclature,
          new_oem_name: get("New OEM Name"),
          new_supplier_name: get("New OEM Supplier Name"),
          new_oem_part_no: get("New OEM Part No"),
          new_serial_no: serial,
        };
        return payload;
      }
      case "Survey & Demand":
      case "Local Purchase": {
        const payload: SurveyDemandTransactionPayload = {
          ...common,
          removal_date: get("Removal Date") || undefined,
          authority_of_removal: get("Removal Authority"),
          new_installation_date: get("Date of Installation (New Eqpt)") || undefined,
          // "New Eqpt Serial Number" is the only serial control on this form (see isSerialSpec) —
          // it's the newly-installed equipment's serial, so it belongs in new_serial_no. There's no
          // confirmed source yet for the OLD equipment's serial that `serial_no` is meant to carry.
          new_serial_no: serial,
          installation_remark: get("Installation Remarks"),
          new_service_life: toId(get("Shelf Life (New Eqpt)")),
        };
        return payload;
      }
      default:
        return common;
    }
  }

  /**
   * Builds the payload for `PUT sfd-list/{id}/` — Update resolves to `SFDTransactionBaseSerializer`
   * regardless of the record's category (see TransactionCreateCommonFields's type doc), so it's
   * exactly the CAT I/II create field set; no per-category "new_*" fields are accepted here.
   */
  buildUpdatePayload(
    category: SfdCategory,
    sfdType: SfdTransactionType,
    formValue: Record<string, unknown>,
    serial: string,
    frame: FrameRange,
    checkVals: CheckVals,
    ref: SfdActionReferenceData,
  ): TransactionCreateCommonFields {
    return this.buildCommonFields(category, sfdType, formValue, serial, frame, checkVals, ref);
  }

  /**
   * Submits an Add/Update SFD action. Create POSTs to the category-specific `transaction/cat*`
   * endpoint; Update PUTs to `sfd-list/{id}/` (no per-category update route was given) — both now
   * share the same field set (buildCommonFields), Update just omits the per-category "new_*" ones.
   */
  async submitAction(input: {
    category: SfdCategory;
    sfdType: SfdTransactionType;
    formValue: Record<string, unknown>;
    serial: string;
    frame: FrameRange;
    checkVals: CheckVals;
    ref: SfdActionReferenceData;
    isEditing: boolean;
    recordId?: string | number;
  }): Promise<SfdActionSubmitResult> {
    const { category, sfdType, formValue, serial, frame, checkVals, ref, isEditing, recordId } = input;
    try {
      if (isEditing && recordId) {
        const payload = this.buildUpdatePayload(category, sfdType, formValue, serial, frame, checkVals, ref);
        await firstValueFrom(this.api.updateTransaction(recordId, payload));
      } else {
        const payload = this.buildCreatePayload(category, sfdType, formValue, serial, frame, checkVals, ref);
        await firstValueFrom(this.api.createCategoryTransaction(category, payload));
      }
      return { ok: true };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  /** Change Serial Number form prefill — `GET sfd-list/{id}/update_sr_no_details/`. Returns `null`
   * on failure so the form can fall back to the grid row's own fields instead of blocking. */
  async loadUpdateSrNoDetails(equipmentShipId: string | number): Promise<RawUpdateSrNoDetails | null> {
    return firstValueFrom(this.api.getUpdateSrNoDetails(equipmentShipId)).catch(() => null);
  }

  /**
   * "serial" mode is the Change Serial flow — `POST sfd-list/{id}/update_sr_no/`, which writes a
   * `RemoveEquipmentRequest` with `request_type: 2`. "update" mode is the qty/serial Record Edit
   * modal — a direct PATCH on the real `EquipmentTransaction` row.
   */
  async submitRecordEdit(
    row: SfdActionRow,
    mode: RecordEditMode,
    formValue: {
      serial: string;
      qty: string;
      equipmentNomenclature?: string;
      currentSrNo?: string;
      subDept?: string;
      maintopNo?: string;
      removalAuthority?: string;
      removalDate?: string;
      installationDate?: string;
    },
  ): Promise<SfdActionSubmitResult> {
    try {
      if (mode === "serial") {
        // `row.*` is the grid's cached SfdActionRow — it can lag or be blank for fields the backend
        // now sources from `update_sr_no_details/` (see `RawUpdateSrNoDetails`), so the caller-supplied
        // values (already reconciled against that fetch) take priority; `row` is only a last-resort.
        const payload: UpdateSerialNoPayload = {
          equipment_nomenclature: formValue.equipmentNomenclature || row.nomen,
          current_sr_no: formValue.currentSrNo || row.serial,
          sub_dept: formValue.subDept || row.dept,
          maintop_no: formValue.maintopNo || row.maintop,
          new_sr_no: formValue.serial,
          removal_authority: formValue.removalAuthority ?? "",
          removal_date: formValue.removalDate ?? "",
          installation_date: formValue.installationDate ?? "",
        };
        await firstValueFrom(this.api.updateSerialNumber(row.code, payload));
      } else {
        await firstValueFrom(
          this.api.patchTransaction(row.code, {
            no_of_fits: formValue.qty ? Number(formValue.qty) : null,
            equipment_sr_no: formValue.serial || undefined,
          }),
        );
      }
      return { ok: true };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  /** Dependency check before Remove — flattens `open_defects`/`maintenance_routines` into one list for
   * the "choose how to proceed" screen. Defends against either list coming back missing/null (not just
   * `[]`) so a malformed response can't throw and strand the Remove flow on its default stage. */
  async loadOpenDependencies(equipmentShipId: string | number): Promise<DefectRecord[]> {
    const deps = await firstValueFrom(this.api.getOpenDependencies(equipmentShipId)).catch(() => null);
    if (!deps) return [];
    const defects: DefectRecord[] = (deps.open_defects ?? []).map((d) => ({
      id: d.defect_no,
      type: "Defect",
      desc: d.title,
      raised: "—",
      priority: d.severity ?? "—",
      status: d.status,
    }));
    const routines: DefectRecord[] = (deps.maintenance_routines ?? []).map((r) => ({
      id: r.routine_no,
      type: "Routine",
      desc: r.title,
      raised: r.due_date ?? "—",
      priority: "—",
      status: r.status,
    }));
    return [...defects, ...routines];
  }

  /** Removal Details form prefill — `GET sfd-list/{id}/remove-details/`. Returns `null` on failure so the
   * form can fall back to the grid row's own fields instead of blocking the Remove flow. */
  async loadRemovalDetails(equipmentShipId: string | number): Promise<RawRemovalDetails | null> {
    return firstValueFrom(this.api.getRemovalDetails(equipmentShipId)).catch(() => null);
  }

  /** Removal Details form submit — `POST sfd-list/{id}/remove/`, writes a `RemoveEquipmentRequest` (`request_type: 1`). */
  async submitRemoval(
    row: SfdActionRow,
    form: {
      removalDate: string;
      authority: string;
      remarks: string;
      equipmentNomenclature?: string;
      equipmentSrNo?: string;
      subDept?: string;
      compartmentName?: string;
    },
  ): Promise<SfdActionSubmitResult> {
    try {
      // `row.*` is the grid's cached SfdActionRow — it can be blank for fields the backend now
      // sources from `remove-details/` (see `RawRemovalDetails`), so the caller-supplied values
      // (already reconciled against that fetch, and what's actually shown in the form) take
      // priority; `row` is only a last-resort fallback.
      const payload: RemovalRequestPayload = {
        equipment_nomenclature: form.equipmentNomenclature || row.nomen,
        equipment_sr_no: form.equipmentSrNo || row.serial,
        sub_dept: form.subDept || row.dept,
        compartment_name: form.compartmentName || row.compartment,
        removal_date: form.removalDate,
        removal_authority: form.authority,
        removal_remark: form.remarks,
      };
      await firstValueFrom(this.api.submitRemoval(row.code, payload));
      return { ok: true };
    } catch (err) {
      return toErrorResult(err);
    }
  }

  /** "View Approval Status" grid — GET approval-tracking/, a flat array combining Remove + Change Sr. No. requests. */
  async loadApprovalTracking(): Promise<ApprovalSfdRow[]> {
    const rows = await firstValueFrom(this.api.getApprovalTracking());
    return rows.map((r) => ({
      id: r.request_id,
      eqp: r.equipment || "—",
      cat: categoryFromBodyValue(r.transaction_category),
      by: r.submitted_by || "—",
      date: r.submitted ?? "—",
      status: r.status,
      officer: r.insma_officer || "—",
      remarks: r.insma_remarks || "—",
      approveDate: r.approve_date || "—",
      lastUpdatedDate: r.updated_date || "—",
      requestType: r.category.toLowerCase() as "remove" | "change",
      transactionCategoryRaw: r.transaction_category,
    }));
  }

  /**
   * Resubmits a "Returned" approval request — `PUT approval-tracking/?request_id=...`. `row` is
   * the pre-edit `ApprovalSfdRow` (for `requestType`/`transactionCategoryRaw`/current
   * `insma_remarks`, which must be echoed back unchanged or the backend blanks them out — see
   * `ApprovalTrackingUpdatePayload`'s doc), `formValue` is what the correction form actually edited.
   */
  async submitApprovalCorrection(
    row: ApprovalSfdRow,
    formValue: { eqp: string; cat: string; by: string; date: string; correctionNote: string },
  ): Promise<SfdActionSubmitResult> {
    const payload: ApprovalTrackingUpdatePayload = {
      category: row.requestType,
      equipment: formValue.eqp,
      transaction_category: CATEGORY_TO_BODY_VALUE[formValue.cat as SfdCategory] ?? row.transactionCategoryRaw,
      submitted_by: formValue.by,
      submitted: formValue.date,
      insma_remarks: row.remarks === "—" ? "" : row.remarks,
      amendment_note: formValue.correctionNote || "",
    };
    try {
      await firstValueFrom(this.api.updateApprovalTracking(row.id, payload));
      return { ok: true };
    } catch (err) {
      return toErrorResult(err);
    }
  }
}
