export interface SFDDashboardResponse {
  hierarchy: HierarchyData;
  configuration_validation: ConfigurationValidation;
  active_change_and_deviations: ActiveChangeAndDeviations;
  baseline_vs_current_comparison: BaselineVsCurrentComparisons;
  movement_and_configuration_history: MovementAndConfigurationHistory;
  contextual_search_and_drill_down: ContextualSearchAndDrillDown;
}

export interface HierarchyData {
  heading: string;
  view_all: boolean;
  tree: HierarchyNode[];
}

export interface HierarchyNode {
  id: number;
  name: string;
  type: string;
  children: HierarchyNode[];
}

export interface ConfigurationValidation {
  heading: string;
  view_all: boolean;
  items: ConfigurationValidationItem[];
}

export interface ConfigurationValidationItem {
  name: string;
  count: number;
}

export interface ActiveChangeAndDeviations {
  view_all: boolean;
  heading: string;
  items: ActiveChangeItem[];
}

export interface ActiveChangeItem {
  id: number;
  title: string;
  count: number;
  status: string;
}

export interface BaselineVsCurrentComparisons {
  view_all: boolean;
  heading: string;
  filters: string[];
  selected_filter: string;
  records: BaselineRecord[];
  summary: BaselineSummary;
}

export interface BaselineRecord {
  equipment: string;
  from_location: string;
  to_location: string;
  status: string;
}

export interface BaselineSummary {
  total_changes: number;
  relocations: number;
  replacements: number;
  removed: number;
  temporary_fitments: number;
}

export interface MovementAndConfigurationHistory {
  heading: string;
  view_all_flag: boolean;
  movement_and_configuration_histories: MovementHistoryItem[];
}

export interface MovementHistoryItem {
  date: string;
  event_type: string;
  title: string;
  description: string;
}

export interface ContextualSearchAndDrillDown {
  filters: string[];
  view_all: boolean;
  heading: string;
  selected_filter: string;
  search_text: string;
  results: SearchResult[];
  selected_item: SelectedItem;
}

export interface SearchResult {
  equipment: string;
  location: string;
  status: string;
}

export interface SelectedItem {
  equipment_name: string;
  equipment_status: string;
  location: string;
  system: string;
  status: string;
  equipment_id: number | null;
  compartment: string;
  last_updated: string | null;
}
export interface KpiPeriodData {
  count: number;
  trend: {
    period: string;
    percentage: number;
    direction: string;
    current_count: number;
    previous_count: number;
  };
}

export interface KpiItem {
  key: string;
  title: string;

  "6m": KpiPeriodData;
  "1y": KpiPeriodData;
  "2y": KpiPeriodData;

  count: number;
  trend: {
    period: string;
    percentage: number;
    direction: string;
    current_count: number;
    previous_count: number;
  };
}

export interface KpiResponse {
  kpis: KpiItem[];
  periods: string[];
  default_period: string;
}
