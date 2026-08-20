export interface DepartmentAffected {
  id: number;
  name: string;
}

export interface DepartmentOption {
  id: number;
  name: string;
}

export interface TagoutHistoryDataItem {
  id: number;
  date?: string;
  ship_name?: string;
  department_name?: string;
  departments_affected?: (DepartmentAffected | number)[];
  active?: number;
  tagout_number?: string;
  tag_no?: string;
  equipment?: string;
  name_of_component?: string;
  name_of_subsystem?: string;
  approval_status?: string;
  status?: string;
}

export interface TagoutHistoryFilters {
  from_date: string;
  to_date: string;
  department: string;
}

export interface TagoutHistoryResponse {
  status: string;
  data: TagoutHistoryDataItem[];
  departments: DepartmentOption[];
  filters: TagoutHistoryFilters;
  is_dyhod: boolean;
}
