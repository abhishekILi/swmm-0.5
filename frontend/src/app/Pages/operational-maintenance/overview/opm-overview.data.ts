import { BarDatum, LegendItem, LineSeries } from "../../../shared/components";
import { DonutSegment } from "../../../shared/components/donut-chart/donut-chart";
import { OpmActivityRow, OpmAlert, OpmDeptDatum, OpmDeptLoad, OpmOverviewKpi, OpmQuickAction } from "./opm-overview.model";

/** Lucide icon names for the Overview panel headers (reused by the component). */
export const OPM_OVERVIEW_PANEL_ICONS = {
  alerts: "triangle-alert",
  quickActions: "zap",
  deptBar: "chart-column",
  trend: "chart-line",
  activity: "upload",
  severity: "chart-pie",
  deptLoad: "chart-bar",
} as const;

/** All Overview KPIs (customizable set). Icon colour/background are design-fixed. */
export const OPM_OVERVIEW_KPIS: OpmOverviewKpi[] = [
  {
    key: "opdef",
    title: "OPDEF / OPDEF (STA) Count",
    count: 9,
    displayValue: "9",
    iconColor: "#F82C36",
    iconBg: "rgba(248,44,54,0.16)",
    iconName: "triangle-alert",
    trendUp: false,
    baseUp: false,
    selectedPeriod: "all",
    trendData: { all: "+2", "6m": "+1", "1y": "+3", "2y": "+5" },
    valueData: { all: "9", "6m": "6", "1y": "14", "2y": "22" },
    drawerSubtitle: "operational defects with readiness impact",
    sectionTitle: "OPDEF breakdown by class",
    sectionHint: "Count · Share",
    stats: [
      { value: "5", label: "OPDEF" },
      { value: "4", label: "OPDEF (STA)" },
      { value: "3", label: "> 7 days" },
    ],
    mode: "breakdown",
    breakdown: [
      { name: "OPDEF", pct: 100, metrics: [{ label: "Count", value: "5" }, { label: "Share", value: "56%" }] },
      { name: "OPDEF (STA)", pct: 80, metrics: [{ label: "Count", value: "4" }, { label: "Share", value: "44%" }] },
    ],
  },
  {
    key: "ra-fmu-yard",
    title: "RAs With FMU / With Yard",
    count: 11,
    displayValue: "11",
    iconColor: "#4AA8FF",
    iconBg: "rgba(0,136,255,0.16)",
    iconName: "house",
    trendUp: false,
    baseUp: false,
    selectedPeriod: "all",
    trendData: { all: "+1", "6m": "+2", "1y": "+4", "2y": "+7" },
    valueData: { all: "11", "6m": "8", "1y": "19", "2y": "31" },
    drawerSubtitle: "repair assistances in external routing",
    sectionTitle: "RA routing status",
    sectionHint: "Count",
    stats: [
      { value: "7", label: "With FMU" },
      { value: "4", label: "With Yard" },
      { value: "3", label: "SLA breach" },
    ],
    mode: "breakdown",
    breakdown: [
      { name: "With FMU", pct: 100, color: "#4AA8FF", metrics: [{ label: "Count", value: "7" }] },
      { name: "With Yard", pct: 57, color: "#A855F7", metrics: [{ label: "Count", value: "4" }] },
    ],
  },
  {
    key: "guarantee",
    title: "Guarantee Exposure Alerts",
    count: 4,
    displayValue: "4",
    iconColor: "#F82C36",
    iconBg: "rgba(248,44,54,0.16)",
    iconName: "shield-alert",
    trendUp: false,
    baseUp: false,
    selectedPeriod: "all",
    trendData: { all: "+1", "6m": "0", "1y": "+2", "2y": "+3" },
    valueData: { all: "4", "6m": "4", "1y": "6", "2y": "9" },
    drawerSubtitle: "equipment past the 76% exposure threshold",
    sectionTitle: "Equipment at guarantee risk",
    sectionHint: "Exposure",
    stats: [
      { value: "4", label: "Red (>76%)" },
      { value: "6", label: "Amber" },
      { value: "18", label: "Green" },
    ],
    mode: "list",
    listRows: [
      { title: "Diesel Alternator No.1", sub: "Electrical · exposure 82%", meta: "Red", tag: "Critical", tagColor: "#F82C36", dotColor: "#F82C36" },
      { title: "HP Air Compressor", sub: "Marine Eng · exposure 79%", meta: "Red", tag: "Critical", tagColor: "#F82C36", dotColor: "#F82C36" },
      { title: "Sea Viper Director", sub: "Weapon Eng · exposure 77%", meta: "Red", tag: "Critical", tagColor: "#F82C36", dotColor: "#F82C36" },
      { title: "Gyro Compass", sub: "Navigation · exposure 76%", meta: "Red", tag: "Watch", tagColor: "#F59E0B", dotColor: "#F59E0B" },
    ],
  },
  {
    key: "certificates",
    title: "Certificates Issued",
    count: 7,
    displayValue: "7",
    iconColor: "#22C55E",
    iconBg: "rgba(34,197,94,0.16)",
    iconName: "award",
    trendUp: true,
    baseUp: true,
    selectedPeriod: "all",
    trendData: { all: "+2", "6m": "+3", "1y": "+5", "2y": "+9" },
    valueData: { all: "7", "6m": "5", "1y": "12", "2y": "21" },
    drawerSubtitle: "completion certificates issued this period",
    sectionTitle: "Certificates by type",
    sectionHint: "Count",
    stats: [
      { value: "4", label: "Repair" },
      { value: "2", label: "Service" },
      { value: "1", label: "Guarantee" },
    ],
    mode: "breakdown",
    breakdown: [
      { name: "Repair completion", pct: 100, color: "#22C55E", metrics: [{ label: "Count", value: "4" }] },
      { name: "Service completion", pct: 50, color: "#4AA8FF", metrics: [{ label: "Count", value: "2" }] },
      { name: "Guarantee closure", pct: 25, color: "#A855F7", metrics: [{ label: "Count", value: "1" }] },
    ],
  },
];

