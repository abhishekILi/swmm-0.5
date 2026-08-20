export type HierarchyNodeType =
  | "co"
  | "hod"
  | "divisional_officer"
  | "division"
  | "sailor";

export interface HierarchyNode {
  id: string;
  dbId: number | null;
  type: HierarchyNodeType;
  name: string;
  rank: string;
  designation: string;
  personalNumber: string;
  photoUrl: string | null;
  divisionName: string;
  isRegulator: boolean;
  selectedUserId: number | null;
  collapsed: boolean;
  children: HierarchyNode[];
}

export interface AvailableUser {
  id: number;
  name: string;
  rank: string;
  designation: string;
  personal_number: string;
  photo: string;
}

export const NODE_LABELS: Record<HierarchyNodeType, string> = {
  co: "CO",
  hod: "HOD",
  divisional_officer: "Divisional Officer",
  division: "Division",
  sailor: "Sailor",
};

export const NODE_COLORS: Record<HierarchyNodeType, string> = {
  co: "#3b93b6",
  hod: "#c37575",
  divisional_officer: "#af7442",
  division: "#7289d0",
  sailor: "#8f61ad",
};

export const CHILD_TYPE: Partial<Record<HierarchyNodeType, HierarchyNodeType>> = {
  co: "hod",
  hod: "divisional_officer",
  divisional_officer: "division",
};

export interface RawHierarchyNode {
  dbId: number;
  type: HierarchyNodeType;
  name: string;
  rank?: string;
  designation?: string;
  personalNumber?: string;
  photoUrl?: string | null;
  divisionName?: string;
  isRegulator?: boolean;
  selectedUserId?: number | null;
  children?: RawHierarchyNode[];
}

export interface HierarchyTreeResponse {
  status: string;
  hierarchy: RawHierarchyNode | null;
}

export interface AvailableUsersResponse {
  status: string;
  users: AvailableUser[];
}
