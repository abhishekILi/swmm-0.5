import { HttpClient, HttpErrorResponse, HttpParams } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { Observable, combineLatest, forkJoin, of, throwError } from "rxjs";
import { catchError, map, shareReplay, switchMap } from "rxjs/operators";

import { environment } from "../../../../../environments/environment";
import { skipFeedback } from "../../../../Core/services/common/http-feedback";
import {
  DropdownOptionDto,
  Spare,
  SpareCategory,
  SpareFormPayload,
  SpareSearchFilters,
} from "../models/spare.model";
import {
  IssueListEntry,
  IssueReason,
  IssueSparePayload,
  IssuedReturnedTrend,
  MultiIssuePayload,
  MultiIssueResult,
  ObsDashboardCounts,
  ReturnedItemStatus,
  ReturnSparePayload,
} from "../models/issue.model";
import {
  IssueRequisitionPayload,
  IssueRequisitionRow,
  RequisitionEntry,
  SendToCartPayload,
} from "../models/requisition.model";
import {
  DemandDetailsPayload,
  DemandEntry,
  IifEntry,
  SurveyDetailsPayload,
  SurveyEntry,
  VerifyPatternResult,
} from "../models/transaction.model";
import { HistoryEntry, HistoryFilters } from "../models/history.model";
import {
  BackendAuthority,
  BackendDemand,
  BackendDenomination,
  BackendEquipmentClass,
  BackendIssue,
  BackendIssueListEntry,
  BackendLookup,
  BackendMasterDropdown,
  BackendMultiIssueResult,
  BackendNotInCattedItem,
  BackendDefectRequisitionRow,
  BackendReturn,
  BackendRoutineRequisitionRow,
  BackendSpare,
  BackendSpareClass,
  BackendSurvey,
  BackendTyLoanPair,
  BackendVerifyPatternResult,
  ObsMasterMaps,
} from "../models/obs-backend.model";

const ISSUE_REMARKS: Record<IssueReason, string> = {
  Defect: "DEFECT",
  "Ty Loan - Other Ship": "TY LOAN",
};

/**
 * Ship Inventory - OBS API — talks to `backend/obs` (`api/v1/onboard-spares/...`).
 *
 * The backend serializers are id-only / snake_case (e.g. `Spares.equipment_class` is a plain FK
 * id, `spare_class` is only reachable via `equipment_class.spare_class`). The UI models in
 * `../models/*.model.ts` are flat, human-readable camelCase DTOs, so every method here joins the
 * raw response against cached master-data lookups (`masterMaps$`) and/or the full spares table
 * (`sparesById$`) before returning. Both caches are fetched once per app session (`shareReplay(1)`).
 *
 * A handful of methods have no working backend endpoint yet (noted inline as `BACKEND GAP`) —
 * they fail loudly via `throwError` (or return an empty list for read endpoints) instead of
 * silently faking success.
 */
