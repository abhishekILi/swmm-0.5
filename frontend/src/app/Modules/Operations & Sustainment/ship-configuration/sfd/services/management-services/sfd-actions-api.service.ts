import { HttpParams } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { AppService } from "../../../../../../Core/services/app/app.service";
import { skipFeedback } from "../../../../../../Core/services/common/http-feedback";
import { SfdCategory } from "../../management/sfd-actions-fields.config";
import {
  ApprovalTrackingUpdatePayload,
  ApprovalTrackingUpdateResult,
  CascadingDropdownParams,
  CascadingDropdownValues,
  CompartmentDetail,
  EquipmentDependencies,
  EquipmentTransactionPatchPayload,
  GetTransactionListParams,
  PaginatedResponse,
  RawApprovalTrackingRow,
  RawEquipmentTransactionRow,
  RawRecentActivityRow,
  RawRemovalDetails,
  RawUpdateSrNoDetails,
  RecentActivityParams,
  RemovalRequestPayload,
  SfdListFilterOptions,
  TransactionCreateCommonFields,
  TransactionCreatePayload,
  UpdateSerialNoPayload,
} from "./sfd-actions.models";


export interface RawAddSfdEquipmentOptions {
  equipment_name: { universal_id_m_equipment: string; equipment_name: string }[];
  system_name: { universal_id_m_equipment: string; system_name: string }[][];
  model: { universal_id_m_equipment: string; model: string }[];
  Nomenclature: { universal_id_m_equipment: string; Nomenclature: string }[];
  "OEM Name": { universal_id_M_supplier: string; manufacturer_name: string }[];
  Supplier: { universal_id_M_supplier: string; supplier_name: string }[];
  "OEM Part No": { universal_id_m_equipment: string; oem_part_no: string }[];
  "Compartment Name": { compartment_id: number; compartment_name: string }[];
  "Shelf Life": { shelf_lifes_id: number; shelf_lifes_name: number }[];
  "Equipment Section": { universal_id_m_sub_department: string; sub_department_name: string }[];
  "Equipment Type": { universal_id_ch_master_equipment_type: string; name: string }[];
}

function toHttpParams(params: object): HttpParams {
  let httpParams = new HttpParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      httpParams = httpParams.set(key, String(value));
    }
  }
  return httpParams;
}
@Injectable({ providedIn: "root" })
export class SfdActionsApiService {
  private readonly appService = inject(AppService);
  private readonly mutationContext = () => ({ context: skipFeedback({ loader: true, toast: true }) });

  private readonly categoryTransactionPaths: Record<SfdCategory, string> = {
    "CAT I": "api/v1/sfd/transaction/cat1/",
    "CAT II": "api/v1/sfd/transaction/cat2/",
    "CAT III": "api/v1/sfd/transaction/cat3/",
    "Survey & Demand": "api/v1/sfd/transaction/survey-demand/",
    "Local Purchase": "api/v1/sfd/transaction/others/",
  };

  createCategoryTransaction(category: SfdCategory, payload: TransactionCreatePayload) {
    return this.appService.post(this.categoryTransactionPaths[category], payload, this.mutationContext());
  }

  /** No per-category update route was given — Update keeps using the existing `sfd-list/{id}/` resource. */
  updateTransaction(equipmentShipId: number | string, payload: TransactionCreateCommonFields) {
    return this.appService.put(
      `api/v1/sfd/sfd-list/${equipmentShipId}/`,
      payload,
      this.mutationContext(),
    );
  }

  /** Partial update of an `EquipmentTransaction` row — used by the Record Edit (qty/serial) modal. */
  patchTransaction(equipmentShipId: number | string, payload: EquipmentTransactionPatchPayload) {
    return this.appService.patch(
      `api/v1/sfd/sfd-list/${equipmentShipId}/`,
      payload,
      this.mutationContext(),
    );
  }

  /** No trailing slash — the backend route (`sfd/urls.py`) is registered without one and does not append-slash redirect. */
  getAddSfdEquipmentDropdowns() {
    return this.appService.get<RawAddSfdEquipmentOptions>("api/v1/sfd/add-sfd-equipement/dropdowns");
  }

