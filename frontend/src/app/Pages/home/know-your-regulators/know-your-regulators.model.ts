export interface RegulatorSummary {
  id: number;
  name: string;
  rank: string | null;
  designation: string;
  assignedCount: number;
}

export interface DepartmentRegulators {
  id: number;
  dep_name?: string;
  name?: string;
  regulators: RegulatorSummary[];
  expanded?: boolean;
}

export interface RegulatorsTreeResponse {
  status: string;
  departments: DepartmentRegulators[];
}

export interface RegulatorSailor {
  id: number;
  name: string;
  rank: string;
  designation: string;
  personalNumber: string;
}

export interface RegulatorSailorsResponse {
  status: string;
  regulator: { id: number; name: string };
  assigned: RegulatorSailor[];
  unassigned: RegulatorSailor[];
}