@Injectable({ providedIn: "root" })
export class ObsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}api/v1/onboard-spares/`;

  private readonly rawSpareClasses$ = this.http
    .get<BackendSpareClass[]>(`${this.baseUrl}spare_class/`)
    .pipe(shareReplay(1));

  private readonly rawEquipmentClasses$ = this.http
    .get<BackendEquipmentClass[]>(`${this.baseUrl}equipment_class/`)
    .pipe(shareReplay(1));

  private readonly rawDenominations$ = this.http
    .get<BackendDenomination[]>(`${this.baseUrl}denominations/`)
    .pipe(shareReplay(1));

  private readonly rawAuthorities$ = this.http
    .get<BackendAuthority[]>(`${this.baseUrl}authorities/`)
    .pipe(shareReplay(1));

  private readonly masterMaps$: Observable<ObsMasterMaps> = combineLatest([
    this.rawSpareClasses$,
    this.rawEquipmentClasses$,
    this.rawDenominations$,
    this.rawAuthorities$,
  ]).pipe(
    map(([spareClasses, equipmentClasses, denominations, authorities]) => ({
      spareClassNameById: new Map(spareClasses.map((c) => [c.id, c.name])),
      equipmentClassById: new Map(
        equipmentClasses.map((c) => [c.id, { name: c.name, spareClassId: c.spare_class }]),
      ),
      denominationNameById: new Map(denominations.map((d) => [d.id, d.name])),
      authorityNameById: new Map(authorities.map((a) => [a.id, a.name])),
    })),
    shareReplay(1),
  );

  /** Full spares table, keyed by id — used to join pattern_number/description/etc onto the
   * id-only Issue/Return/Survey/Demand/IIF rows returned by the transaction endpoints. */
  private readonly sparesById$: Observable<Map<number, BackendSpare>> = this.http
    .get<BackendSpare[]>(`${this.baseUrl}view/`)
    .pipe(
      map((rows) => new Map(rows.map((row) => [row.id, row]))),
      shareReplay(1),
    );

  /** issue_list (pending-return) pk -> spare id, populated by `getReturnList()` and consumed by
   * `returnSpare()` since `ReturnSerializer` takes a `spare_id`, not an issue/issue-list pk. */
  private readonly returnListSpareByIssuePk = new Map<string, string>();

  /** not-in-catted-item pk -> spare id, populated by `getIifList()` and consumed by
   * `updateIifPatternNumber()` since `update-spare-pattern/` needs the Spares pk. */
  private readonly iifSpareByEntryId = new Map<string, string>();

  // ---------------------------------------------------------------------------------------
  // Master / dropdown data
  // ---------------------------------------------------------------------------------------

  getSpareClasses(): Observable<DropdownOptionDto[]> {
    return this.rawSpareClasses$.pipe(map(toDropdownOptions));
  }

  getEquipmentClasses(): Observable<DropdownOptionDto[]> {
    return this.rawEquipmentClasses$.pipe(map(toDropdownOptions));
  }

  getDenominations(): Observable<DropdownOptionDto[]> {
    return this.rawDenominations$.pipe(map(toDropdownOptions));
  }

  getAuthorities(): Observable<DropdownOptionDto[]> {
    return this.rawAuthorities$.pipe(map(toDropdownOptions));
  }

  getDepartments(): Observable<DropdownOptionDto[]> {
    return this.http
      .get<BackendMasterDropdown>(`${this.baseUrl}master/`)
      .pipe(map((response) => toDropdownOptions(response.departments)));
  }

  // ---------------------------------------------------------------------------------------
  // Spares search / CRUD — GET/POST/PUT api/v1/onboard-spares/{search_result,view,add,edit}/
  // ---------------------------------------------------------------------------------------

  searchSpares(filters: SpareSearchFilters): Observable<Spare[]> {
    const params = this.toParams({
      department: filters.department,
      spare_class: filters.spareClass,
      equipment_class: filters.equipmentClass,
      equipment: filters.equipmentClassText,
      pattern_number: filters.patternNumber,
      description: filters.description,
      remarks: filters.remarksText,
      q: filters.q,
    });
    return this.masterMaps$.pipe(
      switchMap((maps) =>
        this.http
          .get<BackendSpare[]>(`${this.baseUrl}search_result/`, { params })
          .pipe(map((rows) => rows.map((row) => this.adaptSpare(row, maps)))),
      ),
    );
  }

  exportSparesExcel(filters: SpareSearchFilters): Observable<Blob> {
    const params = this.toParams({
      department: filters.department,
      spare_class: filters.spareClass,
      equipment_class: filters.equipmentClass,
      equipment: filters.equipmentClassText,
      pattern_number: filters.patternNumber,
      description: filters.description,
      remarks: filters.remarksText,
      q: filters.q,
    });
    return this.http.get(`${this.baseUrl}export-excel/`, { params, responseType: "blob" });
  }

  getSpare(id: string): Observable<Spare> {
    return this.masterMaps$.pipe(
      switchMap((maps) =>
        this.http
          .get<BackendSpare>(`${this.baseUrl}view/${id}/`)
          .pipe(map((row) => this.adaptSpare(row, maps))),
      ),
    );
  }

  getSpares(ids: string[]): Observable<Spare[]> {
    if (!ids.length) return of([]);
    return this.masterMaps$.pipe(
      switchMap((maps) =>
        forkJoin(ids.map((id) => this.http.get<BackendSpare>(`${this.baseUrl}view/${id}/`))).pipe(
          map((rows) => rows.map((row) => this.adaptSpare(row, maps))),
        ),
      ),
    );
  }

  addSpare(payload: SpareFormPayload): Observable<Spare> {
    return this.masterMaps$.pipe(
      switchMap((maps) =>
        this.http
          .post<BackendSpare>(`${this.baseUrl}add/`, this.buildSpareFormData(payload))
          .pipe(map((row) => this.adaptSpare(row, maps))),
      ),
    );
  }

  updateSpare(id: string, payload: SpareFormPayload): Observable<Spare> {
    return this.masterMaps$.pipe(
      switchMap((maps) =>
        this.http
          .put<BackendSpare>(`${this.baseUrl}edit/${id}/`, this.buildSpareFormData(payload))
          .pipe(map((row) => this.adaptSpare(row, maps))),
      ),
    );
  }

  issueSpare(id: string, payload: IssueSparePayload): Observable<void> {
    return this.http
      .post(`${this.baseUrl}multi_issue_spare/`, {
        items: [{ spare: Number(id), quantity: payload.quantityIssued }],
        remarks: ISSUE_REMARKS[payload.reason],
        dart_number: payload.dartNo || "",
        equipment: this.toOptionalId(payload.equipmentName),
      })
      .pipe(map(() => void 0));
  }

  issueMultiple(payload: MultiIssuePayload): Observable<MultiIssueResult> {
    const items = payload.rows.map((row) => ({ spare: Number(row.spareId), quantity: row.quantityIssued }));
    return this.http
      .post<BackendMultiIssueResult>(`${this.baseUrl}multi_issue_spare/`, {
        items,
        remarks: ISSUE_REMARKS[payload.reason],
        equipment: this.toOptionalId(payload.equipmentName),
      })
      .pipe(
        map(() => ({
          // `multi_issue/` is all-or-nothing (a single validation error aborts the whole batch),
          // so a successful response means every requested row was issued.
          issued: payload.rows.map((row) => row.patternNumber),
          errors: [] as MultiIssueResult["errors"],
        })),
      );
  }

  // ---------------------------------------------------------------------------------------
  // Pending-return list (Issue + IssueList) and returns
  // ---------------------------------------------------------------------------------------

  getReturnList(): Observable<IssueListEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        forkJoin({
          issueList: this.http.get<BackendIssueListEntry[]>(`${this.baseUrl}issue_list/`),
          issues: this.http.get<BackendIssue[]>(`${this.baseUrl}sparesissued_tomaintainers/`),
        }).pipe(
          map(({ issueList, issues }) => {
            const issueById = new Map(issues.map((issue) => [issue.id, issue]));
            this.returnListSpareByIssuePk.clear();
            const rows: IssueListEntry[] = [];
            for (const entry of issueList) {
              const issue = issueById.get(entry.issue_entry);
              if (!issue) continue;
              this.returnListSpareByIssuePk.set(String(entry.id), String(issue.spare));
              rows.push(
                this.adaptIssueToListEntry(issue, sparesById.get(issue.spare), maps, entry.id),
              );
            }
            return rows;
          }),
        ),
      ),
    );
  }

  returnSpare(issuePk: string, payload: ReturnSparePayload): Observable<void> {
    const spareId = this.returnListSpareByIssuePk.get(issuePk);
    if (!spareId) {
      return throwError(
        () => new Error("Unable to resolve the spare for this return — reload the list and try again."),
      );
    }
    return this.http
      .post<BackendReturn>(`${this.baseUrl}return/`, {
        spare_id: Number(spareId),
        remarks: payload.remarks,
        quantity_returned: payload.quantityReturned,
      })
      .pipe(
        map((created) => {
          // BACKEND GAP: `Return` has no column for the "Same as Issued / New Item" choice made
          // in the Return modal — the serializer drops it. Persisted client-side (keyed by the
          // new Return row's id) so Return History can still show it for returns made from here.
          this.setReturnItemStatus(created.id, payload.itemStatus);
        }),
      );
  }

  // ---------------------------------------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------------------------------------

  getDashboardCounts(): Observable<ObsDashboardCounts> {
    return forkJoin({
      sparesIssuedToMaintainers: this.getSparesIssuedToMaintainers(),
      sparesIssuedOnTyLoan: this.getSparesIssuedOnTyLoan(),
      sparesReturned: this.getSparesReturnedList(),
      sparesLessThan50Percent: this.getSparesLessThan50Percent(),
      d787jDeficiency: this.getD787jDeficiency(),
      criticalSpareList: this.getCriticalSpareList(),
    }).pipe(
      map((results) => ({
        sparesIssuedToMaintainers: results.sparesIssuedToMaintainers.length,
        sparesIssuedOnTyLoan: results.sparesIssuedOnTyLoan.length,
        sparesReturned: results.sparesReturned.length,
        sparesLessThan50Percent: results.sparesLessThan50Percent.length,
        d787jDeficiency: results.d787jDeficiency.length,
        criticalSpareList: results.criticalSpareList.length,
      })),
    );
  }

  getIssuedReturnedTrend(): Observable<IssuedReturnedTrend> {
    const monthKeys = this.lastSixMonthKeys();
    return forkJoin({
      defectIssues: this.http.get<BackendIssue[]>(`${this.baseUrl}issue/`, {
        params: this.toParams({ remarks: "DEFECT" }),
      }),
      tyLoanPairs: this.http.get<BackendTyLoanPair[]>(`${this.baseUrl}sparesissued_ontyloan/`),
      allReturns: this.http.get<BackendReturn[]>(`${this.baseUrl}sparesreturned/`),
    }).pipe(
      map(({ defectIssues, tyLoanPairs, allReturns }) => {
        const tyLoanReturnDates = tyLoanPairs.map((pair) => pair.return?.return_time ?? null);
        const allReturnDates = allReturns.map((row) => row.return_time);
        const tyLoanReturned = this.countByMonth(tyLoanReturnDates, monthKeys);
        const allReturned = this.countByMonth(allReturnDates, monthKeys);
        // `Return` has no defect/ty-loan reason of its own — ty-loan returns are known from the
        // matched issue/return pairs above, so "defect" returns are approximated as the remainder.
        const defectReturned = allReturned.map((total, i) => Math.max(total - tyLoanReturned[i], 0));

        return {
          months: monthKeys.map((key) => this.monthLabel(key)),
          defect: {
            issued: this.countByMonth(defectIssues.map((issue) => issue.date_of_issue), monthKeys),
            returned: defectReturned,
          },
          tyLoan: {
            issued: this.countByMonth(tyLoanPairs.map((pair) => pair.issue.date_of_issue), monthKeys),
            returned: tyLoanReturned,
          },
        };
      }),
    );
  }

  // ---- Dashboard KPI "View more" drill-downs ----

  getSparesIssuedToMaintainers(): Observable<IssueListEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http.get<BackendIssue[]>(`${this.baseUrl}sparesissued_tomaintainers/`).pipe(
          map((issues) =>
            issues.map((issue) =>
              this.adaptIssueToListEntry(issue, sparesById.get(issue.spare), maps, issue.id),
            ),
          ),
        ),
      ),
    );
  }

  getSparesIssuedOnTyLoan(): Observable<IssueListEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http.get<BackendTyLoanPair[]>(`${this.baseUrl}sparesissued_ontyloan/`).pipe(
          map((pairs) =>
            pairs.map((pair) =>
              this.adaptIssueToListEntry(
                pair.issue,
                sparesById.get(pair.issue.spare),
                maps,
                pair.issue.id,
              ),
            ),
          ),
        ),
      ),
    );
  }

  getSparesReturnedList(): Observable<HistoryEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http
          .get<BackendReturn[]>(`${this.baseUrl}sparesreturned/`)
          .pipe(map((rows) => rows.map((row) => this.adaptReturnToHistoryEntry(row, sparesById, maps)))),
      ),
    );
  }

  getSparesLessThan50Percent(): Observable<Spare[]> {
    return this.getSpareListAction("spares_lessthen50per_in_inventory/");
  }

  getD787jDeficiency(): Observable<Spare[]> {
    return this.getSpareListAction("d787jdefficiency/");
  }

  getCriticalSpareList(): Observable<Spare[]> {
    return this.getSpareListAction("criticalsparelist/");
  }

  // ---------------------------------------------------------------------------------------
  // Maintainer Spare Requests (Routine / Defect DART)
  //
  // `requisition_details/`/`defect_requisition_details/` (`PlannedRoutineSpareListViewSet
  // .requisition`/`SparesViewSet.defect_requisition`) now return every pending row when called
  // with no id (previously mandatory, 400'd otherwise). Neither action embeds the routine's
  // name/number or the spare's category/authority/qty-authorised — only a `pattern_number` and an
  // `onboard_spare` pk — so those are joined in here from the same `sparesById$` cache the rest of
  // this service already uses. DART assignment (`raiseDartForDefectRequisitions`) and MO/WED cart
  // forwarding (`sendRequisitionsToCart`) still have no backend endpoint anywhere and remain
  // stubbed.
  // ---------------------------------------------------------------------------------------

  getRoutineRequisitions(): Observable<RequisitionEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http.get<BackendRoutineRequisitionRow[]>(`${this.baseUrl}requisition_details/`).pipe(
          map((rows) =>
            rows.map((row) =>
              this.adaptRoutineRequisition(row, row.onboard_spare != null ? sparesById.get(row.onboard_spare) : undefined, maps),
            ),
          ),
        ),
      ),
    );
  }

  getDefectRequisitions(): Observable<RequisitionEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http.get<BackendDefectRequisitionRow[]>(`${this.baseUrl}defect_requisition_details/`).pipe(
          map((rows) =>
            rows.map((row) =>
              this.adaptDefectRequisition(row, row.onboard_spare != null ? sparesById.get(row.onboard_spare) : undefined, maps),
            ),
          ),
        ),
      ),
    );
  }

  /** `delete-requisition-spare/` (routine) / `delete-defect-requisition-spare/` (defect) — real,
   * working endpoints, unlike the cart/DART actions below. `inventory_type` is always "OBS" here
   * since these requisitions all originate from this ship's own onboard-spares store. */
  deleteRequisition(kind: "routine" | "defect", id: string): Observable<void> {
    const endpoint = kind === "defect" ? "delete-defect-requisition-spare/" : "delete-requisition-spare/";
    return this.http
      .post(`${this.baseUrl}${endpoint}`, { pk: Number(id), inventory_type: "OBS" })
      .pipe(map(() => void 0));
  }

  /** BACKEND GAP: DART assignment lives in the `dart` app, not `obs` — no bulk endpoint here. */
  raiseDartForDefectRequisitions(_ids: string[]): Observable<void> {
    return throwError(
      () => new Error("Raising a DART for requisitions is not implemented on the backend yet."),
    );
  }

  /** BACKEND GAP: no endpoint anywhere creates an MO/WED cart entry from an OBS requisition —
   * only post-hoc cleanup actions exist once a cart entry has been created elsewhere. */
  sendRequisitionsToCart(_kind: "routine" | "defect", _payload: SendToCartPayload): Observable<void> {
    return throwError(
      () => new Error("Sending requisitions to the MO/WED cart is not implemented on the backend yet."),
    );
  }

  /** Uses the DART-aware bulk-issue actions (matched by pattern_number, not spare id) instead of
   * the plain `multi_issue_spare/` — those are the only two endpoints that actually touch the
   * originating `PlannedRoutineSpareList`/`DartSpare` requisition rows server-side. */
  issueRequisition(kind: "routine" | "defect", payload: IssueRequisitionPayload): Observable<void> {
    const endpoint = kind === "defect" ? "defect_multi_issue_spare/" : "routine_multi_issue_spare/";
    const remarks = `${kind.toUpperCase()} REQUISITION - ${payload.username}`.slice(0, 200);
    const toItems = (rows: IssueRequisitionRow[]) =>
      rows.map((row) => ({ pattern_number: row.patternNumber, quantity_issued: row.quantityIssued }));

    if (kind !== "defect") {
      return this.http
        .post(`${this.baseUrl}${endpoint}`, { items: toItems(payload.rows), remarks })
        .pipe(map(() => void 0));
    }

    // defect_multi_issue_spare/ is scoped to one dart_number per call — group the selected rows
    // by their originating DART and fire one bulk call per group.
    const groups = new Map<string, IssueRequisitionRow[]>();
    for (const row of payload.rows) {
      const key = row.dartNumber ?? "";
      groups.set(key, [...(groups.get(key) ?? []), row]);
    }
    const calls = [...groups.entries()].map(([dartNumber, rows]) =>
      this.http.post(`${this.baseUrl}${endpoint}`, {
        items: toItems(rows),
        remarks,
        dart_number: dartNumber || undefined,
      }),
    );
    return forkJoin(calls).pipe(map(() => void 0));
  }

  // ---------------------------------------------------------------------------------------
  // Internal Transactions — Survey
  // ---------------------------------------------------------------------------------------

  getSurveyList(): Observable<SurveyEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http
          .get<BackendSurvey[]>(`${this.baseUrl}survey_list/`)
          .pipe(map((rows) => rows.map((row) => this.adaptSurvey(row, sparesById.get(row.spare), maps)))),
      ),
    );
  }

  getSurveyEntry(id: string): Observable<SurveyEntry | undefined> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http
          .get<BackendSurvey>(`${this.baseUrl}survey_details/${id}/`)
          .pipe(map((row) => this.adaptSurvey(row, sparesById.get(row.spare), maps))),
      ),
    );
  }

  /** BACKEND GAP: `SurveyViewSet.complete` exists (views.py) but has no registered URL in
   * obs/urls.py — unlike Demand, which is wired via `demandgenerate/` -> `complete_from_payload`.
   * Add e.g. `path("survey_details/<int:pk>/complete/", SurveyViewSet.as_view({"post": "complete"}))`
   * to unblock this. */
  submitSurveyDetails(id: string, payload: SurveyDetailsPayload): Observable<void> {
    return this.http
      .post(`${this.baseUrl}survey_details/${id}/complete/`, {
        quantity_surveyed: payload.quantitySurveyed,
        survey_number: payload.surveyNumber,
        survey_report_date: payload.surveyReportDate,
        remarks: payload.remarks,
      })
      .pipe(map(() => void 0));
  }

  /** BACKEND GAP: DART assignment lives in the `dart` app, not `obs` — no bulk endpoint here. */
  raiseDartForSurvey(_ids: string[]): Observable<void> {
    return throwError(() => new Error("Raising a DART for surveys is not implemented on the backend yet."));
  }

  /** BACKEND GAP: no MO/WED survey-cart endpoint in the `obs` app. */
  sendSurveyToCart(_payload: SendToCartPayload): Observable<void> {
    return throwError(
      () => new Error("Sending surveys to the MO/WED cart is not implemented on the backend yet."),
    );
  }

  // ---------------------------------------------------------------------------------------
  // Internal Transactions — Demand
  // ---------------------------------------------------------------------------------------

  getDemandList(): Observable<DemandEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http
          .get<BackendDemand[]>(`${this.baseUrl}demand_list/`)
          .pipe(map((rows) => rows.map((row) => this.adaptDemand(row, sparesById.get(row.spare), maps)))),
      ),
    );
  }

  getDemandEntry(id: string): Observable<DemandEntry | undefined> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http
          .get<BackendDemand>(`${this.baseUrl}demand_details/${id}/`)
          .pipe(map((row) => this.adaptDemand(row, sparesById.get(row.spare), maps))),
      ),
    );
  }

  submitDemandDetails(id: string, payload: DemandDetailsPayload): Observable<void> {
    return this.http
      .post(`${this.baseUrl}demandgenerate/`, {
        demand_id: Number(id),
        quantity_demanded: payload.quantityDemanded,
        demand_number: payload.demandNumber,
        demand_date: payload.demandDate,
        remarks: payload.remarks,
      })
      .pipe(map(() => void 0));
  }

  /** BACKEND GAP: DART assignment lives in the `dart` app, not `obs` — no bulk endpoint here. */
  raiseDartForDemand(_ids: string[]): Observable<void> {
    return throwError(() => new Error("Raising a DART for demands is not implemented on the backend yet."));
  }

  /** BACKEND GAP: no MO cart endpoint in the `obs` app. */
  sendDemandToCart(_payload: SendToCartPayload): Observable<void> {
    return throwError(() => new Error("Sending demands to the MO cart is not implemented on the backend yet."));
  }

  // ---------------------------------------------------------------------------------------
  // Internal Transactions — Items Identified as Faulty / Not-Catted (IIF)
  // ---------------------------------------------------------------------------------------

  getIifList(): Observable<IifEntry[]> {
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http.get<BackendNotInCattedItem[]>(`${this.baseUrl}iif_list/`).pipe(
          map((rows) => {
            this.iifSpareByEntryId.clear();
            return rows.map((row) => {
              if (row.spare_id != null) this.iifSpareByEntryId.set(String(row.id), String(row.spare_id));
              const spareRow = row.spare_id != null ? sparesById.get(row.spare_id) : undefined;
              const spare = spareRow ? this.adaptSpare(spareRow, maps) : null;
              const entry: IifEntry = {
                id: String(row.id),
                patternNumber: spare?.patternNumber ?? "",
                description: spare?.description ?? "",
                quantity: spare?.quantityAvailable ?? 0,
                category: spare?.category ?? "",
                equipmentClass: spare?.equipmentClass ?? "",
                critical: spare?.critical ?? false,
                authority: spare?.authority ?? "",
                parentInventory: "ILMS",
              };
              return entry;
            });
          }),
        ),
      ),
    );
  }

  verifyPatternNumber(_id: string, patternNumber: string): Observable<VerifyPatternResult> {
    return this.http
      .post<BackendVerifyPatternResult>(`${this.baseUrl}verify-pattern/`, {
        pattern_number: patternNumber,
      })
      .pipe(
        map((result) => ({
          matched: result.valid,
          itemCode: result.item_code,
          description: result.description ?? result.item_desc,
          category: result.category,
        })),
      );
  }

  updateIifPatternNumber(id: string, patternNumber: string): Observable<void> {
    const sparePk = this.iifSpareByEntryId.get(id);
    if (!sparePk) {
      return throwError(
        () => new Error("Unable to resolve the spare for this IIF entry — reload the list and try again."),
      );
    }
    return this.http
      .post(`${this.baseUrl}update-spare-pattern/`, {
        spare_pk: Number(sparePk),
        pattern_number: patternNumber,
      })
      .pipe(map(() => void 0));
  }

  sendIifToCart(payload: SendToCartPayload): Observable<void> {
    // obs has no dedicated MO/WED "cart" endpoint; mark-incatted is the closest real action and
    // produces the visible effect this screen wants (the item leaves the pending IIF list).
    return forkJoin(
      payload.ids.map((id) => this.http.post(`${this.baseUrl}iifdetails/${id}/`, {})),
    ).pipe(map(() => void 0));
  }

  // ---------------------------------------------------------------------------------------
  // References — Masters (Import Data / Upload PIL)
  // ---------------------------------------------------------------------------------------

  /** `POST import-excel-file/` — real `ExcelImportExportMixin.import_excel` action on
   * `SparesViewSet`. Bulk-creates `Spares` rows from an uploaded `.xlsx` (headers must match
   * `SparesSerializer`'s writable fields); 400s with a per-row `errors` array on any invalid row
   * (the whole batch is rejected, nothing partially imported). Toast is suppressed on the request
   * (`skipFeedback`) so the specific validation detail from the response body can be shown instead
   * of the interceptor's generic fallback. */
  importSparesExcel(file: File): Observable<{ imported: number }> {
    const formData = new FormData();
    formData.append("file", file);
    return this.http
      .post<ExcelImportResponse>(`${this.baseUrl}import-excel-file/`, formData, {
        context: skipFeedback({ toast: true }),
      })
      .pipe(
        map((response) => ({ imported: response.imported })),
        catchError((error: unknown) => throwError(() => new Error(describeExcelImportError(error)))),
      );
  }

  /** BACKEND GAP: `VendorPilViewSet` (ilms app) mixes in `ExcelImportExportMixin` — the same
   * `import_excel`/`export_excel`/`download_template` actions `importSparesExcel()` above uses —
   * but `ilms/urls.py` only wires `list`/`create` for it (`path("vendor-pils/", ...)`), not the
   * mixin's actions. `ilms.excel.ExcelImportExportMixin.import_excel` is itself a different,
   * async-task-dispatching implementation from the `obs` one (confirmed live: `POST
   * vendor-pils/import-excel/` returns Django's raw CSRF-failure HTML, meaning the URL never
   * resolves to any DRF view at all). Needs a real backend route added before this can work. */
  importVendorPil(_file: File): Observable<{ imported: number }> {
    return throwError(
      () => new Error("PIL upload isn't wired up on the backend yet — no route serves this action."),
    );
  }

  // ---------------------------------------------------------------------------------------
  // History
  // ---------------------------------------------------------------------------------------

  /** BACKEND GAP: `history_search/` unconditionally 500s — `select_related("user_profile")`
   * in the Django view references a field that doesn't exist on that model (confirmed via the
   * live error body: "Invalid field name(s) given in select_related: 'user_profile'. Choices
   * are: rank, designation_master, department, role_master, command_name, ship, division").
   * Sourced from `sparesissued_tomaintainers/` + `sparesissued_ontyloan/` instead — the same two
   * real, working endpoints the "Spares Issued to Maintainers" / "Spares Issued on Ty Loan"
   * dashboard drill-downs already use — mirroring how `getReturnedHistory()` below already
   * bypasses `history_search/`'s equally-unusable `history_return` rows in favor of
   * `sparesreturned/`. */
  getIssuedHistory(filters: HistoryFilters): Observable<HistoryEntry[]> {
    return forkJoin({
      toMaintainers: this.getSparesIssuedToMaintainers(),
      tyLoan: this.getSparesIssuedOnTyLoan(),
    }).pipe(
      map(({ toMaintainers, tyLoan }) =>
        [...toMaintainers, ...tyLoan]
          .map(
            (entry): HistoryEntry => ({
              id: entry.issuePk,
              patternNumber: entry.patternNumber,
              description: entry.description,
              date: entry.issueDate,
              quantity: entry.issuedQty,
              user: entry.username,
              equipmentClass: entry.equipmentClass,
              authority: entry.authority,
              reason: entry.reason,
              equipmentNomenclature: entry.equipmentNomenclature,
            }),
          )
          .filter((entry) => this.matchesHistoryFilters(entry, filters)),
      ),
    );
  }

  getReturnedHistory(filters: HistoryFilters): Observable<HistoryEntry[]> {
    // The `history_search/` action's `history_return` rows carry no date/quantity, so returned
    // history is sourced from `sparesreturned/` (Return records) instead, which has both — joined
    // against `sparesById$`/`masterMaps$` for equipment class + authority the same way the pending
    // returns list (`getReturnList`) already does.
    return combineLatest([this.masterMaps$, this.sparesById$]).pipe(
      switchMap(([maps, sparesById]) =>
        this.http.get<BackendReturn[]>(`${this.baseUrl}sparesreturned/`).pipe(
          map((rows) =>
            rows
              .map((row) => this.adaptReturnToHistoryEntry(row, sparesById, maps))
              .filter((entry) => this.matchesHistoryFilters(entry, filters)),
          ),
        ),
      ),
    );
  }

  /** Equipment class name -> spare class name, derived from the same cached master lookups used
   * everywhere else in this service — lets History filter by Spare Class even though the history
   * rows themselves only carry an equipment class name. */
  getEquipmentClassToSpareClass(): Observable<Map<string, string>> {
    return this.masterMaps$.pipe(
      map((maps) => {
        const result = new Map<string, string>();
        for (const { name, spareClassId } of maps.equipmentClassById.values()) {
          const spareClassName = maps.spareClassNameById.get(spareClassId);
          if (spareClassName) result.set(name, spareClassName);
        }
        return result;
      }),
    );
  }

  private matchesHistoryFilters(entry: HistoryEntry, filters: HistoryFilters): boolean {
    if (!this.withinDateRange(entry.date, filters)) return false;
    if (filters.equipmentClass && entry.equipmentClass !== filters.equipmentClass) return false;
    return true;
  }

  // ---------------------------------------------------------------------------------------
  // Adapters — backend snake_case/id-only DTOs -> UI camelCase DTOs
  // ---------------------------------------------------------------------------------------

  private adaptSpare(row: BackendSpare, maps: ObsMasterMaps): Spare {
    const equipmentClass = maps.equipmentClassById.get(row.equipment_class);
    const spareClassName = equipmentClass
      ? maps.spareClassNameById.get(equipmentClass.spareClassId)
      : undefined;
    return {
      id: String(row.id),
      spareClass: spareClassName ?? "",
      equipmentClass: equipmentClass?.name ?? String(row.equipment_class),
      patternNumber: row.pattern_number,
      description: row.description,
      compartment: row.compartment ?? "",
      rackPosition: row.rack_position ?? "",
      rackNumber: row.rack_number ?? "",
      location: row.location ?? "",
      category: (row.category || "PERMANENT") as SpareCategory,
      critical: row.critical,
      denomination:
        row.denomination != null ? maps.denominationNameById.get(row.denomination) ?? "" : "",
      authority: maps.authorityNameById.get(row.authority) ?? String(row.authority),
      quantityAuthorised: row.quantity_authorised,
      quantityAvailable: row.quantity_available,
      page: row.page ?? "",
      line: row.line ?? "",
      remarks: row.remarks ?? "",
      // DRF serializes ImageField as an absolute URL when request context is present, which
      // CleanValidationModelViewSet always provides — no origin-prefixing needed here.
      imageUrl: row.image ?? undefined,
    };
  }

  private adaptIssueToListEntry(
    issue: BackendIssue,
    spareRow: BackendSpare | undefined,
    maps: ObsMasterMaps,
    issuePk: number,
  ): IssueListEntry {
    const spare = spareRow ? this.adaptSpare(spareRow, maps) : null;
    return {
      issuePk: String(issuePk),
      spareId: String(issue.spare),
      patternNumber: spare?.patternNumber ?? "",
      description: spare?.description ?? "",
      issueDate: issue.date_of_issue,
      username: String(issue.username),
      issuedQty: issue.quantity_issued,
      authority: spare?.authority ?? "",
      reason: issue.remarks?.toUpperCase() === "TY LOAN" ? "Ty Loan - Other Ship" : "Defect",
      equipmentNomenclature: "", // ems.EquipmentName isn't exposed via the obs API
      equipmentClass: spare?.equipmentClass ?? "",
      spareClass: spare?.spareClass ?? "",
      category: spare?.category ?? "",
      denomination: spare?.denomination ?? "",
      critical: spare?.critical ?? false,
      isWedMo: false, // not exposed by IssueSerializer
    };
  }

  private adaptRoutineRequisition(
    row: BackendRoutineRequisitionRow,
    spareRow: BackendSpare | undefined,
    maps: ObsMasterMaps,
  ): RequisitionEntry {
    const spare = spareRow ? this.adaptSpare(spareRow, maps) : null;
    return {
      id: String(row.planned_spare_id),
      requestedFrom: "",
      patternNumber: row.pattern_number,
      description: row.description || spare?.description || "",
      equipmentClass: spare?.equipmentClass ?? "",
      equipmentName: "",
      category: spare?.category ?? "",
      denomination: spare?.denomination ?? "",
      quantityAuthorised: spare?.quantityAuthorised ?? 0,
      quantityAvailable: row.quantity_available,
      quantityRequired: row.quantity_required,
      availableWithMo: row.available_onboard ? "Available Onboard" : "Requires MO/WED",
      critical: spare?.critical ?? false,
      authority: spare?.authority ?? "",
      boxNo: spare?.location ?? "",
      remarks: spare?.remarks ?? "",
    };
  }

  private adaptDefectRequisition(
    row: BackendDefectRequisitionRow,
    spareRow: BackendSpare | undefined,
    maps: ObsMasterMaps,
  ): RequisitionEntry {
    const spare = spareRow ? this.adaptSpare(spareRow, maps) : null;
    return {
      id: String(row.dart_spare_id),
      requestedFrom: "",
      patternNumber: row.pattern_number,
      description: row.description || spare?.description || "",
      equipmentClass: spare?.equipmentClass ?? "",
      equipmentName: "",
      category: spare?.category ?? "",
      denomination: spare?.denomination ?? "",
      quantityAuthorised: spare?.quantityAuthorised ?? 0,
      quantityAvailable: row.quantity_available,
      quantityRequired: row.quantity_required,
      availableWithMo: row.available_onboard ? "Available Onboard" : "Requires MO/WED",
      critical: spare?.critical ?? false,
      authority: spare?.authority ?? "",
      boxNo: spare?.location ?? "",
      remarks: spare?.remarks ?? "",
      dartNumber: row.dart_number,
    };
  }

  // BACKEND GAP: see `returnSpare()` — `Return` has no "Same as Issued / New Item" column, so
  // this is captured client-side (localStorage) at submission time and re-attached here.
  private static readonly RETURN_ITEM_STATUS_KEY = "obs_return_item_status_v1";

  private setReturnItemStatus(returnId: number, status: ReturnedItemStatus): void {
    const map = this.readReturnItemStatusMap();
    map[returnId] = status;
    localStorage.setItem(ObsApiService.RETURN_ITEM_STATUS_KEY, JSON.stringify(map));
  }

  private readReturnItemStatusMap(): Record<number, ReturnedItemStatus> {
    try {
      const raw = localStorage.getItem(ObsApiService.RETURN_ITEM_STATUS_KEY);
      return raw ? (JSON.parse(raw) as Record<number, ReturnedItemStatus>) : {};
    } catch {
      return {};
    }
  }

  private adaptReturnToHistoryEntry(
    row: BackendReturn,
    sparesById: Map<number, BackendSpare>,
    maps: ObsMasterMaps,
  ): HistoryEntry {
    const spareRow = row.spare_id != null ? sparesById.get(row.spare_id) : undefined;
    const spare = spareRow ? this.adaptSpare(spareRow, maps) : null;
    return {
      id: String(row.id),
      patternNumber: spare?.patternNumber ?? "",
      description: spare?.description ?? "",
      date: row.return_time ?? "",
      quantity: row.quantity_returned,
      user: row.username || "",
      equipmentClass: spare?.equipmentClass ?? "",
      authority: spare?.authority ?? "",
      remarks: row.remarks ?? "",
      returnedItemStatus: this.readReturnItemStatusMap()[row.id],
    };
  }

  private adaptSurvey(
    row: BackendSurvey,
    spareRow: BackendSpare | undefined,
    maps: ObsMasterMaps,
  ): SurveyEntry {
    const spare = spareRow ? this.adaptSpare(spareRow, maps) : null;
    return {
      id: String(row.id),
      patternNumber: spare?.patternNumber ?? "",
      dartNumber: row.dart_number ?? "",
      description: spare?.description ?? "",
      quantity: row.quantity_tosurvey,
      category: spare?.category ?? "",
      equipmentClass: spare?.equipmentClass ?? "",
      critical: spare?.critical ?? false,
      authority: spare?.authority ?? "",
      parentInventory: "ILMS", // Survey doesn't track an MO/WED source — obs has one merged queue
      incattingStatus: row.is_iif ? "IIF" : "OK",
    };
  }

  private adaptDemand(
    row: BackendDemand,
    spareRow: BackendSpare | undefined,
    maps: ObsMasterMaps,
  ): DemandEntry {
    const spare = spareRow ? this.adaptSpare(spareRow, maps) : null;
    return {
      id: String(row.id),
      patternNumber: spare?.patternNumber ?? "",
      description: spare?.description ?? "",
      quantity: row.quantity_todemand,
      category: spare?.category ?? "",
      equipmentClass: spare?.equipmentClass ?? "",
      critical: spare?.critical ?? false,
      authority: spare?.authority ?? "",
      parentInventory: "ILMS",
      incattingStatus: row.is_iif ? "IIF" : "OK",
      dartNumber: row.dart_number ?? "",
    };
  }

  // ---------------------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------------------

  private getSpareListAction(path: string): Observable<Spare[]> {
    return this.masterMaps$.pipe(
      switchMap((maps) =>
        this.http
          .get<BackendSpare[]>(`${this.baseUrl}${path}`)
          .pipe(map((rows) => rows.map((row) => this.adaptSpare(row, maps)))),
      ),
    );
  }

  private buildSpareFormData(payload: SpareFormPayload): FormData {
    const formData = new FormData();
    formData.append("equipment_class", payload.equipmentClass);
    formData.append("pattern_number", payload.patternNumber);
    formData.append("description", payload.description);
    formData.append("category", payload.category);
    formData.append("critical", String(payload.critical));
    formData.append("compartment", payload.compartment || "");
    formData.append("location", payload.location || "");
    formData.append("rack_position", payload.rackPosition || "");
    formData.append("rack_number", payload.rackNumber || "");
    formData.append("denomination", payload.denomination);
    formData.append("quantity_authorised", String(payload.quantityAuthorised));
    formData.append("quantity_available", String(payload.quantityAvailable));
    formData.append("authority", payload.authority);
    formData.append("page", payload.page || "");
    formData.append("line", payload.line || "");
    formData.append("remarks", payload.remarks || "");
    formData.append("is_obs", "true");
    if (payload.image) {
      formData.append("image", payload.image);
    }
    return formData;
  }

  private withinDateRange(date: string, filters: HistoryFilters): boolean {
    if (!date) return !filters.dateFrom && !filters.dateTo;
    const value = date.slice(0, 10);
    if (filters.dateFrom && value < filters.dateFrom) return false;
    if (filters.dateTo && value > filters.dateTo) return false;
    return true;
  }

  private lastSixMonthKeys(): string[] {
    const keys: string[] = [];
    const now = new Date();
    for (let offset = 5; offset >= 0; offset--) {
      const date = new Date(now.getFullYear(), now.getMonth() - offset, 1);
      keys.push(`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`);
    }
    return keys;
  }

  private monthLabel(key: string): string {
    const [year, month] = key.split("-").map(Number);
    return new Date(year, month - 1, 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
  }

  /** Counts how many ISO date strings fall in each "YYYY-MM" month key, in the given order. */
  private countByMonth(isoDates: (string | null)[], monthKeys: string[]): number[] {
    return monthKeys.map((key) => isoDates.filter((date) => !!date && date.slice(0, 7) === key).length);
  }

  private toOptionalId(value?: string): number | undefined {
    if (!value) return undefined;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  private toParams(query: Record<string, string | number | undefined | null>): HttpParams {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === "") continue;
      params = params.set(key, String(value));
    }
    return params;
  }
}

