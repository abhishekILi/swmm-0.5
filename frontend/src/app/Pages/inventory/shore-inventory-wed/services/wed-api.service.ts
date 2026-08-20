import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { Observable, combineLatest, forkJoin, of, throwError } from "rxjs";
import { map, shareReplay, switchMap } from "rxjs/operators";

import { environment } from "../../../../../environments/environment";
import {
  ApprovalEntry,
  IifHistoryEntry,
  NormalDemandHistoryEntry,
  RioHistoryEntry,
  WedCartEntry,
  WedDashboardCounts,
  WedItem,
} from "../models/wed.model";
import {
  BackendCombinedOutboxEntry,
  BackendCombinedOutboxResponse,
  BackendDemandEntry,
  BackendDemandPendingListResponse,
  BackendPendingDemand,
  BackendPendingPts,
  BackendPendingSurvey,
  BackendPtsPendingListResponse,
  BackendReceiveDemand,
  BackendReceiveQueueDemand,
  BackendSurveyPendingListResponse,
  BackendWedExternalSyncResponse,
  BackendWedIif,
  BackendWlmsDashboard,
  BackendWlmsEquipment,
  BackendWlmsSpare,
  BackendWlmsSyncResponse,
  ObsEquipmentClassLookup,
  ObsSpareLookup,
} from "../models/wlms-backend.model";

export type WedCartKind = "survey" | "pts" | "demand" | "receive" | "pts-rio-pending" | "iif";

