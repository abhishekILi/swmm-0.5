export interface CloseDefectResponse {
  status: string;
  message: string;
  data: CloseDefectData;
}

export interface CloseDefectData {
  defect: Defect;
  issued_spare_obj: IssuedSpare[];
  repair_agency_list: RepairAgencyOption[];
  diagnostic_list: DiagnosticOption[];
  repair_list: RepairOption[];
  delay_list: DelayOption[];
}

export interface Defect {
  id: number;
  dart_number: string;
  equipment_name: string;
  nomenclature: string;
  sub_dept: string;
  defect_date: string;
  defect_closing_date: string;
  scheduled_date: string;
  defective_discriptions: string;
}

export interface RepairAgencyOption {
  id: number;
  repair_agency_code: string;
  repair_agency_name: string;
}

export interface DiagnosticOption {
  id: number;
  diagnostic_code: string;
  diagnostic_name: string;
}

export interface RepairOption {
  id: number;
  repair_code: string;
  repair_name: string;
}

export interface DelayOption {
  id: number;
  delay_code: string;
  delay_name: string;
}

export interface IssuedSpare {
  spare_pattern_number: string;
  spare_description: string;
  quantity_issued: number;
  date_of_issue: string;
}
