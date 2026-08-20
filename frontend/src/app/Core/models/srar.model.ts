export interface SrarLookupRecord {
  id?: number;
  name: string;
}

export interface SrarRecord {
  id: string | number;
  srarNo?: string;
  shipName?: string;
  month?: number | string;
  month_name?: string;
  year?: number;
  submissionDate?: string;
  approvalStatus?: "Approved" | "Pending" | "In Review" | "Draft" | "Submitted" | (string & {});
  status?: string;
  engineerOfficer?: string;
  cmms_sync_status?: boolean;
  cmmsSyncStatus?: boolean;
  can_edit?: boolean;
  can_export?: boolean;
  can_preview?: boolean;
  is_saved?: boolean;
  send_to_co?: boolean;
  hoursUnderway?: string;
  distanceRun?: number;
  fuelConsumed?: number;
}


export interface SrarRunningParameters {
  duringMonthHours?: string;
  duringMonthMinutes?: string;
  duringMonthDistance?: string;
  maxSpeedDuringMonth?: string;
  maxShaftRpm?: string;
  maxSpeedDate?: string;
  maxSpeedDurationHours?: string;
  maxSpeedDurationMinutes?: string;
}

export interface SrarFuelConsumption {
  bfLastMonth?: string;
  received?: string;
  consHarbor?: string;
  consAnchorage?: string;
  consSea?: string;
  totalCons?: string;
  defueled?: string;
  balLeftOnboard?: string;
}

export interface SrarAvcatStatus {
  bfLastMonth?: string;
  received?: string;
  givenToAc?: string;
  usedForTrials?: string;
  totalCons?: string;
  defueled?: string;
  balLeftOnboard?: string;
}

export interface SrarEefData {
  hoursUnderway?: string;
  eefFactor?: string;
  shipRemarks?: string;
}

export interface SrarReportDetail {
  id?: string | number;
  srarNo?: string;
  shipName?: string;
  month?: string;
  year?: number;
  submissionDate?: string;
  approvalStatus?: string;
  engineerOfficer?: string;
  runningParameters?: SrarRunningParameters;
  fuelConsumption?: SrarFuelConsumption;
  avcatStatus?: SrarAvcatStatus;
  eefData?: SrarEefData;
  [key: string]: unknown;
}

export interface SrarApplicationStatus {
  draft?: number;
  pending_co_review?: number;
  co_approved?: number;
  synced?: number;
  total?: number;
}

export interface SrarAnalyticsKpis {
  past_6_months_count?: number | string;
  active_status_count?: number | string;
  pending_drafts_count?: number | string;
  application_status?: SrarApplicationStatus;
  editable_srar_count?: number | string;
  history_logs_count?: number | string;
  [key: string]: unknown;
}

export interface SrarAnalyticsMonthlyTrendItem {
  month: string;
  month_num?: number;
  year?: number;
  submitted: number;
  draft: number;
  total?: number;
  label?: string;
  value?: number;
  primary?: boolean;
  color?: string;
  [key: string]: unknown;
}

export interface SrarAnalyticsMonthlyTrendResponse {
  trend: SrarAnalyticsMonthlyTrendItem[];
  [key: string]: unknown;
}

export interface SrarLifecycleDistributionItem {
  status: string;
  count: number;
  percentage: number;
  [key: string]: unknown;
}

export interface SrarAnalyticsYearlyStatusItem {
  status?: string;
  count?: number;
  percentage?: number;
  label?: string;
  value?: number;
  color?: string;
  [key: string]: unknown;
}

export interface SrarAnalyticsYearlyStatusResponse {
  year: number;
  total_year_records: number;
  lifecycle_distribution: SrarLifecycleDistributionItem[];
  [key: string]: unknown;
}

export interface SrarAnalyticsDashboardSummary {
  total_reports: number;
  approved_reports: number;
  pending_reports: number;
  draft_reports: number;
  [key: string]: unknown;
}

export interface SrarApiResponse<T = unknown> {
  status?: string;
  message?: string;
  id?: number | string;
  tab?: number;
  data?: T;
  item?: T;
  [key: string]: unknown;
}

// Export endpoint returns either a 202 task hand-off or a 200 synchronous fallback payload
export interface ExportSrarResponse {
  status?: string;
  message?: string;
  task_id?: string;
  task_status_url?: string;
  download_url?: string;
  filename?: string;
  file_path?: string;
  background_fallback?: boolean;
  [key: string]: unknown;
}

export interface SrarCarryForwardInjectorFip {
  sfd_details: number | null;
  eqpt_code: string | null;
  eqpt_name: string | null;
  running_hours_since_installation: string | number | null;
}

