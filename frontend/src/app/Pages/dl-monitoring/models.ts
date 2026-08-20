export type DlType = 'DL1' | 'DL2' | 'DL3' | 'ALL';

export interface DashboardCardResponse {
  success: boolean;
  message: string;
  data: {
    count: number;
  };
}

export interface DashboardCounts {
  dl1: number;
  dl2: number;
  dl3: number;
}

export interface DlMasterResponse {
  success: boolean;
  message: string;
  data: {
    dl_types: string[];
  };
}

export interface DlTrackingPagination {
  count: number;
  current_page: number;
  page_size: number;
  total_pages: number;
  next: string | null;
  previous: string | null;
}

export interface DlTrackingResponse {
  status: boolean;
  message: string;
  pagination: DlTrackingPagination;
  data: DlRecord[];
}

export interface DlHistoryResponse {
  status: boolean;
  message: string;
  pagination: DlTrackingPagination;
  data: DlHistory[];
}

export interface DlRecord {
  ser: number; id: number; sub_department: string; dl_type: string; dart_no: string;
  equip_name: string; defect_no: string; defect_description: string; ship_remarks: string;
  yard_remarks: string; final_prm: string; c_no: string; wi_generation_status: string;
  qc_clearance: string; wi_closing_status: string; wi_generated_by_yard: string;
  dl_importance: string; weekly_status: string; current_status_updated_on: string; status: string;
  critical?: string; er_date_by_yard?: string; start_work_by_yard?: string;
  complete_work_by_yard?: string; dl_work?: number | string | null;
}

export interface DlTrackingUpdatePayload {
  id: number;
  yard_remarks: string;
  final_prm: string;
  c_no: string;
  wi_generation_status: string;
  qc_clearance: string;
  wi_closing_status: string;
  wi_generated_by_yard: string;
  dl_importance: string;
  weekly_status: string;
  status: string;
}

export interface DlHistory extends Partial<DlRecord> {
  er_date_by_yard?: string; start_work_by_yard?: string; complete_work_by_yard?: string;
  dl_work?: number | string | null; critical?: string;
}

export interface ApiResponse<T = unknown> { status?: string; message: string; data?: T; current_status_updated_on?: string; }