/** Operational alerts (Alerts panel). Each opens a detail drawer whose rows/action deep-link
 *  into the relevant tab. */
export const OPM_ALERTS: OpmAlert[] = [
  {
    text: "DART-2026-0142 raised — Sea Viper Director (OPDEF)",
    color: "#F82C36",
    tag: "DART",
    severity: "Critical",
    desc: "A Defect / Action Report (DART-2026-0142) has been raised against the Sea Viper Director and classified OPDEF. It requires immediate assessment and routing to the repair authority.",
    details: [
      { label: "DART No.", value: "DART-2026-0142" },
      { label: "Equipment", value: "Sea Viper Director" },
      { label: "Classification", value: "OPDEF" },
    ],
    itemsLabel: "Open DARTs (3)",
    items: [
      "DART-2026-0142 · Sea Viper Director · OPDEF",
      "DART-2026-0139 · Radar Type 997 · Non-OPDEF",
      "DART-2026-0136 · Gas Turbine GT2 · OPDEF",
    ],
    nav: "actions",
    // actionLabel: "View DART",
    actionIcon: "arrow-up-right",
  },
  {
    text: "Repair marked complete — SAT / UNSAT verification required",
    color: "#F59E0B",
    tag: "Verify",
    severity: "Caution",
    desc: "A repair has been marked complete and now awaits SAT / UNSAT verification before the Repair Authority can be closed out.",
    details: [
      { label: "Stage", value: "Verification" },
      { label: "Awaiting", value: "SAT / UNSAT" },
      { label: "Raised", value: "1400 hrs" },
    ],
    itemsLabel: "Awaiting Verification (2)",
    items: [
      "RA-2026-0091 · Fire Main Pump No.3 · SAT/UNSAT pending",
      "RA-2026-0088 · Gyro Compass · SAT/UNSAT pending",
    ],
    nav: "approval",
    // actionLabel: "Verify SAT / UNSAT",
    actionIcon: "square-check-big",
  },
  {
    text: "UNSAT returned for rework — LO Pump ME No.1",
    color: "#F82C36",
    tag: "UNSAT",
    severity: "Critical",
    desc: "The LO Pump (ME No.1) repair was verified UNSAT and has been returned for rework. A fresh repair cycle must be initiated.",
    details: [
      { label: "Equipment", value: "LO Pump ME No.1" },
      { label: "Result", value: "UNSAT" },
      { label: "Action", value: "Rework" },
    ],
    itemsLabel: "Returned for Rework (2)",
    items: ["LO Pump ME No.1 · UNSAT · Rework", "Bilge Pump No.2 · UNSAT · Rework"],
    nav: "actions",
    // actionLabel: "Open Rework",
    actionIcon: "wrench",
  },
  {
    text: "Guarantee exposure 82% — Diesel Alternator (Red)",
    color: "#F82C36",
    tag: "Guarantee",
    severity: "Critical",
    desc: "Guarantee exposure on the Diesel Alternator has reached 82% (Red band). Review the equipment guarantee before further work is authorised.",
    details: [
      { label: "Equipment", value: "Diesel Alternator" },
      { label: "Exposure", value: "82%" },
      { label: "Band", value: "Red" },
    ],
    itemsLabel: "Guarantee Exposure — High (3)",
    items: ["Diesel Alternator · 82% · Red", "Gas Turbine GT1 · 74% · Red", "Steering Gear Ram · 69% · Amber"],
    nav: "guarantee",
    // actionLabel: "Review Guarantee",
    actionIcon: "shield-check",
  },
  {
    text: "RA export to NavYojana failed — offline file generated",
    color: "#F59E0B",
    tag: "Export",
    severity: "Caution",
    desc: "The Repair Authority export to NavYojana did not complete. An offline file has been generated as a fallback; a retry is required to sync with the shore system.",
    details: [
      { label: "Target", value: "NavYojana" },
      { label: "Status", value: "Failed" },
      { label: "Fallback", value: "Offline file" },
    ],
    itemsLabel: "Failed Exports (2)",
    items: ["RA-2026-0090 · NavYojana · Failed 0630 hrs", "RA-2026-0087 · NavYojana · Failed 0630 hrs"],
    nav: "reports",
    // actionLabel: "Retry Export",
    actionIcon: "refresh-cw",
  },
];

