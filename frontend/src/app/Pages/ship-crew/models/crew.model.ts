export type PersonnelStatus = "Present" | "On Leave" | "Ty Duty";

export interface CrewPersonnel {
  id: number;
  pno: string;
  rank: string;
  firstName: string;
  lastName: string;
  department: string;
  designation?: string;
  status: PersonnelStatus;
  dateOfJoining?: string;
}

export interface CrewDashboardCounts {
  total: number;
  present: number;
  onLeave: number;
  tyDuty: number;
}

export interface DeptStrength {
  department: string;
  total: number;
  present: number;
}

export interface WatchbillDashboardCounts {
  total: number;
  present: number;
  absent: number;
}

export interface WatchbillDashboardData {
  counts: WatchbillDashboardCounts;
  deptStrength: DeptStrength[];
  activeSailingsCount: number;
  completedSailingsCount: number;
}

export type LeaveType = "On Leave" | "Ty Duty";
export type ApplicationStatus = "Pending" | "Approved" | "Rejected";

/** Payload for `leave-applications/apply_on_behalf/` — an HOD/DY-HOD/CO applying leave or TY
 * duty for a selected member of their department. Auto-approved server-side. */
export interface ApplyOnBehalfPayload {
  personalNumber: string;
  leaveType: LeaveType;
  hasPrefix: boolean;
  prefixStartDate?: string;
  startDate: string;
  endDate: string;
  hasSuffix: boolean;
  suffixCompletionDate?: string;
  reportingDate?: string;
  station?: string;
  reason?: string;
  attachment?: File | null;
}

export interface LeaveApplication {
  id: number;
  personalNumber: string;
  name: string;
  rank: string;
  department?: string;
  leaveType: LeaveType;
  hasPrefix: boolean;
  prefixStartDate?: string;
  startDate: string;
  endDate: string;
  hasSuffix: boolean;
  suffixCompletionDate?: string;
  reportingDate?: string;
  noOfDays: number;
  station?: string;
  reason?: string;
  applicationStatus: ApplicationStatus;
  rejectionReason?: string;
  appliedAt: string;
}

export type PersonType = "civilian" | "officer" | "fleet_officer" | "fleet_staff" | "fleet_commander" | "sailor";

export interface Civilian {
  id: number;
  name: string;
  role: string;
  personType: PersonType;
  desig?: string;
  rank?: string;
  serviceNo?: string;
  fleet?: string;
  ship?: string;
  refId?: string;
  contact?: string;
  remarks?: string;
}

export interface RankOption {
  id: number;
  name: string;
}

export type SailorClass = "Junior" | "Senior";

export interface RankClassification {
  id: number;
  rankName: string;
  classification: SailorClass;
}

export type SailingStatus = "active" | "completed";

export interface SailingSummary {
  id: number;
  name: string;
  area?: string;
  start: string;
  co?: string;
  status: SailingStatus;
  completedAt?: string;
  personnelCount: number;
  civilianCount: number;
}

export interface SailingAssignmentRow {
  /** The `SailingPersonnel` row's own id — required to PATCH/DELETE
   * `sailings/personnel/{id}/` (removal is keyed by this, not by `pno`). */
  id: number;
  pno: string;
  name: string;
  rank: string;
  dept: string;
  w3?: string;
  w2?: string;
  action?: string;
  defence?: string;
  cruising?: string;
  shelter?: string;
  emergency?: string;
  lifeRaft?: string;
  mess?: string;
  bloodGroup?: string;
  ssd?: string;
  messStn?: string;
  section?: string;
  remarks?: string;
}

export interface SailingDetail extends SailingSummary {
  departments: Record<string, SailingAssignmentRow[]>;
}

export type MasterType = "action" | "defence" | "cruising" | "shelter" | "emergency";

export interface MasterEntry {
  id: number;
  name: string;
}
