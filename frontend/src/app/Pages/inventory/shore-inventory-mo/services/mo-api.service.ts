import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { Observable, combineLatest, forkJoin, of, throwError } from "rxjs";
import { map, shareReplay, switchMap } from "rxjs/operators";

import { environment } from "../../../../../environments/environment";
import {
  ApprovalEntry,
  IifHistoryEntry,
  MoCartEntry,
  MoDashboardCounts,
  MoItem,
  NormalDemandHistoryEntry,
  RioHistoryEntry,
  Vendor,
} from "../models/mo.model";
import {
  BackendIif,
  BackendIlmsSyncResponse,
  BackendItem,
  BackendItemSearchResponse,
  BackendMergedReceiveListResponse,
  BackendPendingDemand,
  BackendPendingPts,
  BackendPendingSurvey,
  BackendReceiveRow,
  BackendVendor,
  ObsEquipmentClassLookup,
  ObsSpareLookup,
} from "../models/ilms-backend.model";

export type MoCartKind = "survey" | "pts" | "demand" | "receive" | "pts-rio-pending" | "iif";

interface MoLookups {
  items: Map<string, BackendItem>;
  obsSpares: Map<number, ObsSpareLookup>;
  obsEquipmentClasses: Map<number, ObsEquipmentClassLookup>;
}

interface ResolvedItemFields {
  itemCode: string;
  itemDescription: string;
  denomination: string;
  category: string;
}

type PendingRow = BackendPendingSurvey | BackendPendingPts | BackendPendingDemand;
type WorkflowKind = "Survey" | "PTS" | "Demand";

/** Maps a workflow kind to its URL segment for `{segment}/{pk}/mark-synced/` etc. */
const WORKFLOW_URL_SEGMENT: Record<WorkflowKind, string> = {
  Survey: "survey",
  PTS: "pts",
  Demand: "demand",
};

/**
 * Shore Inventory - MO API — talks to `backend/ilms` (`api/v1/ilms/...`), with a couple of
 * cross-app lookups against `backend/obs` (`api/v1/onboard-spares/...`) since Survey/PTS/Demand/
 * IIF entries can originate from either an ILMS-side `Item` or an onboard `obs.Spares` row.
 *
 * Like `ObsApiService`/`WedApiService`, backend serializers here are id-only / snake_case; every
 * method joins the raw response against cached lookups (`lookups$`) before returning the
 * camelCase UI DTOs from `../models/mo.model.ts`. A few methods have no working backend endpoint
 * yet (`BACKEND GAP` comments) and fail loudly via `throwError` (or return `[]`/best-effort
 * partial data for read endpoints) instead of silently faking success.
 */