/** Quick actions (Quick Actions panel) — each deep-links to a module tab. "Add Defect / DART"
 *  is rendered as the dropdown primary (Reason → Add form); the rest are plain buttons. */
export const OPM_QUICK_ACTIONS: OpmQuickAction[] = [
  { label: "Add Defect / DART", icon: "plus", tab: "actions" },
  { label: "View Approval / RA Status", icon: "square-check-big", tab: "actions", queryParams: { view: "approval" } },
  { label: "Add / Extend Guarantee", icon: "shield-check", tab: "actions", queryParams: { view: "guarantee" } },
];

/** Open DARTs by department (bar chart top level). */
export const OPM_DEPT: OpmDeptDatum[] = [
  { label: "Marine Eng", short: "Marine", value: 14 },
  { label: "Weapon Eng", short: "Weapon", value: 9 },
  { label: "Electrical", short: "Elec", value: 7 },
  { label: "Navigation", short: "Nav", value: 5 },
  { label: "Logistics", short: "Logistics", value: 3 },
];

/** Sub-department drill-down for the bar chart (keyed by department label). */
export const OPM_DEPT_SUBS: Record<string, OpmDeptDatum[]> = {
  "Marine Eng": [
    { label: "Propulsion", short: "Propulsion", value: 6 },
    { label: "Auxiliary", short: "Auxiliary", value: 5 },
    { label: "Steering", short: "Steering", value: 3 },
  ],
  "Weapon Eng": [
    { label: "Missiles", short: "Missiles", value: 4 },
    { label: "Guns", short: "Guns", value: 3 },
    { label: "Fire Control", short: "Fire Ctrl", value: 2 },
  ],
  Electrical: [
    { label: "Power Gen", short: "Power", value: 4 },
    { label: "Distribution", short: "Dist", value: 3 },
  ],
};

