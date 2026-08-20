import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { environment } from "../../../../environments/environment";
import { catchError, Observable, of } from "rxjs";
import {
  SrarLookupRecord,
  SrarRecord,
  SrarReportDetail,
  SrarAnalyticsKpis,
  SrarAnalyticsMonthlyTrendItem,
  SrarAnalyticsMonthlyTrendResponse,
  SrarAnalyticsYearlyStatusItem,
  SrarAnalyticsYearlyStatusResponse,
  SrarAnalyticsDashboardSummary,
  SrarApiResponse,
  SrarMasterItem,
  EquipmentValidityItem,
  SrarCarryForward,
  ExportSrarResponse
} from "../../models/srar.model";

// Re-export models for centralized access
export * from "../../models/srar.model";

interface SrarCmmsSyncResponse {
  status?: boolean | string;
  message?: string;
  [key: string]: unknown;
}

interface SrarMasterEquipmentOnly extends SrarLookupRecord {
  equipment_type_id?: number | string;
  equipment_desc?: string;
  srar_txt?: string;
  srar_type?: string;
  equipment_category_code?: string;
  [key: string]: unknown;
}

@Injectable({
  providedIn: "root",
})
export class SrarService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = environment.apiUrl + "api/v1/srar/";

  // Fetch dashboard summary list of reports
  getDashboard(): Observable<SrarRecord[]> {
    return this.http.get<SrarRecord[]>(`${this.baseUrl}dashboard/`).pipe(
      catchError(() => of([]))
    );
  }

  // Get full nested details of a report for editing / modal view
  getReportDetails(headerId: number): Observable<SrarReportDetail> {
    return this.http.get<SrarReportDetail>(`${this.baseUrl}report/edit/${headerId}/`);
  }

  // Get carry-forward values (fuel/AVCAT balance, R/H since installation) from the
  // previous month's SRAR for a ship, matched per-equipment by eqpt_code/eqpt_name
  getCarryForward(shipId: number | null | undefined, month: number, year: number): Observable<SrarCarryForward> {
    const shipParam = shipId ? `ship=${shipId}&` : "";
    const params = `${shipParam}month=${month}&year=${year}`;
    return this.http.get<SrarCarryForward>(`${this.baseUrl}report/carry-forward/?${params}`).pipe(
      catchError(() => of(this.getEmptyCarryForward()))
    );
  }

  private getEmptyCarryForward(): SrarCarryForward {
    return {
      fuel_balance_last_month: 0,
      avcat_balance_last_month: 0,
      injector_fip: [],
      gas_turbine: [],
      reduction_gear: []
    };
  }

  // Save the entire report and all tabs using the composite save view
  saveCompositeSrar(payload: Record<string, unknown>): Observable<SrarApiResponse> {
    return this.http.post<SrarApiResponse>(`${this.baseUrl}report/save/`, payload);
  }

  // Save a specific step tab number
  saveTab(tabNumber: number, payload: Record<string, unknown>): Observable<SrarApiResponse> {
    return this.http.post<SrarApiResponse>(`${this.baseUrl}tab/${tabNumber}/save/`, payload);
  }

  // Finalize/approve the report
  finalizeReport(srarId: number, payload: Record<string, unknown>): Observable<SrarApiResponse> {
    return this.http.post<SrarApiResponse>(`${this.baseUrl}report/finalize/${srarId}/`, payload);
  }

  // Sync SRAR report to CMMS API using /api/v1/srar_sync/{id}/
  syncSrarToCmms(id: number | string): Observable<SrarApiResponse> {
    const syncUrl = `${environment.apiUrl}api/v1/srar_sync/${id}/`;
    return this.http.get<SrarApiResponse>(syncUrl);
  }

  // Export SRAR report PDF/file using /api/v1/srar/report/export/{headerId}/
  exportSrarReport(headerId: number | string): Observable<ExportSrarResponse> {
    return this.http.get<ExportSrarResponse>(`${this.baseUrl}report/export/${headerId}/`);
  }

  private getFullUrl(url: string): string {
    if (url.startsWith("http")) {
      return url;
    }
    const apiBase = environment.apiUrl.replace(/\/$/, "");
    const prefix = url.startsWith("/") ? "" : "/";
    return `${apiBase}${prefix}${url}`;
  }

  // Fetch exported file blob directly for browser downloading
  downloadFileBlob(downloadUrl: string): Observable<Blob> {
    return this.http.get(this.getFullUrl(downloadUrl), { responseType: "blob" });
  }

  // Fetch exported JSON file data
  fetchFileJson<T = Record<string, unknown>>(downloadUrl: string): Observable<T> {
    return this.http.get<T>(this.getFullUrl(downloadUrl));
  }

  // Sync SRAR to CMMS by Month and Year
  syncSrarWithCmms(month: string, year: number): Observable<SrarCmmsSyncResponse> {
    const swmmApiUrl = `${environment.apiUrl}api/v1/swmmapi/srar_api/srar_pull_from_cmms/`;
    return this.http.get<SrarCmmsSyncResponse>(`${swmmApiUrl}?month=${encodeURIComponent(month)}&year=${year}`);
  }

  // Sync only Ch_Master_Equipment_Type from CMMS into SRAR/SFD/SWMM master equipment tables
  syncChMasterEquipmentType(): Observable<SrarCmmsSyncResponse> {
    const swmmApiUrl = `${environment.apiUrl}api/v1/swmmapi/sfd/ch-master-equipment-type/sync/`;
    return this.http.get<SrarCmmsSyncResponse>(swmmApiUrl);
  }

  // CMMS-backed "Conducted By" options (Ch_Master_Full_Power_Conducted_By)
  getConductedByOptions(): Observable<{ id: string; label: string; value: string }[]> {
    return this.http.get<{ id: string; label: string; value: string }[]>(`${this.baseUrl}master/full-power-conducted-by/`).pipe(
      catchError(() => of([]))
    );
  }

  // CMMS-backed Lubricant picker (M_Lubricant) — name + unit
  getCmmsLubricants(): Observable<{ id: string; label: string; value: string; name: string; unit: string; type: string }[]> {
    return this.http.get<{ id: string; label: string; value: string; name: string; unit: string; type: string }[]>(`${this.baseUrl}master/cmms-lubricants/`).pipe(
      catchError(() => of([]))
    );
  }

  // CMMS-backed "Designed EEF" value for the ship's class (M_ShipClassEEF)
  getEefDesignedValue(): Observable<{ designed_eef: number | null }> {
    return this.http.get<{ designed_eef: number | null }>(`${this.baseUrl}master/eef-designed-value/`).pipe(
      catchError(() => of({ designed_eef: null }))
    );
  }

  // Master Equipment metadata lookup
  getEquipments(srarType?: string): Observable<SrarLookupRecord[]> {
    const url = srarType
      ? `${this.baseUrl}master/equipments/?srar_type=${srarType}`
      : `${this.baseUrl}master/equipments/`;
    return this.http.get<SrarLookupRecord[]>(url);
  }

  // Ship States master metadata lookup
  getShipStates(): Observable<SrarLookupRecord[]> {
    return this.http.get<SrarLookupRecord[]>(`${this.baseUrl}master/ship-states/`);
  }

  // Ship Locations master metadata lookup
  getShipLocations(): Observable<SrarLookupRecord[]> {
    return this.http.get<SrarLookupRecord[]>(`${this.baseUrl}master/ship-locations/`);
  }

  // Activity Types master metadata lookup
  getActivityTypes(): Observable<SrarLookupRecord[]> {
    return this.http.get<SrarLookupRecord[]>(`${this.baseUrl}master/activity-types/`).pipe(
      catchError(() => of([]))
    );
  }


  // Ship Activity Details master metadata lookup
  getActivityDetails(): Observable<SrarLookupRecord[]> {
    return this.http.get<SrarLookupRecord[]>(`${this.baseUrl}master/activity-details/`);
  }

  // Lubricant Units master metadata lookup
  getLubricantUnits(): Observable<SrarLookupRecord[]> {
    return this.http.get<SrarLookupRecord[]>(`${this.baseUrl}master/lubricant-units/`);
  }

  // EEF Reasons master metadata lookup
  getEefReasons(): Observable<SrarLookupRecord[]> {
    return this.http.get<SrarLookupRecord[]>(`${this.baseUrl}master/eef-reasons/`);
  }

  // All Dropdowns master consolidated lookup
  getAllDropdownOptions(): Observable<Record<string, SrarLookupRecord[]>> {
    return this.http.get<Record<string, SrarLookupRecord[]>>(`${this.baseUrl}master/dropdown-options/`);
  }

  // Analytics APIs (Dynamic Database Aggregations)
  getAnalyticsKpis(): Observable<SrarAnalyticsKpis> {
    return this.http.get<SrarAnalyticsKpis>(`${this.baseUrl}analytics/kpis/`);
  }

  getAnalyticsMonthlyTrend(): Observable<SrarAnalyticsMonthlyTrendResponse | SrarAnalyticsMonthlyTrendItem[]> {
    return this.http.get<SrarAnalyticsMonthlyTrendResponse | SrarAnalyticsMonthlyTrendItem[]>(`${this.baseUrl}analytics/monthly-trend/`);
  }

  getAnalyticsYearlyStatus(): Observable<SrarAnalyticsYearlyStatusResponse | SrarAnalyticsYearlyStatusItem[]> {
    return this.http.get<SrarAnalyticsYearlyStatusResponse | SrarAnalyticsYearlyStatusItem[]>(`${this.baseUrl}analytics/yearly-status/`);
  }

  getAnalyticsDashboardSummary(): Observable<SrarAnalyticsDashboardSummary> {
    return this.http.get<SrarAnalyticsDashboardSummary>(`${this.baseUrl}analytics/dashboard-summary/`);
  }

  // Fetch historical / archived SRAR reports list
  getHistoryLogs(): Observable<SrarRecord[]> {
    return this.http.get<SrarRecord[]>(`${this.baseUrl}history/`);
  }

  // Fetch Master Equipment items list
  getMasterEquipments(): Observable<SrarMasterItem[]> {
    return this.http.get<SrarMasterItem[]>(`${this.baseUrl}master/equipments-list/`);
  }

  // Fetch raw srar_masterequipment rows (CMMS master equipment types only)
  getMasterEquipmentsOnly(): Observable<SrarMasterEquipmentOnly[]> {
    return this.http.get<SrarMasterEquipmentOnly[]>(`${this.baseUrl}master/srar_master_equipments_only/`).pipe(
      catchError(() => of([]))
    );
  }

  // Fetch Equipment Validity items list
  getEquipmentValidityList(): Observable<EquipmentValidityItem[]> {
    return this.http.get<EquipmentValidityItem[]>(`${this.baseUrl}master/validity-list/`);
  }

  // Add new Master Equipment item
  addMasterEquipment(payload: Record<string, unknown>): Observable<SrarApiResponse<SrarMasterItem>> {
    return this.http.post<SrarApiResponse<SrarMasterItem>>(`${this.baseUrl}master/equipments/add/`, payload);
  }

  // Delete Master Equipment item
  deleteMasterEquipment(id: string): Observable<SrarApiResponse> {
    return this.http.delete<SrarApiResponse>(`${this.baseUrl}master/equipments/delete/${id}/`);
  }

  // Linked Equipments CRUD
  getLinkedEquipments(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(`${this.baseUrl}crud/linked-equipments/`);
  }

  addLinkedEquipment(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.baseUrl}crud/linked-equipments/`, payload);
  }

  // Equipment Type Lists CRUD
  getEquipmentTypeLists(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(`${this.baseUrl}crud/equipment-type-lists/`);
  }

  addEquipmentTypeList(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.baseUrl}crud/equipment-type-lists/`, payload);
  }

  // Equipment Validities CRUD
  getEquipmentValidities(): Observable<Record<string, unknown>[]> {
    return this.http.get<Record<string, unknown>[]>(`${this.baseUrl}crud/equipment-validities/`);
  }

  addEquipmentValidity(payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${this.baseUrl}crud/equipment-validities/`, payload);
  }

  updateEquipmentValidity(id: number | string, payload: Record<string, unknown>): Observable<Record<string, unknown>> {
    return this.http.put<Record<string, unknown>>(`${this.baseUrl}crud/equipment-validities/${id}/`, payload);
  }
}
