import { HttpClient, HttpContext, HttpParams } from "@angular/common/http";
import { inject, Injectable, signal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { InboxMessage } from "../../Pages/inbox-dashboard/inbox-model/inbox-model";
import { Observable, Subject, catchError, of } from "rxjs";
import { getDummyResponse } from "./dummy-responses";
import { skipFeedback } from "../../Core/services/common/http-feedback";
import { MaintenanceDashboardResponse } from "../../Pages/op-maintenance/op-maintenance-dashboard/maintenance-dashboard.model";
import {
  DartDashboardResponse,
  MaintenancePeriodRow,
  SubDeptDefectRow,
} from "../../Pages/op-maintenance/op-maintenance-dashboard/op-maintenance-dashboard.model";
import { OpenDefectsResponse } from "../../Pages/op-maintenance/open-defects/open-defects.model";
import { CreateRAResponse } from "../../Pages/op-maintenance/create-ra/create-ra.model";
import { CreateDLResponse } from "../../Pages/op-maintenance/create-dliii/create-dliii.model";
import { CompleteDartListItem } from "../../Pages/op-maintenance/complete-dart-list/complete-dart-list.model";
import {
  GeneratedDl1ReportInnerRow,
  GeneratedDl1ReportRow,
} from "../../Pages/op-maintenance/routines-dashboard/references/exported-files-dl1/exported-files-dl1.model";
import { SlipHistoryResponse } from "../../Pages/op-maintenance/routines-dashboard/history/slip-history/slip-history";
import { MaintenanceApiResponse } from "../../Pages/op-maintenance/routines-dashboard/reports/reports.component";
import { SFDDashboardResponse } from "../../Pages/ship-configuration/ship-configuration.model";
import { CloseDefectResponse } from "../../Pages/op-maintenance/defect-closure-details/defect-closure-details.model";
import { UniqueMaintopResponse } from "../../Pages/op-maintenance/routines-dashboard/main-top.model";
import { RoutineResponse } from "../../Pages/op-maintenance/routines-dashboard/calendar-based-routines/calendar-based-routines.model";
import { EquipmentDueForAberResponse } from "../../Pages/op-maintenance/routines-dashboard/equipment-due-for-aber/equipment-due-for-aber.model";
import {
  CloseRoutinePayload,
  CloseRoutineResponse,
  FUSSTriggerListResponse,
  RaiseFussPayload,
  RaiseFussResponse,
} from "../../Pages/op-maintenance/routines-dashboard/fuss-triger-list/fuss-trigger-list.model";
import { EmsSearchResultItem, PlannedRoutineDetail, RoutinePlanResponse, SearchDetailResultItem } from "../../Pages/op-maintenance/routines-dashboard/search-routines/search-routines.model";
import { GenerateDl1ListResponse, RefitRoutineDetail, RefitSearchListResponse, SaveDlDraftRowsPayload } from "../../Pages/op-maintenance/routines-dashboard/dl1-generation/refit-routines.model";
import { DartHistoryResponse } from "../../Pages/op-maintenance/history/history.component";
import { GeneratedDlIiReport } from "../../Pages/op-maintenance/references/exported-files/exported-files.component";
import {
  RoutineHistoryApiResponse,
  RoutineHistoryFilters,
  RoutineHistoryTimelineResponse,
} from "../../Pages/op-maintenance/routines-dashboard/history/equipment-routine-history/equipment-routine-history";
import { ClosedRoutineApiResponse } from "../../Pages/op-maintenance/routines-dashboard/history/close-routine-history/close-routine-history";
import { SyncCmmsResponse } from "../../Pages/op-maintenance/routines-dashboard/references/import-data/import-data";
import { RaiseFussSaveResponse } from "../../Pages/op-maintenance/routines-dashboard/fuss-triger-list/fuss-triger-raise-fuss/fuss-triger-raise-fuss";
import {
  AvailableUsersResponse,
  HierarchyTreeResponse,
} from "../../Pages/home/divisional-organisation/divisional-organisation.model";
import {
  RegulatorSailorsResponse,
  RegulatorsTreeResponse,
} from "../../Pages/home/know-your-regulators/know-your-regulators.model";
import { GalleryImage } from "../../Pages/home/gallery/gallery.model";
import { CoMessageApi, DepartmentMaster, LoginPageImageApi, MemberDetailApi, QuoteApi, ShipRoleApi, UpcomingEventApi } from "../../Pages/home/department-master/department-master.model";
import {
  EmsSectionsResponse,
  EmsThumbnailResponse,
  EquipmentHistoryResponse,
  SaveMonthlyRunningHoursPayload,
  SectionRhsiBarchartResponse,
  UpdateEquipmentStatePayload,
} from "../../Pages/op-maintenance/routines-dashboard/ems-dashboard/ems-dashboard.model";
import {
  PersonnelEventsResponse,
  SaveDailyOrderPayload,
  UserByIdResponse,
} from "../../Pages/home/home/home.model";

@Injectable({
  providedIn: "root",
})
export class Call {
  private readonly http = inject(HttpClient);
  public composeTrigger$ = new Subject<void>();
  public refreshData$ = new Subject<void>();
  public logincallFailed = signal<boolean>(false);

  baseUrl = environment.apiUrl;

  apiUrl = environment.API_URL;

  logincall(cred: { loginname: string; password: string }) {
    return this.http
      .post(this.apiUrl + "api/auth/token", cred, {
        context: skipFeedback({ loader: true, toast: true }),
      })
      .pipe(
        catchError((err) => {
          console.warn("[Call] logincall API failed silently:", err);
          localStorage.removeItem("user");
          this.logincallFailed.set(true);
          return of(null);
        }),
      )
      .subscribe((res: unknown) => {
        if (res) {
          localStorage.setItem("user", JSON.stringify(res));
          this.logincallFailed.set(false);
        } else {
          localStorage.removeItem("user");
          this.logincallFailed.set(true);
        }
      });
  }

  isTrialAvailable(): boolean {
    if (this.logincallFailed()) {
      return false;
    }
    const userStr = localStorage.getItem("user");
    if (!userStr) {
      return false;
    }
    try {
      const userObj = JSON.parse(userStr);
      return !!(userObj && (userObj.access || userObj.token));
    } catch {
      return false;
    }
  }

  refreshAccessToken() {
    const user = localStorage.getItem('user');
    let refresh = '';
    if (user) {
       refresh = JSON.parse(user).refresh;
    }
    return this.http.post(this.apiUrl + "api/auth/token/refresh", { refresh });
  }

  logoutcall() {
    localStorage.clear();
    return this.http.post(this.apiUrl + "api/auth/logout", {});
  }

  getCurrentUser() {
    return this.http.get<{ profile?: { department?: number } }>(
      `${this.baseUrl}api/v1/user/me/`,
    );
  }

  getUserById(id: number) {
    return this.http.get<UserByIdResponse>(`${this.baseUrl}api/v1/user/users/${id}/`);
  }

  getUsers() {
    return this.http.get<UserByIdResponse[]>(`${this.baseUrl}api/v1/user/users/`);
  }

  updateMarriageDate(id: number, marriageDate: string) {
    return this.http.patch(
      `${this.baseUrl}api/v1/user/profiles/${id}/marriage/`,
      { marriage_date: marriageDate },
    );
  }

  // creaet sfe equipments for refrence of ship config
  createSfdEquipment(payload: Record<string, unknown>) {
    return this.http.post(`${this.baseUrl}api/v1/sfd/add-equipment/`, payload);
  }

  // tickets

  getTickets() {
    return this.http.get(
      this.baseUrl + "api/v1/ticket-management/tickets/my-tickets/",
    );
  }

  getLoggedInuserDetails() {
    return this.http.get(this.baseUrl + "api/v1/user/retrive/");
  }

  getGalleryData() {
    return this.http.get<GalleryImage[]>(this.baseUrl + "api/v1/user/gallery/");
  }

  createGalleryImage(payload: FormData) {
    return this.http.post(this.baseUrl + "api/v1/user/gallery/", payload);
  }

  deleteGalleryImage(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/user/gallery/${id}/`);
  }

  getLoginPageImages() {
    return this.http.get<LoginPageImageApi[]>(this.baseUrl + "api/v1/user/login-images/");
  }

  createLoginPageImage(payload: FormData) {
    return this.http.post<LoginPageImageApi>(this.baseUrl + "api/v1/user/login-images/", payload);
  }

  updateLoginPageImage(id: number, payload: FormData) {
    return this.http.patch<LoginPageImageApi>(`${this.baseUrl}api/v1/user/login-images/${id}/`, payload);
  }

  getDepartments() {
    return this.http.get<DepartmentMaster[]>(
      this.baseUrl + "api/v1/user/departments/",
    );
  }

  createDepartment(payload: Partial<DepartmentMaster>) {
    return this.http.post(this.baseUrl + "api/v1/user/departments/", payload);
  }

  updateDepartment(id: number, payload: Partial<DepartmentMaster>) {
    return this.http.patch(
      `${this.baseUrl}api/v1/user/departments/${id}/`,
      payload,
    );
  }

  deleteDepartment(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/user/departments/${id}/`);
  }

  getMemberDetails() {
    return this.http.get<MemberDetailApi[]>(this.baseUrl + "api/v1/master/member-details/");
  }

  createMemberDetail(payload: FormData) {
    return this.http.post<MemberDetailApi>(this.baseUrl + "api/v1/master/member-details/", payload);
  }

  updateMemberDetail(id: number, payload: FormData) {
    return this.http.patch<MemberDetailApi>(`${this.baseUrl}api/v1/master/member-details/${id}/`, payload);
  }

  deleteMemberDetail(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/master/member-details/${id}/`);
  }

  getQuotes() {
    return this.http.get<QuoteApi[]>(this.baseUrl + "api/v1/master/quotes/");
  }

  createQuote(payload: { quoteText: string }) {
    return this.http.post<QuoteApi>(this.baseUrl + "api/v1/master/quotes/", payload);
  }

  updateQuote(id: number, payload: { quoteText: string }) {
    return this.http.patch<QuoteApi>(`${this.baseUrl}api/v1/master/quotes/${id}/`, payload);
  }

  deleteQuote(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/master/quotes/${id}/`);
  }

  activateQuote(id: number) {
    return this.http.post(`${this.baseUrl}api/v1/master/quotes/${id}/activate/`, {});
  }

  getShipRoles() {
    return this.http.get<ShipRoleApi[]>(this.baseUrl + "api/v1/master/ship-roles/");
  }

  createShipRole(payload: FormData) {
    return this.http.post<ShipRoleApi>(this.baseUrl + "api/v1/master/ship-roles/", payload);
  }

  updateShipRole(id: number, payload: FormData) {
    return this.http.patch<ShipRoleApi>(`${this.baseUrl}api/v1/master/ship-roles/${id}/`, payload);
  }

  deleteShipRole(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/master/ship-roles/${id}/`);
  }

  getCoMessages() {
    return this.http.get<CoMessageApi[]>(this.baseUrl + "api/v1/master/co-messages/");
  }

  createCoMessage(payload: { message: string; valid_till_date: string }) {
    return this.http.post<CoMessageApi>(this.baseUrl + "api/v1/master/co-messages/", payload);
  }

  updateCoMessage(id: number, payload: { message: string; valid_till_date: string }) {
    return this.http.patch<CoMessageApi>(`${this.baseUrl}api/v1/master/co-messages/${id}/`, payload);
  }

  deleteCoMessage(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/master/co-messages/${id}/`);
  }

  getHierarchy() {
    return this.http.get(this.baseUrl + "api/v1/master/hierarchy/");
  }

  getHierarchyTree() {
    return this.http.get<HierarchyTreeResponse>(
      this.baseUrl + "api/v1/master/hierarchy/nested/",
    );
  }

  getAvailableHierarchyUsers(excludeNodeId?: number) {
    const query = excludeNodeId ? `?exclude_node_id=${excludeNodeId}` : "";
    return this.http.get<AvailableUsersResponse>(
      `${this.baseUrl}api/v1/master/hierarchy/available_users/${query}`,
    );
  }

  createHierarchyNode(payload: FormData) {
    return this.http.post(this.baseUrl + "api/v1/master/hierarchy/", payload);
  }

  updateHierarchyNode(id: number, payload: FormData) {
    return this.http.patch(
      `${this.baseUrl}api/v1/master/hierarchy/${id}/`,
      payload,
    );
  }

  deleteHierarchyNode(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/master/hierarchy/${id}/`);
  }

  toggleSailorRegulator(id: number, isRegulator: boolean) {
    return this.http.post(
      `${this.baseUrl}api/v1/master/hierarchy/toggle_sailor_regulator/`,
      { id, is_reg: isRegulator },
    );
  }

  getRegulatorsTree() {
    return this.http.get<RegulatorsTreeResponse>(
      this.baseUrl + "api/v1/master/hierarchy/regulators_tree/",
    );
  }

  getRegulatorSailors(regulatorId: number) {
    return this.http.get<RegulatorSailorsResponse>(
      `${this.baseUrl}api/v1/master/hierarchy/regulator_sailors/?regulator_id=${regulatorId}`,
    );
  }

  assignRegulatorBulk(regulatorId: number, sailorIds: number[]) {
    return this.http.post(
      `${this.baseUrl}api/v1/master/hierarchy/assign_regulator_bulk/`,
      { regulator_id: regulatorId, sailor_ids: sailorIds },
    );
  }

  getEvents() {
    return this.http.get<UpcomingEventApi[]>(this.baseUrl + "api/v1/events/");
  }

  createEvent(payload: FormData | Record<string, unknown>) {
    return this.http.post<UpcomingEventApi>(this.baseUrl + "api/v1/events/", payload);
  }

  updateEvent(id: number, payload: FormData) {
    return this.http.patch<UpcomingEventApi>(`${this.baseUrl}api/v1/events/${id}/`, payload);
  }

  deleteEvent(id: number) {
    return this.http.delete(`${this.baseUrl}api/v1/events/${id}/`);
  }

  getBirthdays() {
    return this.http.get(this.baseUrl + "api/v1/user/ships/birthdays/");
  }

  getPersonnelEvents() {
    return this.http.get<PersonnelEventsResponse>(
      `${this.baseUrl}api/v1/user/personnel-events/`,
    );
  }

  getKnowYourShip() {
    return this.http.get(this.baseUrl + "api/v1/master/ships/know-your-ship/");
  }

  getDailyOrders() {
    return this.http.get(
      this.baseUrl + "api/v1/master/order-duties/daily-orders/",
    );
  }

  getDutyRosters() {
    return this.http.get(
      this.baseUrl + "api/v1/master/order-duties/duty-rosters/",
    );
  }

  getRoutines() {
    return this.http.get<{ routines: string[] }>(
      this.baseUrl + "api/v1/master/order-duties/routines/",
    );
  }

  saveDailyOrder(payload: SaveDailyOrderPayload | FormData, context?: HttpContext) {
    return this.http.post(
      this.baseUrl + "api/v1/master/order-duties/save-daily-order/",
      payload,
      { context }
    );
  }

  saveDailyOrders(payload: FormData, context?: HttpContext) {
    return this.http.post(
      this.baseUrl + "api/v1/master/order-duties/save-daily-orders/",
      payload,
      { context }
    );
  }

  // DART Initiation
  initiateDart(payload: Record<string, unknown> | FormData) {
    return this.http.post(`${this.baseUrl}api/v1/dart/initiate_dart/`, payload, {
      context: skipFeedback({ loader: true, toast: true }),
    });
  }

  getInboxMessages() {
    return this.get<InboxMessage[]>("api/v1/user/messages/inbox/");
  }
  getInboxUnreadCount(mailbox: "inbox" | "outbox") {
    return this.http.get<{ count: number }>(
      `${this.baseUrl}api/v1/user/messages/unread_count/`,
      {
        params: {
          mailbox,
        },
      },
    );
  }

  markMessagesRead(messageIds: number[]) {
    return this.post("api/v1/user/messages/mark_read/", {
      message_ids: messageIds,
    });
  }

  getOutboxMessages() {
    return this.get<InboxMessage[]>("api/v1/user/messages/outbox/");
  }

  sendMessage(payload: Record<string, unknown>) {
    return this.post("api/v1/user/messages/", payload);
  }

  getMaintenanceDashboard(): Observable<MaintenanceDashboardResponse> {
    return this.get<MaintenanceDashboardResponse>(
      "api/v1/dart/maintainance_overview_details/",
    );
  }
  getOpenDartsAndABER(params?: Record<string, string>): Observable<OpenDefectsResponse> {
    const query = params && Object.keys(params).length
      ? `?${new URLSearchParams(params).toString()}`
      : "";
    return this.get<OpenDefectsResponse>(`api/v1/dart/pending_defect/${query}`);
  }
  postCmmsDart(payload: unknown[]) {
    return this.post("api/v1/cmms/dart", payload, skipFeedback({ loader: true, toast: true }));
  }
  getDartDetails(dart_id: number) {
    return this.http.get(`${this.baseUrl}api/v1/dart/get_dart_details/`, {
      params: {
        dart_id: dart_id.toString(),
      },
    });
  }
  createRA(defectIds: number[]) {
    return this.post<CreateRAResponse>(
      "api/v1/dart/create_ra/",
      { defect_ids: defectIds },
      skipFeedback({ loader: true, toast: true }),
    );
  }
  exportRA(payload: {
    yard: string;
    dtg_date: string;
    dtg_hour: string;
    dtg_minute: string;
    export_format: string;
    dart_ids: number[];
    remarks_data: Record<number, string>;
    ss_remarks_data: Record<number, string>;
    dl_type: 'RA';
  }) {
    return this.post<{
      status: string;
      message: string;
      data: {
        ra_group_id: string;
        total_records: number;
        yard: string;
        dtg: string;
        export_format: string;
        dl_type: string;
        download_url: string;
      };
    }>("api/v1/dart/export_pending_defects_accdb/", payload, skipFeedback({ loader: true, toast: true }));
  }
  createDL(defectIds: number[]) {
    return this.post<CreateDLResponse>(
      "api/v1/dart/createdlfun/",
      { dl_defect_ids: defectIds },
      skipFeedback({ loader: true, toast: true }),
    );
  }
  /** `dart_id` here is actually the InitiateRADL draft row's own id, per the
   * backend serializer's help_text — matches the wire contract's naming. */
  saveDLRows(rows: { dart_id: number; remarks?: string; additional_remarks?: string }[]) {
    return this.post<{ status: string; message: string }>(
      "api/v1/dart/save_dl_rows/",
      { rows },
      skipFeedback({ loader: true, toast: true }),
    );
  }
  deleteDLRow(dlId: number) {
    return this.post<{ status: string; message: string }>(
      "api/v1/dart/delete_dl_row/",
      { dl_id: dlId },
      skipFeedback({ loader: true, toast: true }),
    );
  }
  exportDLII(
    exportPath: string,
    payload: {
      yard: string;
      export_format: string;
      refit_Type?: number;
      row_data: { dart_id: number; dl_id: number; dl_number: string; additional_remark: string; ss_remark: string }[];
    },
  ) {
    return this.post<{
      status: string;
      message: string;
      data: { ra_dl_name: string; total_records: number; yard: string; download_url: string };
    }>(`api/v1/dart/${exportPath}/`, payload, skipFeedback({ loader: true, toast: true }));
  }
  getCompleteDartList() {
    return this.get<CompleteDartListItem[]>("api/v1/dart/complete_dart_list/");
  }
  searchRefitRoutines(filters?: {
    section?: number | string;
    equipmentId?: number | string;
    equipment?: string;
    routineName?: string;
    converted?: boolean;
  }): Observable<RefitSearchListResponse> {
    const params = new URLSearchParams();
    if (filters?.section) params.set('section', String(filters.section));
    if (filters?.equipmentId) params.set('equipment_id', String(filters.equipmentId));
    if (filters?.equipment) params.set('equipment', filters.equipment);
    if (filters?.routineName) params.set('routine_name', filters.routineName);
    if (filters?.converted !== undefined) params.set('converted', String(filters.converted));
    const query = params.toString();
    const queryString = query ? `?${query}` : '';
    return this.get<RefitSearchListResponse>(
      `api/v1/refit/refit_search/${queryString}`,
    );
  }
  getRefitRoutineDetail(id: number): Observable<RefitRoutineDetail> {
    return this.get<RefitRoutineDetail>(`api/v1/refit/refit_search/${id}/`);
  }
  generateDl1(pkList: number[]) {
    return this.post<{ status: string; message: string }>(
      "api/v1/ems/generatedl1/",
      { pk_list: pkList },
      skipFeedback({ loader: true, toast: true }),
    );
  }
  getDlDraftRows(filters?: {
    search?: string;
    page?: number;
    pageSize?: number;
  }): Observable<GenerateDl1ListResponse> {
    const params = new URLSearchParams();
    if (filters?.search) params.set('search', filters.search);
    if (filters?.page) params.set('page', String(filters.page));
    if (filters?.pageSize) params.set('page_size', String(filters.pageSize));
    const query = params.toString();
    const queryString = query ? `?${query}` : '';
    return this.get<GenerateDl1ListResponse>(`api/v1/ems/generatedl1/${queryString}`);
  }
  deleteDlDraftRow(id: number) {
    return this.post<{ status: string; message?: string }>(
      "api/v1/ems/delete_dl_draft_row/",
      { id },
      skipFeedback({ loader: true }),
    );
  }
  saveDlDraftRows(payload: SaveDlDraftRowsPayload) {
    return this.post<{ status: string; message?: string }>(
      "api/v1/ems/save_dl_draft_rows/",
      payload,
      skipFeedback({ loader: true }),
    );
  }
  exportDl1Accdb(yardKey: 'ndmbi' | 'ndv' | 'nsrykoc' | 'nsrykar' | 'nsrypdr') {
    return this.post<{ status: string; message: string }>(
      `api/v1/ems/export_dl1_accdb_${yardKey}/`,
      {},
      skipFeedback({ loader: true, toast: true }),
    );
  }
  getGeneratedDl1Reports() {
    return this.get<{ report_rows: GeneratedDl1ReportRow[] }>("api/v1/ems/generatedl1_list/");
  }
  getGeneratedDl1ReportInnerRows(id: number) {
    return this.get<{ data: GeneratedDl1ReportInnerRow[] }>(`api/v1/ems/report_inner_rows/${id}/`);
  }
  getCloseDefectById(defectId: number): Observable<CloseDefectResponse> {
    return this.get<CloseDefectResponse>(
      `api/v1/dart/complete_defect/${defectId}/`,
    );
  }
  getCloseRoutineById(defectId: number): Observable<CloseRoutineResponse> {
    return this.get<CloseRoutineResponse>(
      `api/v1/ems/initiate_close_routine/${defectId}/`,
    );
  }
  getRoutineById(id: number) {
    return this.get<{ result: SearchDetailResultItem[] }>(
      `api/v1/ems/search_detail/${id}/`,
    );
  }
  getRoutinePlanById(id: number) {
    return this.get<RoutinePlanResponse>(`api/v1/ems/plan_routine/${id}/`);
  }
  planRoutineSave(
    id: number,
    payload: {
      planned_commencement_date?: string;
      spares_required?: 'YES' | 'NO';
      spares?: { pattern: string; qty: number; inventory_type?: string }[];
    },
  ) {
    return this.post<{
      status: string;
      message: string;
      routine_id: number;
      planned_routine_id: number | null;
    }>(`api/v1/ems/plan_routine_save/${id}/`, payload);
  }
  planRoutineMultiSave(payload: { selected_ids: string; planned_commencement_date?: string }) {
    return this.post<{
      status: string;
      message: string;
      planned_count: number;
      planned_ids: number[];
    }>('api/v1/ems/plan_routine_multi_save/', payload);
  }
  updateCloseDefect(defectId: number, payload: FormData) {
    return this.post(
      `api/v1/dart/complete_defect/${defectId}/`,
      payload,
      skipFeedback({ loader: true, toast: true }),
    );
  }
  updateCloseFUSSRoutine(defectId: number, payload: CloseRoutinePayload) {
    return this.post(
      `api/v1/ems/initiate_close_routine/${defectId}/`,
      payload,
      skipFeedback({ loader: true, toast: true }),
    );
  }
  getSFDData(): Observable<SFDDashboardResponse> {
    return this.get<SFDDashboardResponse>("api/v1/sfd/dashboard/");
  }
  getUniqueMaintopRoutinesData(
    equipmentName?: string,
    search?: string,
  ): Observable<UniqueMaintopResponse> {
    const params = new URLSearchParams();
    if (equipmentName && equipmentName !== 'All') params.set('equipment_name', equipmentName);
    if (search) params.set('search', search);
    const query = params.toString();
    const qs441 = query ? '?' + query : '';
    return this.get<UniqueMaintopResponse>(
      `api/v1/ems/unique_maintop/${qs441}`,
    );
  }
  getRHBasedRoutinesData(search?: string): Observable<RoutineResponse> {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.get<RoutineResponse>(`api/v1/ems/result_specific_runninghr/${query}`);
  }
  getCalenderRoutinesData(search?: string): Observable<RoutineResponse> {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.get<RoutineResponse>(`api/v1/ems/result_specific_calender/${query}`);
  }
  getFUSSTriggerListRoutinesData(filters?: {
    subDept?: string;
    equipment?: string;
    routineName?: string;
    search?: string;
  }): Observable<FUSSTriggerListResponse> {
    const params = new URLSearchParams();
    if (filters?.subDept && filters.subDept !== 'All') params.set('sub_dept', filters.subDept);
    if (filters?.equipment && filters.equipment !== 'All') params.set('equipment', filters.equipment);
    if (filters?.routineName && filters.routineName !== 'All') params.set('routine_name', filters.routineName);
    if (filters?.search) params.set('search', filters.search);
    const query = params.toString();
    const qs465 = query ? '?' + query : '';
    return this.get<FUSSTriggerListResponse>(
      `api/v1/ems/fuss_trigger_list/${qs465}`,
    );
  }
  getABERTriggerRoutinesData(filters?: {
    nomenclature?: string;
    compartment?: string;
    search?: string;
  }): Observable<EquipmentDueForAberResponse> {
    const params = new URLSearchParams();
    if (filters?.nomenclature && filters.nomenclature !== 'All') params.set('nomenclature', filters.nomenclature);
    if (filters?.compartment && filters.compartment !== 'All') params.set('compartment', filters.compartment);
    if (filters?.search) params.set('search', filters.search);
    const query = params.toString();
    const qs479 = query ? '?' + query : '';
    return this.get<EquipmentDueForAberResponse>(
      `api/v1/ems/aber_trigger_list/${qs479}`,
    );
  }
  // Routines Dashboard (EMS home)
  getEmsThumbnail() {
    return this.get<EmsThumbnailResponse>("api/v1/ems/thumbnail/");
  }
  getEmsSections() {
    return this.get<EmsSectionsResponse>("api/v1/ems/section_name/");
  }
  getEmsEquipmentNames(sectionId?: number | string) {
    return this.get<{ equipment_name: Record<string, number> }>(
      sectionId ? `api/v1/ems/equipment_name/${sectionId}/` : "api/v1/ems/equipment_name/",
    );
  }
  getSectionRhsiBarchart(sectionId: number) {
    return this.get<SectionRhsiBarchartResponse>(`api/v1/ems/barchart/${sectionId}/`);
  }
  updateEmsTotalRunningHours(payload: {
    equipment: number;
    rhsi: number;
    rhsi_updated_until: string;
  }) {
    return this.post<{ message: string }>(
      "api/v1/ems/create_total_running_hrs/",
      payload,
      skipFeedback({ loader: true, toast: true }),
    );
  }
  updateEmsEquipmentState(payload: UpdateEquipmentStatePayload) {
    return this.post<{ success: boolean; message: string }>(
      "api/v1/ems/update_equipment_state/",
      payload,
      skipFeedback({ loader: true, toast: true }),
    );
  }
  saveEmsMonthlyRunningHours(payload: SaveMonthlyRunningHoursPayload) {
    return this.post<{ success: boolean; message: string }>(
      "api/v1/ems/monthly_save/",
      payload,
      skipFeedback({ loader: true, toast: true }),
    );
  }
  getEmsEquipmentHistory(equipmentId: number) {
    return this.get<EquipmentHistoryResponse>(
      `api/v1/ems/get_equipment_history/${equipmentId}/`,
    );
  }
  getMaintainanceOverviewKpiData() {
    return this.get("api/v1/dart/maintainance_overview/kpis/");
  }
  getSearchPlanData(filters?: {
    subDepartment?: number | string;
    equipment?: number | string;
    routineType?: string;
    routineName?: string;
    search?: string;
  }): Observable<EmsSearchResultItem[]> {
    const params = new URLSearchParams();
    if (filters?.subDepartment) params.set('section', String(filters.subDepartment));
    if (filters?.equipment) params.set('equipment_name', String(filters.equipment));
    if (filters?.routineType) params.set('routine_category', filters.routineType);
    if (filters?.routineName) params.set('routine_name', filters.routineName);
    // NOTE: backend api/v1/ems/search/ does not yet read this param — needs server-side support.
    if (filters?.search) params.set('search', filters.search);
    const query = params.toString();
    const queryString = query ? `?${query}` : '';
    return this.get<EmsSearchResultItem[]>(
      `api/v1/ems/search/${queryString}`,
    );
  }
  getSFDKpiData() {
    return this.get("api/v1/sfd/dashboard/kpis/");
  }
  getRaiseFussDetails(selectedIds: number[]): Observable<RaiseFussResponse> {
    return this.get<RaiseFussResponse>(
      `api/v1/ems/mulraisefuss/?selected_ids=${selectedIds.join(",")}`,
    );
  }
  getPlanedRoutines(filters?: {
    sectionId?: number | string;
    equipmentNameId?: number | string;
    routineCategory?: string;
    routineName?: string;
    search?: string;
  }) {
    const params = new URLSearchParams();
    if (filters?.sectionId) params.set('section', String(filters.sectionId));
    if (filters?.equipmentNameId) params.set('equipment_name', String(filters.equipmentNameId));
    if (filters?.routineCategory) params.set('routine_category', filters.routineCategory);
    if (filters?.routineName) params.set('routine_name', filters.routineName);
    if (filters?.search) params.set('search', filters.search);
    const query = params.toString();
    const qs549 = query ? '?' + query : '';
    return this.get(`api/v1/ems/planned-routines/${qs549}`);
  }
  getFUSSRaisedRoutines() {
    return this.get("api/v1/ems/fuss_raised_routines/");
  }
  getSearchDetailPlan(pk: number) {
    return this.get<{ result: PlannedRoutineDetail[] }>(`api/v1/ems/search_detail_plan/${pk}/`);
  }
  deletePlannedRoutine(pk: number) {
    return this.get<{ success: boolean; message: string }>(
      `api/v1/ems/delete_planned_routine/${pk}/`,
    );
  }
  raiseFuss(payload: RaiseFussPayload): Observable<RaiseFussSaveResponse> {
    return this.post<RaiseFussSaveResponse>(
      "api/v1/ems/mulraisefuss/",
      payload,
      skipFeedback({ loader: true, toast: true }),
    );
  }

  private get<T>(url: string) {
    return this.http.get<T>(`${this.baseUrl}${url}`).pipe(
      catchError(() => {
        const dummy = getDummyResponse(url);
        if (dummy !== undefined) {
          console.warn(`[Call] Backend unavailable for "${url}" — serving dummy data.`);
          return of(dummy as T);
        }
        throw new Error(`No response and no dummy fallback registered for "${url}"`);
      }),
    );
  }

  private post<T = unknown>(url: string, payload: unknown, context?: HttpContext) {
    return this.http.post<T>(`${this.baseUrl}${url}`, payload, context ? { context } : {});
  }

  private put<T = unknown>(url: string, payload: unknown, context?: HttpContext) {
    return this.http.put<T>(`${this.baseUrl}${url}`, payload, context ? { context } : {});
  }

  private delete<T = unknown>(url: string) {
    return this.http.delete<T>(`${this.baseUrl}${url}`);
  }

  // DART Spares

  getDartSpares(type: string) {
    return this.http.get(
      `${this.baseUrl}api/v1/dart/get_dart_spares_data/?type=${type}`,
    );
  }

  updateRhsiEquipment(id: number, payload: Record<string, unknown>) {
    return this.http.put(
      `${this.baseUrl}api/v1/sfd/rhsi-equipment/${id}/`,
      payload,
    );
  }

  // DART Form Master Data
  getDartMasterData(departmentId: number) {
    return this.get(`api/v1/dart/add_dart/?department_id=${departmentId}`);
  }
  // DART Dashboard (Op Maintenance)
  getDartDashboard(departmentId: number) {
    return this.get<DartDashboardResponse>(
      `api/v1/dart/dartdashboard/?department_id=${departmentId}`,
    );
  }
  getSubDeptDefects(subDept: string) {
    return this.get<{ success: boolean; data: SubDeptDefectRow[] }>(
      `api/v1/dart/get_sub_dept_defects/?sub_dept=${encodeURIComponent(subDept)}`,
    );
  }
  getMaintenancePeriodsList() {
    return this.get<MaintenancePeriodRow[]>(`api/v1/dart/maintenance_periods/`);
  }
  // get nomanclature name onchange of equipment name in defect
  getEquipmentObjects(code: string) {
    return this.http.get(
      `${this.baseUrl}api/v1/dart/get-equipment-objects/?code=${code}`,
    );
  }

  // get noman clature behalf on equipmnet code

  getNomenclatureDetails(nomenclatureId: number) {
    return this.http.get(
      `${this.baseUrl}api/v1/dart/get_nomenclature_details/?nomenclature=${nomenclatureId}`,
    );
  }
  // DART History Landing Page
  getDartHistory() {
    return this.get<DartHistoryResponse>("api/v1/dart/history/data/");
  }

  // DART History Filtered Search — auto-fires on every filter change (see
  // history.component.ts), so it's opted out of the global mutation loader/toast
  // that POST requests otherwise get by default; it's a read/filter, not a mutation.
  getFilteredDartHistory(payload: Record<string, unknown>) {
    return this.post<DartHistoryResponse>(
      "api/v1/dart/history/filtered_data/",
      payload,
      skipFeedback({ loader: true, toast: true }),
    );
  }
  getRefitAndOperationalOccation(search?: string) {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    return this.get(`api/v1/dart/refit_and_operational_occation/${query}`);
  }

  // Dart defect submig guarantee defect

  createGuaranteeDefect(payload: Record<string, unknown> | FormData) {
    return this.http.post(
      `${this.baseUrl}api/v1/dart/initiate_dart/`,
      payload,
      {
        observe: "response",
        context: skipFeedback({ loader: true, toast: true }),
      },
    );
  }

  // ship confing calls
  getRhsiEquipment() {
    return this.http.get(`${this.baseUrl}api/v1/sfd/rhsi-equipment/`);
  }

  getEquipmentMasterData() {
    return this.http.get(
      `${this.baseUrl}api/v1/sfd/rhsi-equipment/add-equipment-dropdown-values/`,
    );
  }

  //add ref sfd equipment  api/v1/sfd/rhsi-equipment/

  addEquipmentSfdRef(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/sfd/rhsi-equipment/`,
      payload,
      {
        observe: "response",
      },
    );
  }

  // add equipment in tranasaction

  addEquipmentTransaction(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/sfd/transaction-equipment/`,
      payload,
      {
        observe: "response",
      },
    );
  }
  getGeneratedDlIiReports() {
    return this.get<GeneratedDlIiReport[]>("api/v1/dart/generated-dl-ii-reports/");
  }
  // Slip History
  getSlipHistory(startDate?: string, endDate?: string, search?: string) {

    let params = new HttpParams();

    if (startDate) {
      params = params.set('start_date', startDate);
    }

    if (endDate) {
      params = params.set('end_date', endDate);
    }

    if (search) {
      params = params.set('search', search);
    }

    return this.http.get<SlipHistoryResponse>(
      `${this.baseUrl}api/v1/ems/slip-history/`,
      { params }
    );
  }
  // Closed Routine History
  getClosedRoutineHistory(search?: string) {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.get<ClosedRoutineApiResponse>(`api/v1/ems/closed_routines_list/${query}`);
  }
  getRoutineHistory(filters?: RoutineHistoryFilters) {
    const params = new URLSearchParams();
    if (filters?.subDept && filters.subDept !== 'All') params.set('sub_dept', filters.subDept);
    if (filters?.equipment && filters.equipment !== 'All') params.set('equipment', filters.equipment);
    if (filters?.routineName && filters.routineName !== 'All') params.set('routine_name', filters.routineName);
    if (filters?.search) params.set('search', filters.search);

    const query = params.toString();
    const qs740 = query ? '?' + query : '';
    return this.get<RoutineHistoryApiResponse>(
      `api/v1/ems/routine_history/${qs740}`,
    );
  }
  getRoutineHistoryTimelineData(pk: number, routineNo?: string) {
    const params = new URLSearchParams();
    if (routineNo && routineNo !== 'All') params.set('routine_no', routineNo);

    const query = params.toString();
    const qs749 = query ? '?' + query : '';
    return this.get<RoutineHistoryTimelineResponse>(
      `api/v1/ems/routine_history_timeline_data/${pk}/${qs749}`,
    );
  }
  getEquipmentRunningHistory(filters?: { equipment?: string; month?: string; search?: string }) {
    const params = new URLSearchParams();
    if (filters?.equipment && filters.equipment !== 'All') params.set('equipment', filters.equipment);
    if (filters?.month && filters.month !== 'All') params.set('month', filters.month);
    if (filters?.search) params.set('search', filters.search);
    const query = params.toString();
    const qs758 = query ? '?' + query : '';
    return this.get(`api/v1/ems/equipment_running_history/${qs758}`);
  }

  private buildMaintenancePlanQuery(subDept?: number, search?: string): string {
    const params = new URLSearchParams();
    if (subDept) params.set('sub_dept', String(subDept));
    if (search) params.set('search', search);
    const query = params.toString();
    return query ? `?${query}` : '';
  }

  getWeeklyMaintenancePlan(subDept?: number, search?: string): Observable<MaintenanceApiResponse> {
    return this.get<MaintenanceApiResponse>(
      `api/v1/ems/weekly_maintenance_plan/${this.buildMaintenancePlanQuery(subDept, search)}`,
    );
  }

  getMaintenancePlan(period: string, subDept?: number, search?: string): Observable<MaintenanceApiResponse> {
    return this.get<MaintenanceApiResponse>(
      `api/v1/ems/maintenance_plan/${period}/${this.buildMaintenancePlanQuery(subDept, search)}`,
    );
  }
  /** Creates a new refit/operational period. Backend's POST handler always
   * requires `refit_type` — it has no `action`-based branching for edits. */
  refitAndOperationalOccation(payload: {
    action: string;
    period_id?: number;
    start_date: string;
    completion_date: string;
    refit_type?: string;
  }) {
    return this.http.post(
      `${this.baseUrl}api/v1/dart/refit_and_operational_occation/`,
      payload,
      { context: skipFeedback({ loader: true, toast: true }) },
    );
  }

  /** Edits an existing refit/operational period's dates — a separate PUT
   * handler on the same endpoint, taking only `period_id`/`start_date`/
   * `completion_date` (no `refit_type`, unlike the POST/create handler). */
  editRefitOccasionDates(payload: { period_id: number; start_date: string; completion_date: string }) {
    return this.http.put(
      `${this.baseUrl}api/v1/dart/refit_and_operational_occation/`,
      payload,
      { context: skipFeedback({ loader: true, toast: true }) },
    );
  }

  getDlHistory() {
    return this.http.get(`${this.baseUrl}api/v1/dl-monitoring/dl_history/`);
  }

  getHomeDashboard(period: string) {
    return this.http.get(`${this.baseUrl}api/v1/user/home-dashboard/`, {
      params: { period },
    });
  }

  getHomeDashboardKpis() {
    return this.http.get(`${this.baseUrl}api/v1/user/home-dashboard/kpis/`);
  }
  getDlDashboardCounts() {
    return this.http.get(
      `${this.baseUrl}api/v1/dl-monitoring/dashboard-counts/`,
    );
  }

  getDlDashboard() {
    return this.http.get(`${this.baseUrl}api/v1/dl-monitoring/dashboard/`);
  }

  getRefitDashboard() {
    return this.http.get(`${this.baseUrl}api/v1/refit/dashboard/`);
  }

  getDlMaster() {
    return this.http.get(`${this.baseUrl}api/v1/dl-monitoring/master/`);
  }

  getDlTracking() {
    return this.http.get(`${this.baseUrl}api/v1/dl-monitoring/dl_tracking/`);
  }

  getDl2Tracking() {
    return this.http.get(`${this.baseUrl}api/v1/dl-monitoring/dl2tracking/`);
  }

  getDl3Tracking() {
    return this.http.get(`${this.baseUrl}api/v1/dl-monitoring/dl3tracking/`);
  }

  updateDlTracking(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/dl-monitoring/update_dl_tracking/`,
      payload,
    );
  }

  closeDlTracking(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/dl-monitoring/close_dl_tracking/`,
      payload,
    );
  }

  syncNavyojana(payload: { dl_type: string }) {
    return this.http.post(
      `${this.baseUrl}api/v1/dl-monitoring/sync_navyojana/`,
      payload,
    );
  }

  importDlExcel(payload: FormData) {
    return this.http.post(
      `${this.baseUrl}api/v1/dl-monitoring/import-excel/`,
      payload,
    );
  }

  // transaction

  getAddEquipmentDropdownValues() {
    return this.get("api/v1/sfd/transaction-equipment/add-equipment-dropdown-values/");
  }

  getEquipmentList(params?: Record<string, string | number | boolean | readonly (string | number | boolean)[]>) {
    return this.http.get(
      `${this.baseUrl}api/v1/sfd/transaction-equipment/list/`,
      { params },
    );
  }

  // get one time routine list

  getOnetimeRoutineList(params?: Record<string, string | number | boolean | readonly (string | number | boolean)[]>) {
    return this.http.get(`${this.baseUrl}api/v1/ems/routine_init_data/`, { params });
  }

  getRoutineInitDetails(id: number | string) {
    return this.http.get(`${this.baseUrl}api/v1/ems/get_routine_init_details/${id}/`);
  }

  saveRoutineInit(payload: { routine_id: number; completion_date?: string | null; undertaken_rh?: string | null }) {
    return this.http.post(`${this.baseUrl}api/v1/ems/save_routine_init/`, payload, {
      context: skipFeedback({ loader: true }),
    });
  }

  removeEquipment(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/sfd/transaction-equipment/remove/`,
      payload,
    );
  }

  updateDl1Tracking(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/dl-monitoring/dl_tracking/update/`,
      payload,
    );
  }
  updateEquipmentTransaction(id: number, payload: FormData) {
    return this.http.put(
      `${this.baseUrl}api/v1/sfd/transaction-equipment/${id}/`,
      payload,
      {
        observe: "response",
      },
    );
  }


  // CMMS Routine Sync
  syncCmmsRoutine(): Observable<SyncCmmsResponse> {
    return this.http.get<SyncCmmsResponse>(`${this.baseUrl}api/v1/sfd/routine-sync/`);
  }

  // Generate Routine Schedules
  generateMissingRoutines() {
    return this.http.post(
      `${this.baseUrl}api/v1/ems/routines/generate/`,
      {},
      { context: skipFeedback({ loader: true, toast: true }) },
    );
  }

  addNewNomanClature(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/ems/routines/generate/`,
      payload,
      { context: skipFeedback({ loader: true, toast: true }) },
    );
  }

  updateDl2Tracking(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/dl-monitoring/dl2tracking/update/`,
      payload,
    );
  }

  updateDl3Tracking(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/dl-monitoring/dl3tracking/update/`,
      payload,
    );
  }

  editTransactionEquipment(payload: FormData) {
    return this.http.post(
      `${this.baseUrl}api/v1/sfd/transaction-equipment/edit/`,
      payload,
    );
  }
  changeEquipmentSerialNumber(payload: Record<string, unknown>) {
    return this.http.post(
      `${this.baseUrl}api/v1/sfd/transaction-equipment/save-equipment-change/`,
      payload,
      {
        observe: "response",
      },
    );
  }

  saveAberDefect(payload: Record<string, unknown>) {
    return this.initiateDart(payload);
  }

  // SWMM to CMMS Integration APIs
  initiateDartCmmsSync(pk: number) {
    return this.http.post(`${this.baseUrl}api/v1/swmmapi/initiate-dart-sync/${pk}/`, {});
  }

  completeDartCmmsSync(pk: number) {
    return this.http.post(`${this.baseUrl}api/v1/swmmapi/complete-dart-sync/${pk}/`, {});
  }

  initiateFussCmmsSync(pk: number) {
    return this.http.post(`${this.baseUrl}api/v1/swmmapi/initiate-fuss-sync/${pk}/`, {});
  }

  syncCompletedRoutines() {
    return this.http.post(`${this.baseUrl}api/v1/swmmapi/completed-routine-sync/`, {});
  }

  receiveCompletedRoutines(payload: Record<string, unknown>) {
    return this.http.post(`${this.baseUrl}api/v1/swmmapi/receive_completed_routine/`, payload);
  }

  syncSrarReportToCmms(pk: string) {
    return this.http.get(`${this.baseUrl}api/v1/swmmapi/srar_api/srar_sync/${pk}/`);
  }

  syncSrarByMonthYear(month: string, year: number) {
    return this.http.get(`${this.baseUrl}api/v1/swmmapi/srar_api/srar_pull_from_cmms/?month=${month}&year=${year}`);
  }
}