/** DART lifecycle trend — 3-series line chart. */
export const OPM_TREND_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"];
export const OPM_TREND_SERIES: LineSeries[] = [
  { label: "Raised", color: "#F82C36", values: [12, 15, 11, 17, 14, 13], area: false },
  { label: "Closed", color: "#22C55E", values: [9, 11, 13, 12, 16, 15], area: false },
  { label: "Reopened", color: "#F59E0B", values: [2, 3, 4, 3, 2, 3], area: false },
];
export const OPM_TREND_LEGEND: LegendItem[] = [
  { label: "Raised", color: "#F82C36" },
  { label: "Closed", color: "#22C55E" },
  { label: "Reopened", color: "#F59E0B" },
];

/** Recent DART / RA activity (d = days ago). */
export const OPM_ACTIVITY: OpmActivityRow[] = [
  { d: 0, date: "26 Jun", equip: "LO Pump - ME No.1", action: "Raised", dept: "Marine Eng", ship: "OPDEF", status: "In Progress" },
  { d: 1, date: "25 Jun", equip: "Gyro Compass", action: "Closed", dept: "Navigation", ship: "Normal Defect", status: "Verified" },
  { d: 3, date: "23 Jun", equip: "Painting — Hull (Service)", action: "Raised", dept: "Logistics", ship: "Service", status: "In Progress" },
  { d: 6, date: "22 Jun", equip: "Sea Viper Director", action: "Raised", dept: "Weapon Eng", ship: "OPDEF (STA)", status: "In Progress" },
  { d: 9, date: "19 Jun", equip: "Fire Main Pump", action: "Closed", dept: "Marine Eng", ship: "Normal Defect", status: "Verified" },
  { d: 12, date: "16 Jun", equip: "440V Switchboard", action: "Closed", dept: "Electrical", ship: "Normal Defect", status: "Verified" },
  { d: 15, date: "13 Jun", equip: "Diesel Alternator", action: "Raised", dept: "Electrical", ship: "OPDEF", status: "In Progress" },
  { d: 18, date: "10 Jun", equip: "CIWS Mount", action: "Closed", dept: "Weapon Eng", ship: "Normal Defect", status: "Verified" },
  { d: 26, date: "02 Jun", equip: "Steering Gear", action: "Closed", dept: "Marine Eng", ship: "Normal Defect", status: "Verified" },
  { d: 40, date: "20 May", equip: "Sonar Transducer", action: "Raised", dept: "Navigation", ship: "OPDEF (STA)", status: "In Progress" },
  { d: 63, date: "26 Apr", equip: "HP Air Compressor", action: "Closed", dept: "Marine Eng", ship: "Normal Defect", status: "Verified" },
  { d: 108, date: "12 Mar", equip: "Crane — Dockyard (Service)", action: "Closed", dept: "Logistics", ship: "Service", status: "Verified" },
  { d: 150, date: "30 Jan", equip: "Fire Detection Panel", action: "Closed", dept: "Marine Eng", ship: "Normal Defect", status: "Verified" },
];

/** Open DARTs grouped by operational severity (donut). */
export const OPM_SEVERITY: DonutSegment[] = [
  { label: "OPDEF", value: 5, color: "#F82C36" },
  { label: "OPDEF (STA)", value: 4, color: "#F59E0B" },
  { label: "Normal Defect", value: 29, color: "#4AA8FF" },
];
export const OPM_SEVERITY_TOTAL = OPM_SEVERITY.reduce((sum, s) => sum + s.value, 0);

/** Open DARTs aggregated across ship departments (horizontal bars). */
export const OPM_DEPT_LOAD: OpmDeptLoad[] = [
  { label: "Marine Engineering", value: 14 },
  { label: "Weapon Engineering", value: 9 },
  { label: "Electrical", value: 7 },
  { label: "Navigation", value: 5 },
];

/** Bar chart helper — mark the tallest bar as primary (accent colour). */
export function toBarData(rows: OpmDeptDatum[]): BarDatum[] {
  const max = Math.max(0, ...rows.map((r) => r.value));
  return rows.map((r) => ({ label: r.short, value: r.value, primary: r.value === max }));
}