interface WedLookups {
  equipment: Map<number, BackendWlmsEquipment>;
  spares: Map<number, BackendWlmsSpare>;
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

/** Maps a combined-outbox row's `spare_cart_name` to the URL segment for its per-kind
 * approval-workflow actions (`{segment}/{pk}/mark-synced/` etc). */
const WORKFLOW_URL_SEGMENT: Record<string, string> = {
  Survey: "survey",
  PTS: "pts",
  Demand: "demand",
  IIF: "wlmsiif",
};

/**
 * Shore Inventory - WED API — talks to `backend/wlms` (`api/v1/wlms/...`), with a couple of
 * cross-app lookups against `backend/obs` (`api/v1/onboard-spares/...`) since Survey/PTS/Demand/
 * IIF entries can originate from either a WED-side `WLMSSpare` or an onboard `obs.Spares` row.
 *
 * Like `ObsApiService`, backend serializers here are id-only / snake_case; every method joins
 * the raw response against cached lookups (`lookups$`) before returning the camelCase UI DTOs
 * from `../models/wed.model.ts`. A few methods have no working backend endpoint yet (`BACKEND
 * GAP` comments) and fail loudly via `throwError` (or return `[]` for read endpoints).
 */
@Injectable({ providedIn: "root" })
export class WedApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}api/v1/wlms/`;
  private readonly obsBaseUrl = `${environment.apiUrl}api/v1/onboard-spares/`;

  private readonly wlmsEquipmentById$ = this.http
    .get<BackendWlmsEquipment[]>(`${this.baseUrl}itemsearchwlms/equipments/`)
    .pipe(
      map((rows) => new Map(rows.map((row) => [row.id, row]))),
      shareReplay(1),
    );

  private readonly wlmsSparesById$ = this.http.get<BackendWlmsSpare[]>(`${this.baseUrl}itemsearchwlms/`).pipe(
    map((rows) => new Map(rows.map((row) => [row.id, row]))),
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

  /** Only needed to join `wlmsreceivelist/` rows (which reference a demand by id) back to the
   * WED/OBS spare that demand was for. */
  private readonly demandDetailsById$ = this.http.get<BackendDemandEntry[]>(`${this.baseUrl}wlmsdemanddetails/`).pipe(
    map((rows) => new Map(rows.map((row) => [row.id, row]))),
    shareReplay(1),
  );

  private readonly lookups$: Observable<WedLookups> = combineLatest([
    this.wlmsEquipmentById$,
    this.wlmsSparesById$,
    this.obsSparesById$,
    this.obsEquipmentClassById$,
  ]).pipe(
    map(([equipment, spares, obsSpares, obsEquipmentClasses]) => ({
      equipment,
      spares,
      obsSpares,
      obsEquipmentClasses,
    })),
    shareReplay(1),
  );

  // ---------------------------------------------------------------------------------------
  // Item search
  // ---------------------------------------------------------------------------------------

  getItems(): Observable<WedItem[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http
          .get<BackendWlmsSpare[]>(`${this.baseUrl}itemsearchwlms/`)
          .pipe(map((rows) => rows.map((row) => this.adaptWedItem(row, lookups)))),
      ),
    );
  }

  // ---------------------------------------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------------------------------------

  getDashboardCounts(): Observable<WedDashboardCounts> {
    return forkJoin({
      dashboard: this.http.get<BackendWlmsDashboard>(`${this.baseUrl}dashboardwlms/`),
      outstandingDemands: this.http.get<BackendReceiveQueueDemand[]>(`${this.baseUrl}demand/receive-queue/`),
      ptsRioSurveyPending: this.http.get<unknown[]>(`${this.baseUrl}ptsraised_surveypending/`),
    }).pipe(
      map(({ dashboard, outstandingDemands, ptsRioSurveyPending }) => ({
        surveyInProgress: dashboard.pending_surveys,
        demandInProgress: dashboard.pending_demands,
        ptsDemandInProgress: dashboard.pending_pts,
        outstandingDemands: outstandingDemands.length,
        iifInProgress: dashboard.pending_iif,
        // BACKEND GAP: `ptsraised_surveypending/` isn't filtered separately from the plain PTS
        // list yet (see getCart()'s "pts-rio-pending" case below) — this is the closest real count.
        ptsRioSurveyPending: ptsRioSurveyPending.length,
      })),
    );
  }

  // ---------------------------------------------------------------------------------------
  // Spares Transaction Carts (Survey / PTS / Demand / Receive / IIF / PTS-RIO-Pending)
  // ---------------------------------------------------------------------------------------

  getCart(kind: WedCartKind): Observable<WedCartEntry[]> {
    switch (kind) {
      case "survey":
        return this.getSurveyCart();
      case "pts":
        return this.getPtsCart();
      case "pts-rio-pending":
        // BACKEND GAP: `ptsraised_surveypending/` currently aliases the exact same view as
        // `raisepts/` (no server-side filter distinguishes "survey pending" from plain PTS) —
        // using the annotated pending-PTS list as the closest available real data.
        return this.getPtsCart();
      case "demand":
        return this.getDemandCart();
      case "receive":
        return this.getReceiveCart();
      case "iif":
        return this.getIifCart();
    }
  }

  private getSurveyCart(): Observable<WedCartEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http.get<BackendSurveyPendingListResponse>(`${this.baseUrl}wlmssurveylist/`).pipe(
          map((response) => response.pending_surveys.map((row) => this.adaptPendingEntry(row, lookups))),
        ),
      ),
    );
  }

  private getPtsCart(): Observable<WedCartEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http.get<BackendPtsPendingListResponse>(`${this.baseUrl}wlmsptslist/`).pipe(
          map((response) => response.pending_pts.map((row) => this.adaptPendingEntry(row, lookups))),
        ),
      ),
    );
  }

  private getDemandCart(): Observable<WedCartEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http.get<BackendDemandPendingListResponse>(`${this.baseUrl}wlmsdemandlist/`).pipe(
          map((response) => response.pending_demands.map((row) => this.adaptPendingEntry(row, lookups))),
        ),
      ),
    );
  }

  private getIifCart(): Observable<WedCartEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http
          .get<BackendWedIif[]>(`${this.baseUrl}wlmsiif/`)
          .pipe(map((rows) => rows.map((row) => this.adaptIifCartEntry(row, lookups)))),
      ),
    );
  }

  private getReceiveCart(): Observable<WedCartEntry[]> {
    return combineLatest([this.lookups$, this.demandDetailsById$]).pipe(
      switchMap(([lookups, demandsById]) =>
        this.http
          .get<BackendReceiveDemand[]>(`${this.baseUrl}wlmsreceivelist/`)
          .pipe(map((rows) => rows.map((row) => this.adaptReceiveCartEntry(row, demandsById, lookups)))),
      ),
    );
  }

  sendCartForHodApproval(kind: WedCartKind, ids: string[]): Observable<void> {
    const body = { ids: ids.map(Number) };
    switch (kind) {
      case "survey":
        return this.http.post(`${this.baseUrl}survey_send_hod_approval/`, body).pipe(map(() => void 0));
      case "pts":
      case "pts-rio-pending":
        return this.http.post(`${this.baseUrl}pts_send_hod_approval/`, body).pipe(map(() => void 0));
      case "demand":
        return this.http.post(`${this.baseUrl}demand_send_hod_approval/`, body).pipe(map(() => void 0));
      case "iif":
        // BACKEND GAP: IIF has no bulk-send route (only single-detail send-for-approval) —
        // loop it.
        return forkJoin(
          ids.map((id) => this.http.post(`${this.baseUrl}wlmsiif/${id}/send-for-approval/`, {})),
        ).pipe(map(() => void 0));
      case "receive":
        return throwError(() => new Error("The Receive cart has no HOD approval step."));
    }
  }

  /** No per-kind selection exists for this action — `send-common-api/` marks every
   * approved-but-unsynced Survey/PTS/Demand/IIF entry (department-scoped) as synced locally in
   * one call, regardless of which cart tab the button was clicked from. */
  syncCartWithWlms(_kind: WedCartKind): Observable<BackendWlmsSyncResponse> {
    return this.http.post<BackendWlmsSyncResponse>(`${this.baseUrl}send-common-api/`, {});
  }

  raiseIif(kind: WedCartKind, ids: string[]): Observable<void> {
    if (kind !== "iif" || !ids.length) {
      return throwError(() => new Error(`Raising an IIF from the "${kind}" cart is not supported.`));
    }
    // The "Raise IIF" button only appears on the IIF cart (see shore-inventory-wed.routes.ts),
    // so these ids are WEDIIF entry pks, not onboard-spare ids — IIF has no bulk
    // send-for-approval route, so each selected pending entry is submitted individually.
    return forkJoin(
      ids.map((id) => this.http.post(`${this.baseUrl}wlmsiif/${id}/send-for-approval/`, {})),
    ).pipe(map(() => void 0));
  }

  // ---------------------------------------------------------------------------------------
  // HOD Approval (combined outbox — approved-awaiting-sync items across all 4 workflows)
  // ---------------------------------------------------------------------------------------

  getApprovalList(): Observable<ApprovalEntry[]> {
    return this.lookups$.pipe(
      switchMap((lookups) =>
        this.http
          .get<BackendCombinedOutboxResponse>(`${this.baseUrl}wlmsoutbox/`)
          .pipe(map((response) => response.pts_entries.map((row) => this.adaptApprovalEntry(row, lookups)))),
      ),
    );
  }

  sendApprovalsToWlms(ids: string[]): Observable<void> {
    // `ApprovalEntry.id` is composite (`"<Kind>:<pk>"`, set in adaptApprovalEntry) because the
    // combined outbox merges 4 independently-numbered backend tables — the kind prefix is
    // required to call the correct table's mark-synced endpoint.
    const requests: Observable<unknown>[] = [];
    for (const compositeId of ids) {
      const [kind, pk] = compositeId.split(":");
      const segment = kind ? WORKFLOW_URL_SEGMENT[kind] : undefined;
      if (!segment || !pk) continue;
      requests.push(this.http.post(`${this.baseUrl}${segment}/${pk}/mark-synced/`, {}));
    }
    if (!requests.length) return of(void 0);
    return forkJoin(requests).pipe(map(() => void 0));
  }

  // ---------------------------------------------------------------------------------------
  // History
  //
  // BACKEND GAP: `getNormalDemandHistory`/`getPtsDemandHistory`/`getRioDemandHistory` have no
  // backend aggregation that joins Survey -> Demand -> Receive (or a RIO-specific model — no
  // such model exists) into the flattened shape these screens expect. `wlmshistory/` returns
  // the current WLMSSpare master list, not a transaction history. Stubbed until the backend
  // adds a dedicated history endpoint.
  // ---------------------------------------------------------------------------------------

  getNormalDemandHistory(): Observable<NormalDemandHistoryEntry[]> {
    console.warn(
      "[WedApiService] getNormalDemandHistory: no backend aggregation for this shape yet — returning an empty list.",
    );
    return of([]);
  }

  getPtsDemandHistory(): Observable<NormalDemandHistoryEntry[]> {
    console.warn(
      "[WedApiService] getPtsDemandHistory: no backend aggregation for this shape yet — returning an empty list.",
    );
    return of([]);
  }

  getRioDemandHistory(): Observable<RioHistoryEntry[]> {
    console.warn(
      "[WedApiService] getRioDemandHistory: no RIO-specific backend model/aggregation exists yet — returning an empty list.",
    );
    return of([]);
  }

  getIifHistory(): Observable<IifHistoryEntry[]> {
    return this.obsSparesById$.pipe(
      switchMap((obsSparesById) =>
        this.http.get<BackendWedIif[]>(`${this.baseUrl}wlmsiifhistory/`).pipe(
          map((rows) =>
            rows.filter((row) => row.is_sync).map((row) => this.adaptIifHistoryEntry(row, obsSparesById)),
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------------------
  // References > Masters — external WED sync
  //
  // BACKEND GAP: unlike the URL gaps elsewhere in this file, these two have no backend route
  // AND no view at all (confirmed via repo-wide search) — this is new backend work, not a
  // missing `path()` registration.
  // ---------------------------------------------------------------------------------------

  /** Real, routed endpoint — but the external WED source it would pull from isn't configured in
   * this deployment, so it always responds with `status: "warning"` and 0 created/updated rather
   * than 404ing or throwing. Surfaced to the user as-is rather than swallowed. */
  syncEquipmentFromWed(): Observable<BackendWedExternalSyncResponse> {
    return this.http.post<BackendWedExternalSyncResponse>(`${this.baseUrl}sync-equipment-from-wed/`, {});
  }

  syncSparesFromWed(): Observable<BackendWedExternalSyncResponse> {
    return this.http.post<BackendWedExternalSyncResponse>(`${this.baseUrl}sync-spares-from-wed/`, {});
  }

  // ---------------------------------------------------------------------------------------
  // Adapters
  // ---------------------------------------------------------------------------------------

  private adaptWedItem(row: BackendWlmsSpare, lookups: WedLookups): WedItem {
    const equipment = row.eqpt != null ? lookups.equipment.get(row.eqpt) : undefined;
    return {
      equipmentName: equipment?.eqpt_name ?? "",
      patternNo: row.item_code ?? "",
      itemDescription: row.item_desc ?? "",
      denomination: row.denom_id ?? "",
      itemCategory: row.category ?? "",
      inventoryType: row.typeofspare ?? "",
    };
  }

  /** Survey/PTS/Demand cart entries reference either a WED-side `WLMSSpare` (`wed_spares_id`)
   * or an onboard `obs.Spares` row (`obs_spare_id`) — exactly one is set. */
  private resolveItemFields(
    wedSpareId: number | null,
    obsSpareId: number | null,
    lookups: WedLookups,
  ): ResolvedItemFields {
    if (wedSpareId != null) {
      const spare = lookups.spares.get(wedSpareId);
      return {
        itemCode: spare?.item_code ?? "",
        itemDescription: spare?.item_desc ?? "",
        denomination: spare?.denom_id ?? "",
        category: spare?.category ?? "",
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

  /** `PendingRow` is a union of row shapes that carry the demand number under different
   *  keys — pick whichever is present, preferring the PTS-specific field when both exist. */
  private resolveDemandNo(row: PendingRow): string | null {
    if ("PTS_demand_no" in row) return row.PTS_demand_no ?? row.demand_no;
    if ("demand_no" in row) return row.demand_no;
    return "";
  }

  private adaptPendingEntry(row: PendingRow, lookups: WedLookups): WedCartEntry {
    const fields = this.resolveItemFields(row.wed_spares_id, row.obs_spare_id, lookups);
    const scrapQty = typeof row.scrap_qty === "number" ? row.scrap_qty : Number(row.scrap_qty);
    const demandNo = this.resolveDemandNo(row);
    const surveyNo = "survey_no" in row ? row.survey_no : "";
    return {
      id: String(row.id),
      syncStatus: row.is_sync ? "Synced" : "Not Synced",
      itemCode: fields.itemCode,
      itemDescription: fields.itemDescription,
      denomination: fields.denomination,
      qty: Number.isFinite(scrapQty) ? scrapQty : undefined,
      category: fields.category,
      hodApprovalStatus: row.is_approval ? "Approved" : "Pending",
      dartNo: row.dart_number || "",
      demandNo: demandNo || "",
      surveyNo: surveyNo || "",
      equipmentNomenclature: row.equipment_nomenclature || "",
      equipmentClass: row.equipment_class && row.equipment_class !== "-" ? row.equipment_class : "",
    };
  }

  private adaptIifCartEntry(row: BackendWedIif, lookups: WedLookups): WedCartEntry {
    const obsSpare = row.spare_id != null ? lookups.obsSpares.get(row.spare_id) : undefined;
    const equipmentClass = obsSpare ? lookups.obsEquipmentClasses.get(obsSpare.equipment_class)?.name ?? "" : "";
    return {
      id: String(row.id),
      syncStatus: row.is_sync ? "Synced" : "Not Synced",
      itemCode: obsSpare?.pattern_number ?? "",
      itemDescription: obsSpare?.description ?? "",
      category: obsSpare?.category ?? "",
      hodApprovalStatus: row.is_approval ? "Approved" : "Pending",
      equipmentClass,
      swmmPatternNo: obsSpare?.pattern_number ?? "",
      // `incattingStatus` has no backend field on WEDIIF — left unset.
    };
  }

  private adaptReceiveCartEntry(
    row: BackendReceiveDemand,
    demandsById: Map<number, BackendDemandEntry>,
    lookups: WedLookups,
  ): WedCartEntry {
    const demand = row.demand_details != null ? demandsById.get(row.demand_details) : undefined;
    const fields = demand
      ? this.resolveItemFields(demand.wed_spares_id, demand.obs_spare_id, lookups)
      : { itemCode: "", itemDescription: "", denomination: "", category: "" };
    const wedIssueQty = demand ? Number(demand.demand_qty) : NaN;
    return {
      id: String(row.id),
      // ReceiveDemandDetails has no is_sync field of its own — a "received" status is the
      // closest real signal that this line is complete.
      syncStatus: (row.demand_status ?? "").toLowerCase() === "received" ? "Synced" : "Not Synced",
      itemCode: fields.itemCode,
      itemDescription: fields.itemDescription,
      denomination: fields.denomination,
      category: fields.category,
      qty: row.demand_quantity,
      issueStatus: row.demand_status ?? "",
      receiptStatus: row.demand_status ?? "",
      surveyNo: demand?.survey_no ?? "",
      vettingRemarks: demand?.remarks ?? "",
      wedIssueQty: Number.isFinite(wedIssueQty) ? wedIssueQty : undefined,
      receivedQty: row.received_qty ?? undefined,
      demandNo: row.demand_number || demand?.demand_no || "",
      dartNo: row.dart_no ?? "",
    };
  }

  private adaptApprovalEntry(row: BackendCombinedOutboxEntry, lookups: WedLookups): ApprovalEntry {
    const kind = row.spare_cart_name;
    const obsSpareId = row.obs_spare_id ?? row.spare_id ?? null;
    const fields = this.resolveItemFields(row.wed_spares_id ?? null, obsSpareId, lookups);
    const obsSpare = obsSpareId != null ? lookups.obsSpares.get(obsSpareId) : undefined;

    let equipmentClass = "";
    if (kind === "IIF") {
      // For IIF rows the backend already resolves `equipment_nomenclature` to the OBS spare's
      // equipment_class name (see `wlms_combined_outbox` in backend/wlms/views.py).
      equipmentClass = row.equipment_nomenclature && row.equipment_nomenclature !== "—" ? row.equipment_nomenclature : "";
    } else if (row.wed_spares_id != null) {
      equipmentClass = this.resolveEquipmentName(row.wed_spares_id, lookups);
    } else if (obsSpare) {
      equipmentClass = lookups.obsEquipmentClasses.get(obsSpare.equipment_class)?.name ?? "";
    }

    const qty = typeof row.quantity_required === "number" ? row.quantity_required : Number(row.quantity_required);
    return {
      id: `${kind}:${row.id}`,
      spareCartName: kind,
      patternNo: fields.itemCode,
      spareDescription: fields.itemDescription,
      dartNo: row.dart_number && row.dart_number !== "—" ? row.dart_number : "",
      equipmentClass,
      category: fields.category,
      critical: obsSpare?.critical ?? false,
      qty: Number.isFinite(qty) ? qty : 0,
    };
  }

  private adaptIifHistoryEntry(row: BackendWedIif, obsSparesById: Map<number, ObsSpareLookup>): IifHistoryEntry {
    const obsSpare = row.spare_id != null ? obsSparesById.get(row.spare_id) : undefined;
    return {
      id: String(row.id),
      // Not populated: fetching WEDIIFDetails.iif_no would call an endpoint that auto-creates
      // a details row as a side effect of a GET (see WEDIIFDetailsViewSet.retrieve in
      // backend/wlms/views.py) — a passive history view must not trigger that write.
      iifRequisitionNo: "",
      iifRequisitionDate: "",
      wlmsSyncDate: row.sync_date ?? "",
      swmmItemCode: obsSpare?.pattern_number ?? "",
      wedItemCode: "",
      incattingCompletionDate: "",
    };
  }

  private resolveEquipmentName(wedSpareId: number | null, lookups: WedLookups): string {
    if (wedSpareId == null) return "";
    const spare = lookups.spares.get(wedSpareId);
    if (spare?.eqpt == null) return "";
    return lookups.equipment.get(spare.eqpt)?.eqpt_name ?? "";
  }
}