  /** Equipment/System pick cascade — `EquipmentDropdownAPIView` only supports `universal_id_m_equipment`. */
  getEquipmentCascade(params: CascadingDropdownParams) {
    return this.appService.get<CascadingDropdownValues>("api/v1/sfd/get_equipment/", {
      params: toHttpParams(params),
    });
  }

  /** Compartment pick cascade — the real source of deck/frame/location data for a Compartment Name pick. */
  getCompartment(compartmentId: number) {
    return this.appService.get<CompartmentDetail>(`api/v1/sfd/compartments/${compartmentId}/`);
  }

  /** Recent Activity popup (SFD Management header). */
  getRecentActivity(params: RecentActivityParams) {
    return this.appService.get<RawRecentActivityRow[]>("api/v1/sfd/recent-activity/", {
      params: toHttpParams(params),
    });
  }

  /** Table grid — real server-side pagination via `page`/`page_size`. */
  getTransactionList(params: GetTransactionListParams) {
    return this.appService.get<PaginatedResponse<RawEquipmentTransactionRow>>("api/v1/sfd/sfd-list/", {
      params: toHttpParams(params),
    });
  }

  /** Active list filter dropdowns — distinct values across the FULL active dataset, not just
   * whatever page is currently loaded in the grid. */
  getSfdListFilterOptions() {
    return this.appService.get<SfdListFilterOptions>("api/v1/sfd/sfd-list/filter-options/");
  }

  /** Dependency check before Remove — always `{open_defects: [], maintenance_routines: []}` today (a backend stub), but wired to the real route. */
  getOpenDependencies(equipmentShipId: number | string) {
    return this.appService.get<EquipmentDependencies>(
      `api/v1/sfd/sfd-list/${equipmentShipId}/open-dependencies/`,
    );
  }

  /** Removal Details form prefill — the equipment's current nomenclature/serial/dept/compartment, shown read-only above the form. */
  getRemovalDetails(equipmentShipId: number | string) {
    return this.appService.get<RawRemovalDetails>(
      `api/v1/sfd/sfd-list/${equipmentShipId}/remove-details/`,
    );
  }

  /** Removal Details form submit — creates a `RemoveEquipmentRequest` (`request_type: 1`), later surfaced on `GET approval-tracking/`. */
  submitRemoval(equipmentShipId: number | string, payload: RemovalRequestPayload) {
    return this.appService.post(
      `api/v1/sfd/sfd-list/${equipmentShipId}/remove/`,
      payload,
      this.mutationContext(),
    );
  }

  /** Change Serial Number form prefill — current nomenclature/serial/dept/maintop + installation authority/date. */
  getUpdateSrNoDetails(equipmentShipId: number | string) {
    return this.appService.get<RawUpdateSrNoDetails>(
      `api/v1/sfd/sfd-list/${equipmentShipId}/update_sr_no_details/`,
    );
  }

  /** Change Serial — the real endpoint; creates a `RemoveEquipmentRequest` (`request_type: 2`). */
  updateSerialNumber(equipmentShipId: number | string, payload: UpdateSerialNoPayload) {
    return this.appService.post(
      `api/v1/sfd/sfd-list/${equipmentShipId}/update_sr_no/`,
      payload,
      this.mutationContext(),
    );
  }

  /** "View Approval Status" grid — a flat, unpaginated array (no `results`/`count` wrapper). */
  getApprovalTracking() {
    return this.appService.get<RawApprovalTrackingRow[]>("api/v1/sfd/approval-tracking/");
  }

  /** Resubmits a "Returned" approval request with corrected details — `request_id` is a query
   * param, not a body field or URL segment (see `ApprovalTrackingUpdatePayload`'s doc for the
   * body-field-name caveats). */
  updateApprovalTracking(requestId: string, payload: ApprovalTrackingUpdatePayload) {
    return this.appService.put<ApprovalTrackingUpdateResult>("api/v1/sfd/approval-tracking/", payload, {
      params: toHttpParams({ request_id: requestId }),
    });
  }
}