function toDropdownOptions(rows: BackendLookup[]): DropdownOptionDto[] {
  return rows.map((row) => ({ value: String(row.id), label: row.name }));
}

/** Response shape of `ExcelImportExportMixin.import_excel` (`backend/obs/excel.py`,
 * shared verbatim by the `ilms` app's `VendorPilViewSet`) on success. */
interface ExcelImportResponse {
  imported: number;
}

function firstStringFromArrayField(body: Record<string, unknown>, key: string): string | null {
  const value = body[key];
  return Array.isArray(value) && value.length ? String(value[0]) : null;
}

function describeExcelRowErrors(body: Record<string, unknown>): string | null {
  const rowErrors = body["errors"];
  if (!Array.isArray(rowErrors) || !rowErrors.length) return null;
  const invalidRows = typeof body["invalid_rows"] === "number" ? body["invalid_rows"] : rowErrors.length;
  const first = rowErrors[0] as { row?: number };
  return `${invalidRows} row(s) failed validation (first at row ${first.row ?? "?"}) — fix the file and try again.`;
}

/** Same action's three distinct 400 shapes: a missing/invalid file (`file`), unrecognised column
 * headers (`headers` + `allowed_columns`), or per-row validation failures (`errors`). Picks the
 * most specific message available instead of the interceptor's generic HTTP-status fallback. */
function describeExcelImportError(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) {
    return error instanceof Error ? error.message : "Something went wrong. Please try again.";
  }
  const body = error.error as Record<string, unknown> | null;
  if (body && typeof body === "object") {
    const message =
      firstStringFromArrayField(body, "file") ??
      firstStringFromArrayField(body, "headers") ??
      describeExcelRowErrors(body);
    if (message) return message;
  }
  if (error.status === 0) return "Unable to reach the server. Please check your connection and try again.";
  return "Import failed. Please check the file and try again.";
}
