export interface EmsThumbnailResponse {
  data: {
    count: number;
    rh_due_count: number;
    cal_due_count: number;
    fuss_due_count: number;
    aber_due_count: number;
  };
}

export interface EmsSectionsResponse {
  section_name: Record<string, number>;
}

export interface SectionRhsiBarchartResponse {
  equipment_ids: number[];
  section: string;
  labels: string[];
  values: number[];
  formatted_values: string[];
  tooltips: string[];
  colors: string[];
}

export type EmsEquipmentLocation = 'AT HARBOUR' | 'AT SEA' | 'AT ANCHORAGE';

export interface UpdateEquipmentStatePayload {
  equipment_id: number;
  state: 'ACTIVE' | 'INACTIVE';
  started_at_location?: EmsEquipmentLocation;
  start_timedate?: string | null;
  stop_timedate?: string | null;
}

export interface MonthlyRunningHoursRow {
  start: string;
  stop: string;
  location: EmsEquipmentLocation | '';
}

export interface SaveMonthlyRunningHoursPayload {
  equipment_id: number;
  rows: MonthlyRunningHoursRow[];
}

export interface EquipmentHistoryItem {
  month: string;
  start: string;
  stop: string;
  duration: string;
  location: string;
}

export interface EquipmentHistoryResponse {
  history: EquipmentHistoryItem[];
}