@Injectable({ providedIn: "root" })
export class MoApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}api/v1/ilms/`;
  private readonly obsBaseUrl = `${environment.apiUrl}api/v1/onboard-spares/`;

  /** Full (uncapped) Item master, keyed by item_code — used to join item details onto the
   * id-only Survey/PTS/Demand rows. `item_search/` (used by `getItems()`) is capped at 100 and
   * unsuitable as a general-purpose lookup. */
  private readonly itemsByCode$ = this.http.get<BackendItem[]>(`${this.baseUrl}item-search-list/`).pipe(
    map((rows) => new Map(rows.map((row) => [row.item_code, row]))),
    shareReplay(1),
  );

  private readonly obsSparesById$ = this.http.get<ObsSpareLookup[]>(`${this.obsBaseUrl}view/`).pipe(
    map((rows) => new Map(rows.map((row) => [row.id, row]))),
    shareReplay(1),
  );

  private readonly obsEquipmentClassById$ = this.http
    .get<ObsEquipmentClassLookup[]>(`${this.obsBaseUrl}equipment_class/`)
    .pipe(
      map((rows) => new Map(rows.map((row) => [row.id, row]))),
      shareReplay(1),
    );

  private readonly lookups$: Observable<MoLookups> = combineLatest([
    this.itemsByCode$,
    this.obsSparesById$,
    this.obsEquipmentClassById$,
  ]).pipe(
    map(([items, obsSpares, obsEquipmentClasses]) => ({ items, obsSpares, obsEquipmentClasses })),
    shareReplay(1),
  );

  // ---------------------------------------------------------------------------------------
  // Vendor / item search
  // ---------------------------------------------------------------------------------------

  /** `VendorSerializer` already returns the full record (address/GST/PAN/approval fields) — this
   * used to discard everything but code/name/class. `search_table` (`vendor_search/`) also exists
   * and literally includes a `ser` field matching the reference design's SER column, but caps
   * results at 100 rows with no equivalent "load everything" mode; `ser` is trivial to compute
   * client-side from row position instead, so `search-list` (uncapped) stays the source. */
  getVendors(): Observable<Vendor[]> {
    return this.http.get<BackendVendor[]>(`${this.baseUrl}vendor-search-list/`).pipe(
      map((rows) =>
        rows.map((row, index) => ({
          id: row.vendor_code,
          ser: index + 1,
          vendorCode: row.vendor_code,
          vendorName: row.name,
          vendorClass: row.vendor_class ?? "",
          addressee: row.addressee ?? "",
          addressLine1: row.address_line1 ?? "",
          addressLine2: row.address_line2 ?? "",
          addressLine3: row.address_line3 ?? "",
          city: row.city ?? "",
          state: row.state ?? "",
          pincode: row.pin_code ?? "",
          countryCode: row.country_code ?? "",
          remarks: row.remarks ?? "",
          gstNo: row.gst_no ?? "",
          pan: row.pan ?? "",
          approvedBy: row.approved_by ?? "",
          dateApproved: row.datetime_approved ?? "",
          dateBannedUpto: row.date_banned_upto ?? "",
        })),
      ),
    );
  }

  getItems(): Observable<MoItem[]> {
    return this.http.get<BackendItemSearchResponse>(`${this.baseUrl}item_search/`).pipe(
      map((response) =>
        response.items.map((row) => ({
          itemCode: row.item_code,
          itemDescription: row.item_desc ?? "",
          crpCategory: row.crp_category ?? "",
          denomination: row.item_deno ?? "",
          // ILMS has no distinct "held onboard" flag — incat_yn ("in catalogue") is the closest
          // available signal.
          shipInventoryStatus: row.incat_yn ? "In Catalogue" : "Not In Catalogue",
          // item_search/ doesn't join a vendor onto each item (vendor linkage lives in
          // MoMappingTable, keyed differently) — left blank.
          vendorName: "",
          ilmsEquipmentDescription: row.nomenclature ?? "",
          equipmentCode: row.equipment_code ?? undefined,
        })),
      ),
    );
  }

  // ---------------------------------------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------------------------------------

  /** Every tile is sourced straight from the same list endpoint its "View more" navigates to
   * (`getCart()` below), not from `dashboard/`'s own aggregated counts — those don't line up with
   * what the cart grids actually show:
   * - Survey/PTS/Demand: `dashboard()`'s counts filter `ilms_spare_id__in=<MoMappingTable-scoped
   *   ids>` (`ilms/views.py` `_scoped_item_ids()`). Those three models carry the item on *either*
   *   `ilms_spare_id` or `obs_spare_id` — rows from an onboard (OBS) spare only ever populate
   *   `obs_spare_id`, so `ilms_spare_id__in=...` can never match them and the count silently
   *   stayed 0. Confirmed live: all 5 "To Be Surveyed" rows are OBS-originated.
   * - IIF: `dashboard.pending_iif` filters `is_sync=False` (a stricter "not yet synced" count),
   *   while the IIF cart grid (`iifcart/`, used here) lists every cart entry regardless of sync
   *   status — with today's data all rows are already `Synced`, so `pending_iif` read 0 while the
   *   grid still showed 5. Binding to `iifcart/` instead keeps the tile consistent with the page. */
  getDashboardCounts(): Observable<MoDashboardCounts> {
    return forkJoin({
      surveyInProgress: this.http.get<unknown[]>(`${this.baseUrl}mo_survey_list/`),
      demandInProgress: this.http.get<unknown[]>(`${this.baseUrl}mo_demand_list/`),
      ptsDemandInProgress: this.http.get<unknown[]>(`${this.baseUrl}mo_pts_list/`),
      outstandingDemands: this.http.get<unknown[]>(`${this.baseUrl}mo_receivedetail/`),
      iifInProgress: this.http.get<unknown[]>(`${this.baseUrl}iifcart/`),
      ptsRioSurveyPending: this.http.get<unknown[]>(`${this.baseUrl}ptsraised_surveypending/`),
    }).pipe(
      map(({ surveyInProgress, demandInProgress, ptsDemandInProgress, outstandingDemands, iifInProgress, ptsRioSurveyPending }) => ({
        surveyInProgress: surveyInProgress.length,
        demandInProgress: demandInProgress.length,
        ptsDemandInProgress: ptsDemandInProgress.length,
        outstandingDemands: outstandingDemands.length,
        iifInProgress: iifInProgress.length,
        // BACKEND GAP: `ptsraised_surveypending/` isn't filtered separately from the plain PTS
        // list yet (mirrors the equivalent gap in the wlms app) — closest real count available.
        ptsRioSurveyPending: ptsRioSurveyPending.length,
      })),
    );
  }

  // ---------------------------------------------------------------------------------------
  // Spares Transaction Carts
  // ---------------------------------------------------------------------------------------

  getCart(kind: MoCartKind): Observable<MoCartEntry[]> {
    switch (kind) {
      case "survey":
        return this.getWorkflowCart("mo_survey_list/");
      case "pts":
        return this.getWorkflowCart("mo_pts_list/");
      case "pts-rio-pending":
        // BACKEND GAP: `ptsraised_surveypending/` aliases the plain PTS list/create view (no
        // filter distinguishing "survey pending" PTS/RIO records) — reusing the annotated
        // pending-PTS list as the closest real data, same gap as in the wlms app.
        return this.getWorkflowCart("mo_pts_list/");
      case "demand":
        return this.getWorkflowCart("mo_demand_list/");
      case "receive":
        return this.getReceiveCart();
      case "iif":
        return this.getIifCart();
    }
  }

  private getWorkflowCart(path: string): Observable<MoCartEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http
          .get<PendingRow[]>(`${this.baseUrl}${path}`)
          .pipe(map((rows) => rows.map((row) => this.adaptPendingEntry(row, lookups)))),
      ),
    );
  }

  private getReceiveCart(): Observable<MoCartEntry[]> {
    return this.http.get<BackendMergedReceiveListResponse>(`${this.baseUrl}mo_receive_list/`).pipe(
      map((response) => response.entries.map((row, index) => this.adaptReceiveRow(row, index))),
    );
  }

  private getIifCart(): Observable<MoCartEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http
          .get<BackendIif[]>(`${this.baseUrl}iifcart/`)
          .pipe(map((rows) => rows.map((row) => this.adaptIifCartEntry(row, lookups)))),
      ),
    );
  }

  sendCartForHodApproval(kind: MoCartKind, ids: string[]): Observable<void> {
    const body = { ids: ids.map(Number) };
    switch (kind) {
      case "survey":
        return this.http.post(`${this.baseUrl}survey_send_hod_approval/`, body).pipe(map(() => void 0));
      case "pts":
      case "pts-rio-pending":
        return this.http.post(`${this.baseUrl}pts_send_hod_approval/`, body).pipe(map(() => void 0));
      case "demand":
        return this.http.post(`${this.baseUrl}demand_send_hod_approval/`, body).pipe(map(() => void 0));
      case "receive":
        return throwError(() => new Error("The Receive cart has no HOD approval step."));
      case "iif":
        return throwError(() => new Error("IIF entries have no HOD approval step in this backend."));
    }
  }

  /** pts_data_send_ilms/ and demand_data_send_ilms/ mark every approved-but-unsynced row as
   * synced (department-scoped) when called with no ids — this bulk-syncs the whole HOD-approved
   * backlog for that workflow rather than a specific selection, matching what "Sync with ILMS"
   * on the cart screen actually offers today (no row-level selection UI for this action). */
  syncCartWithIlms(kind: MoCartKind): Observable<BackendIlmsSyncResponse> {
    switch (kind) {
      case "pts":
      case "pts-rio-pending":
        return this.http.post<BackendIlmsSyncResponse>(`${this.baseUrl}pts_data_send_ilms/`, {});
      case "demand":
        return this.http.post<BackendIlmsSyncResponse>(`${this.baseUrl}demand_data_send_ilms/`, {});
      case "survey":
      case "receive":
      case "iif":
        // BACKEND GAP: no sync endpoint exists for these cart kinds.
        return throwError(
          () => new Error(`Syncing the "${kind}" cart with ILMS is not implemented on the backend yet.`),
        );
    }
  }

  // ---------------------------------------------------------------------------------------
  // HOD Approval (approved-awaiting-sync items, composed from the 3 workflow pending-lists)
  //
  // The backend's own combined inbox (`action/inbox/`) merges Survey/PTS/Demand under one
  // response key with no per-row type discriminator, so ids from the 3 independently-numbered
  // tables could collide — composing the "outbox" from each workflow's own pending-list instead
  // keeps a reliable `Kind:pk` composite id (see `sendApprovalsToIlms`).
  // ---------------------------------------------------------------------------------------

  getApprovalList(): Observable<ApprovalEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        forkJoin({
          survey: this.http.get<BackendPendingSurvey[]>(`${this.baseUrl}mo_survey_list/`),
          pts: this.http.get<BackendPendingPts[]>(`${this.baseUrl}mo_pts_list/`),
          demand: this.http.get<BackendPendingDemand[]>(`${this.baseUrl}mo_demand_list/`),
        }).pipe(
          map(({ survey, pts, demand }) => {
            const outbox: ApprovalEntry[] = [];
            const collect = (kind: WorkflowKind, rows: PendingRow[]) => {
              for (const row of rows) {
                if (row.is_hod && row.is_hod_approval && !row.is_sync) {
                  outbox.push(this.adaptApprovalEntry(kind, row, lookups));
                }
              }
            };
            collect("Survey", survey);
            collect("PTS", pts);
            collect("Demand", demand);
            return outbox;
          }),
        ),
      ),
    );
  }

  sendApprovalsToIlms(ids: string[]): Observable<void> {
    const requests: Observable<unknown>[] = [];
    for (const compositeId of ids) {
      const [kind, pk] = compositeId.split(":");
      const segment = kind ? WORKFLOW_URL_SEGMENT[kind as WorkflowKind] : undefined;
      if (!segment || !pk) continue;
      requests.push(this.http.post(`${this.baseUrl}${segment}/${pk}/mark-synced/`, {}));
    }
    if (!requests.length) return of(void 0);
    return forkJoin(requests).pipe(map(() => void 0));
  }

  // ---------------------------------------------------------------------------------------
  // History
  // ---------------------------------------------------------------------------------------

  getNormalDemandHistory(): Observable<NormalDemandHistoryEntry[]> {
    return this.getDemandHistory("mo_demand_list/");
  }

  getPtsDemandHistory(): Observable<NormalDemandHistoryEntry[]> {
    return this.getDemandHistory("mo_pts_list/");
  }

  /** BACKEND GAP: no RIO-specific model, field, or endpoint exists anywhere in the ilms app. */
  getRioDemandHistory(): Observable<RioHistoryEntry[]> {
    console.warn(
      "[MoApiService] getRioDemandHistory: no RIO-specific backend model/aggregation exists — returning an empty list.",
    );
    return of([]);
  }

  getIifHistory(): Observable<IifHistoryEntry[]> {
    return this.obsSparesById$.pipe(
      switchMap((obsSparesById) =>
        this.http.get<BackendIif[]>(`${this.baseUrl}iifhistory/`).pipe(
          map((rows) =>
            rows.filter((row) => row.is_sync).map((row) => this.adaptIifHistoryEntry(row, obsSparesById)),
          ),
        ),
      ),
    );
  }

  private getDemandHistory(path: string): Observable<NormalDemandHistoryEntry[]> {
    // BACKEND GAP: `mo_demand_list/`/`mo_pts_list/` are the only real data sources — there's no
    // dedicated "history" endpoint, so synced (is_sync=true) rows from the pending-list are used
    // as the closest real history. SurveyDetails/PTSDetails/DemandDetails carry no quantity or
    // date fields at all, so surveyNo/surveyDate/demandedQty/demandDate/moIssuedQty can't be
    // populated from real data.
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http.get<PendingRow[]>(`${this.baseUrl}${path}`).pipe(
          map((rows) =>
            rows.filter((row) => row.is_sync).map((row) => this.adaptDemandHistory(row, lookups)),
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------------------
  // Adapters
  // ---------------------------------------------------------------------------------------

  /** Survey/PTS/Demand entries reference either an ILMS-side `Item` (`ilms_spare_id`, a
   * item_code string) or an onboard `obs.Spares` row (`obs_spare_id`) — at most one is set. */
  private resolveItemFields(
    ilmsSpareId: string | null,
    obsSpareId: number | null,
    lookups: MoLookups,
  ): ResolvedItemFields {
    if (ilmsSpareId) {
      const item = lookups.items.get(ilmsSpareId);
      return {
        itemCode: item?.item_code ?? ilmsSpareId,
        itemDescription: item?.item_desc ?? "",
        denomination: item?.item_deno ?? "",
        category: item?.crp_category ?? "",
      };
    }
    if (obsSpareId != null) {
      const spare = lookups.obsSpares.get(obsSpareId);
      return {
        itemCode: spare?.pattern_number ?? "",
        itemDescription: spare?.description ?? "",
        denomination: "",
        category: spare?.category ?? "",
      };
    }
    return { itemCode: "", itemDescription: "", denomination: "", category: "" };
  }

  /** `PendingRow` is a union of demand/pts/survey rows that only one of `demand_number`
   *  or `pts_number` exists on at a time — pick whichever is present. */
  private resolveTrackingNumber(row: PendingRow): string {
    if ("demand_number" in row) return row.demand_number;
    if ("pts_number" in row) return row.pts_number;
    return "";
  }

  private adaptPendingEntry(row: PendingRow, lookups: MoLookups): MoCartEntry {
    const fields = this.resolveItemFields(row.ilms_spare_id, row.obs_spare_id, lookups);
    const qty = typeof row.quantity_required === "number" ? row.quantity_required : Number(row.quantity_required);
    const number = this.resolveTrackingNumber(row);
    const equipmentClass =
      row.equipment_class && row.equipment_class !== "-" && row.equipment_class !== "—" ? row.equipment_class : "";
    return {
      id: String(row.id),
      syncStatus: row.is_sync ? "Synced" : "Not Synced",
      itemCode: fields.itemCode,
      itemDescription: fields.itemDescription,
      denomination: fields.denomination,
      qty: Number.isFinite(qty) ? qty : 0,
      category: fields.category,
      hodApprovalStatus: row.is_hod_approval ? "Approved" : "Pending",
      dartNo: row.dart_number && row.dart_number !== "—" ? row.dart_number : "",
      ilmsDemandNo: number || "",
      demandNo: number || "",
      equipmentClass,
      equipmentNomenclature:
        row.equipment_nomenclature && row.equipment_nomenclature !== "—" ? row.equipment_nomenclature : "",
    };
  }

  private adaptIifCartEntry(row: BackendIif, lookups: MoLookups): MoCartEntry {
    const obsSpare = row.spare_id != null ? lookups.obsSpares.get(row.spare_id) : undefined;
    const equipmentClass = obsSpare ? lookups.obsEquipmentClasses.get(obsSpare.equipment_class)?.name ?? "" : "";
    return {
      id: String(row.id),
      syncStatus: row.is_sync ? "Synced" : "Not Synced",
      itemCode: obsSpare?.pattern_number ?? "",
      itemDescription: obsSpare?.description ?? "",
      denomination: "",
      // The IIF model carries no quantity field.
      qty: 0,
      category: obsSpare?.category ?? "",
      equipmentClass,
    };
  }

  private adaptReceiveRow(row: BackendReceiveRow, index: number): MoCartEntry {
    const qty = typeof row.demand_qty === "number" ? row.demand_qty : Number(row.demand_qty);
    return {
      // merged_receive_list rows are computed, not model instances — no backend id to reuse.
      id: `${row.source}-${index}-${row.demand_number || row.mo_item_code}`,
      // ReceiveDemandDetails-equivalent rows here carry no sync flag of their own.
      syncStatus: "Not Synced",
      itemCode: row.mo_item_code,
      itemDescription: row.item_description,
      denomination: row.denomination,
      qty: Number.isFinite(qty) ? qty : 0,
      category: row.crp_category,
      dartNo: row.dart_number && row.dart_number !== "—" ? row.dart_number : "",
      surveyNo: row.survey_number && row.survey_number !== "—" ? row.survey_number : "",
      demandNo: row.demand_number,
      moIssueStatus: row.in_progress_status,
      demandType: row.source,
      // BACKEND GAP: see `MoCartEntry.moIssueQty` — always "—" server-side today.
      moIssueQty:
        row.qty_issued_by_mo != null && String(row.qty_issued_by_mo) !== "—" ? String(row.qty_issued_by_mo) : "",
    };
  }

  private adaptApprovalEntry(kind: WorkflowKind, row: PendingRow, lookups: MoLookups): ApprovalEntry {
    const fields = this.resolveItemFields(row.ilms_spare_id, row.obs_spare_id, lookups);
    const obsSpare = row.obs_spare_id != null ? lookups.obsSpares.get(row.obs_spare_id) : undefined;
    const qty = typeof row.quantity_required === "number" ? row.quantity_required : Number(row.quantity_required);
    return {
      id: `${kind}:${row.id}`,
      spareCartName: kind,
      patternNo: fields.itemCode,
      spareDescription: fields.itemDescription,
      dartNo: row.dart_number && row.dart_number !== "—" ? row.dart_number : "",
      equipmentClass:
        row.equipment_class && row.equipment_class !== "-" && row.equipment_class !== "—" ? row.equipment_class : "",
      category: fields.category,
      critical: obsSpare?.critical ?? false,
      qty: Number.isFinite(qty) ? qty : 0,
    };
  }

  private adaptDemandHistory(row: PendingRow, lookups: MoLookups): NormalDemandHistoryEntry {
    const fields = this.resolveItemFields(row.ilms_spare_id, row.obs_spare_id, lookups);
    const number = this.resolveTrackingNumber(row);
    return {
      id: String(row.id),
      moItemCode: fields.itemCode,
      itemDescription: fields.itemDescription,
      category: fields.category,
      surveyNo: "",
      surveyDate: "",
      demandNo: number || "",
      demandedQty: 0,
      demandDate: "",
      moIssuedQty: 0,
      dartNo: row.dart_number && row.dart_number !== "—" ? row.dart_number : "",
    };
  }

  private adaptIifHistoryEntry(row: BackendIif, obsSparesById: Map<number, ObsSpareLookup>): IifHistoryEntry {
    const obsSpare = row.spare_id != null ? obsSparesById.get(row.spare_id) : undefined;
    return {
      id: String(row.id),
      // The IIF model carries no requisition number, dates, or equipment fields — `iifhistory/`
      // is just an alias of the plain IIF list on the backend, not a real history view.
      iifRequisitionNo: "",
      iifRequisitionDate: "",
      ilmsSyncDate: "",
      swmmItemCode: obsSpare?.pattern_number ?? "",
      moItemCode: "",
      incattingCompletionDate: "",
      equipmentClass: "",
      equipmentNomenclature: "",
    };
  }
}
