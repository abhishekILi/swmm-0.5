/** A column in a report grid. */
export interface OpmReportColumn {
  field: string;
  label: string;
  chip?: boolean;
  /** Holds a `dd MMM yyyy` date — drives the report's Date Range filter. */
  date?: boolean;
}

/** A single report definition + its dummy rows. */
export interface OpmReport {
  id: string;
  name: string;
  purpose: string;
  /** Lucide icon name for the report-nav entry. */
  icon: string;
  columns: OpmReportColumn[];
  rows: Record<string, string | number>[];
}

/** Shared status-chip tone map covering every chip value used across reports. */
export const OPM_REPORT_TONE_MAP: Record<string, string> = {
  Critical: "danger",
  Major: "warning",
  Minor: "neutral",
  Open: "info",
  "In Progress": "warning",
  Closed: "success",
  Returned: "danger",
  Pending: "info",
  Approved: "success",
  "With FMU": "warning",
  "With Yard": "warning",
  Red: "danger",
  Amber: "warning",
  Green: "success",
  Success: "success",
  Failed: "danger",
};

export const OPM_REPORTS: OpmReport[] = [
  {
    id: "r1",
    name: "Open DART Register",
    purpose: "Track active defects and raised assistance across the ship.",
    icon: "file-text",
    columns: [
      { field: "dart", label: "DART No." },
      { field: "equip", label: "Equipment" },
      { field: "reason", label: "Reason" },
      { field: "severity", label: "Severity", chip: true },
      { field: "status", label: "Status", chip: true },
      { field: "date", label: "Raised On", date: true },
      { field: "days", label: "Days Open" },
    ],
    rows: [
      { dart: "DART-2026-0142", equip: "Sea Viper Director", reason: "OPDEF (STA)", severity: "Critical", status: "Open", date: "26 Jun 2026", days: 1 },
      { dart: "DART-2026-0141", equip: "LO Pump - ME No.1", reason: "OPDEF", severity: "Critical", status: "In Progress", date: "26 Jun 2026", days: 1 },
      { dart: "DART-2026-0138", equip: "Diesel Alternator", reason: "OPDEF", severity: "Major", status: "In Progress", date: "24 Jun 2026", days: 3 },
      { dart: "DART-2026-0119", equip: "Painting — Hull", reason: "Services", severity: "Minor", status: "Open", date: "17 Jun 2026", days: 10 },
      { dart: "DART-2026-0111", equip: "Sonar Transducer", reason: "OPDEF (STA)", severity: "Critical", status: "In Progress", date: "13 Jun 2026", days: 14 },
    ],
  },
  {
    id: "r2",
    name: "Closed Defect History",
    purpose: "Review completed defects, including onboard rectifications.",
    icon: "circle-check-big",
    columns: [
      { field: "dart", label: "DART No." },
      { field: "equip", label: "Equipment" },
      { field: "reason", label: "Reason" },
      { field: "rectified", label: "Rectified" },
      { field: "closed", label: "Closed On", date: true },
      { field: "cert", label: "Cert No." },
    ],
    rows: [
      { dart: "DART-2026-0135", equip: "Gyro Compass", reason: "Normal Defect", rectified: "Yes", closed: "24 Jun 2026", cert: "CERT-0091" },
      { dart: "DART-2026-0131", equip: "Fire Main Pump", reason: "Normal Defect", rectified: "Yes", closed: "23 Jun 2026", cert: "CERT-0090" },
      { dart: "DART-2026-0128", equip: "440V Switchboard", reason: "Normal Defect", rectified: "Yes", closed: "21 Jun 2026", cert: "CERT-0089" },
      { dart: "DART-2026-0115", equip: "Steering Gear", reason: "Normal Defect", rectified: "Yes", closed: "16 Jun 2026", cert: "CERT-0087" },
    ],
  },
  {
    id: "r3",
    name: "Service Required Register",
    purpose: "Track service requests raised under Reason = Services.",
    icon: "wrench",
    columns: [
      { field: "ref", label: "Ref" },
      { field: "service", label: "Service" },
      { field: "dept", label: "Department" },
      { field: "date", label: "Raised On", date: true },
      { field: "status", label: "Status", chip: true },
    ],
    rows: [
      { ref: "SVC-2026-021", service: "Hull Painting", dept: "Logistics", date: "23 Jun 2026", status: "In Progress" },
      { ref: "SVC-2026-018", service: "Dockyard Crane", dept: "Logistics", date: "12 Mar 2026", status: "Closed" },
      { ref: "SVC-2026-016", service: "Tank Cleaning", dept: "Marine Eng", date: "02 Jun 2026", status: "Closed" },
    ],
  },
  {
    id: "r4",
    name: "Guarantee Monitoring",
    purpose: "Track guarantee exposure per equipment guarantee window.",
    icon: "shield-alert",
    columns: [
      { field: "equip", label: "Equipment" },
      { field: "supplier", label: "Supplier" },
      { field: "exposure", label: "Exposure %" },
      { field: "expiry", label: "Guarantee Expiry", date: true },
      { field: "risk", label: "Risk", chip: true },
    ],
    rows: [
      { equip: "Diesel Alternator No.1", supplier: "BHEL", exposure: "82%", expiry: "12 Aug 2026", risk: "Red" },
      { equip: "HP Air Compressor", supplier: "Kirloskar", exposure: "79%", expiry: "30 Aug 2026", risk: "Red" },
      { equip: "Sea Viper Director", supplier: "MBDA", exposure: "77%", expiry: "18 Sep 2026", risk: "Red" },
      { equip: "Gyro Compass", supplier: "Raytheon", exposure: "64%", expiry: "05 Dec 2026", risk: "Amber" },
      { equip: "Steering Gear", supplier: "Rolls-Royce", exposure: "41%", expiry: "22 Mar 2027", risk: "Green" },
    ],
  },
  {
    id: "r5",
    name: "Spares Consumption",
    purpose: "Track spare usage by defect and equipment.",
    icon: "package",
    columns: [
      { field: "spare", label: "Spare" },
      { field: "equip", label: "Equipment" },
      { field: "qty", label: "Qty Used" },
      { field: "dart", label: "DART No." },
      { field: "date", label: "Date", date: true },
    ],
    rows: [
      { spare: "Impeller Assy", equip: "LO Pump - ME No.1", qty: 1, dart: "DART-2026-0141", date: "26 Jun 2026" },
      { spare: "Carbon Brush Set", equip: "Diesel Alternator", qty: 4, dart: "DART-2026-0138", date: "24 Jun 2026" },
      { spare: "Gasket Kit", equip: "Fire Main Pump", qty: 2, dart: "DART-2026-0131", date: "22 Jun 2026" },
    ],
  },
  {
    id: "r6",
    name: "RA Status Register",
    purpose: "Track RA progress by type and routing status.",
    icon: "send",
    columns: [
      { field: "ra", label: "RA No." },
      { field: "type", label: "Type" },
      { field: "equip", label: "Equipment" },
      { field: "routing", label: "Routing", chip: true },
      { field: "submitted", label: "Submitted", date: true },
      { field: "authority", label: "Authority" },
    ],
    rows: [
      { ra: "RA-2026-0051", type: "OP RA", equip: "Sea Viper Director", routing: "With FMU", submitted: "26 Jun 2026", authority: "FMU Mumbai" },
      { ra: "RA-2026-0047", type: "Guarantee RA", equip: "Diesel Alternator", routing: "With Yard", submitted: "24 Jun 2026", authority: "Naval Dockyard" },
      { ra: "RA-2026-0044", type: "Yard RA", equip: "HP Air Compressor", routing: "Approved", submitted: "22 Jun 2026", authority: "FMU Mumbai" },
    ],
  },
  {
    id: "r7",
    name: "DARTs Under Each RA",
    purpose: "Drill down from an RA to its constituent DARTs.",
    icon: "list-tree",
    columns: [
      { field: "ra", label: "RA No." },
      { field: "dart", label: "DART No." },
      { field: "equip", label: "Equipment" },
      { field: "severity", label: "Severity", chip: true },
      { field: "status", label: "Status", chip: true },
    ],
    rows: [
      { ra: "RA-2026-0051", dart: "DART-2026-0142", equip: "Sea Viper Director", severity: "Critical", status: "Open" },
      { ra: "RA-2026-0049", dart: "DART-2026-0141", equip: "LO Pump - ME No.1", severity: "Critical", status: "In Progress" },
      { ra: "RA-2026-0047", dart: "DART-2026-0138", equip: "Diesel Alternator", severity: "Major", status: "In Progress" },
    ],
  },
  {
    id: "r8",
    name: "NavYojana Export Status",
    purpose: "Track export outcomes for raised RAs.",
    icon: "cloud-upload",
    columns: [
      { field: "ra", label: "RA No." },
      { field: "exported", label: "Exported On", date: true },
      { field: "channel", label: "Channel" },
      { field: "result", label: "Result", chip: true },
      { field: "retries", label: "Retries" },
    ],
    rows: [
      { ra: "RA-2026-0051", exported: "26 Jun 2026", channel: "NavYojana API", result: "Success", retries: 0 },
      { ra: "RA-2026-0049", exported: "26 Jun 2026", channel: "Offline File", result: "Failed", retries: 2 },
      { ra: "RA-2026-0047", exported: "24 Jun 2026", channel: "NavYojana API", result: "Success", retries: 0 },
    ],
  },
];