export interface SrarCarryForwardGasTurbine {
  sfd_details: number | null;
  eqpt_code: string | null;
  eqpt_name: string | null;
  total_rh_si: number | null;
  rh_regime_1_si: number | null;
  rh_regime_2_si: number | null;
  rh_regime_3_si: number | null;
}

export interface SrarCarryForwardReductionGear {
  sfd_details: number | null;
  eqpt_code: string | null;
  eqpt_name: string | null;
  total_rh_si: string | null;
  total_rh_regime1_si: string | null;
  total_rh_regime2_si: string | null;
  total_rh_regime3_si: string | null;
}

export interface SrarCarryForward {
  fuel_balance_last_month: number | string;
  avcat_balance_last_month: number | string;
  injector_fip: SrarCarryForwardInjectorFip[];
  gas_turbine: SrarCarryForwardGasTurbine[];
  reduction_gear: SrarCarryForwardReductionGear[];
}

export interface SrarMasterItem {
  id: string;
  srarTab: string;
  nomenclature: string;
}

export interface EquipmentValidityItem {
  id: string;
  equipmentName: string;
  source: string;
  lastCalibrationDate: string;
  validityMonths: number;
  nextCalibrationDue: string;
}

export interface RunningUpdateItem {
  id: string;
  updateTitle: string;
  validTill: string;
  createdDate: string;
}

export interface ShipDetailItem {
  id: string;
  shipName: string;
  shipType: string;
  commissionDate: string;
}

export interface SectionEquipment {
  id: string;
  section: string;
  nomenclature: string;
}

export interface SrarReportHeader {
  id?: number;
  srar_month?: number;
  srar_year?: number;
  hours_underway_month_hr?: number;
  hours_underway_month_min?: number;
  distance_run_month?: string;
  max_speed?: number;
  max_speed_date?: string;
  max_shaft_rpm?: number;
  eo_name?: string;
  eo_rank?: string;
  eo_personal_no?: string;
  eo_writer_contact_no?: string;
  eo_contact_no?: string;
  cmms_sync_status?: boolean;
}

export interface SrarReportExploitationItem {
  id: number;
  hrs_for_month_hrs?: number;
  hrs_for_month_min?: number;
  rhsi_till_current_month?: number;
}

export interface SrarReportBoilerItem {
  id: number;
  name?: string;
  serial_no?: string;
  hrs_steamed_in_month?: string;
  hrs_steamed_since_commissioning?: string;
  hrs_above_20_percent?: string;
}

export interface SrarReportActivityItem {
  id: number;
  from_date?: string;
  to_date?: string;
  ship_state?: string;
  ship_location?: string;
  ship_activity_type?: string;
  ship_activity_detail?: string;
  remarks?: string;
}

export interface SrarReportFuelItem {
  id: number;
  b_f_from_last_month?: number;
  recieved?: number;
  consumed_in_harbour?: number;
  consumed_at_sea?: number;
  total_consumed?: number;
  balance_left_on_board?: number;
}

export interface SrarReportIccpItem {
  id: number;
  nomenclature?: string;
  loc_on_board?: string;
  ops_or_non_ops?: string;
}

export interface SrarReportTestKitItem {
  id: number;
  description?: string;
  next_calibration_due_date?: string;
}

export interface SrarReportSdcItem {
  id: number;
  eqpt_name?: string;
  loc_on_board?: string;
  date_of_sdc?: string;
  last_sfc_trial_date?: string;
}

export interface SrarReportDgufItem {
  id: number;
  da_number?: string;
  rh_at_sea_and_anchorage?: string;
  rh_at_port?: string;
  total_rh_in_month?: string;
}

export interface SrarReportLubricantItem {
  id: number;
  name?: string;
  quantity?: number;
  unit?: string;
}

export interface SrarReportEef {
  id?: number;
  designed?: number;
  reason_for_exceeding?: string;
  ship_remarks?: string;
}

export interface SrarFullReportPayload {
  header?: SrarReportHeader;
  tab_1_equipment_exploitations?: SrarReportExploitationItem[];
  tab_2_boiler_data?: SrarReportBoilerItem[];
  tab_3_ship_activities?: SrarReportActivityItem[];
  tab_4_fuel_consumptions?: SrarReportFuelItem[];
  tab_5_iccp?: SrarReportIccpItem[];
  tab_6_test_kits?: SrarReportTestKitItem[];
  tab_7_safety_device_checks?: SrarReportSdcItem[];
  tab_8_dguf?: SrarReportDgufItem[];
  tab_12_lubricants?: SrarReportLubricantItem[];
  tab_14_eef?: SrarReportEef;
}
