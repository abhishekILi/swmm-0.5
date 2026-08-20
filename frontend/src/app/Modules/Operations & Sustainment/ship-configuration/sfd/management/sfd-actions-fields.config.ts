import { ChipTone, DropdownOption} from "../../../../../shared/components";

export type SfdCategory =
  | "CAT I"
  | "CAT II"
  | "CAT III"
  | "Survey & Demand"
  | "Local Purchase";

export interface CategoryCard {
  id: SfdCategory;
  title: string;
  desc: string;
  color: string;
}

/** The 5 SFD transaction categories, shown as select-cards on the Add/Update screen. */
export const SFD_CATEGORIES: CategoryCard[] = [
  { id: "CAT I", title: "CAT I — Replacement, Same Make & Model", desc: "Replacement, Same Make & Model.", color: "#0088FF" },
  { id: "CAT II", title: "CAT I — Existing in Indian Navy Inventory", desc: "Existing in Indian Navy Inventory.", color: "#22C55E" },
  { id: "CAT III", title: "CAT III — New Induction", desc: "New Induction", color: "#F59E0B" },
  { id: "Survey & Demand", title: "Survey & Demand — Serial Number Change", desc: "Serial Number Change.", color: "#7FB3E0" },
  { id: "Local Purchase", title: "Local Purchase — Purchase Against NAC/ NFC", desc: "Purchase Against NAC/ NFC", color: "#A855F7" },
];

/**
 * Maps each UI category to the `transaction/<slug>/` URL segment it POSTs to, and doubles as the
 * `category` field value sent in the body / expected back on `GET sfd-list/` rows. The exact
 * string the backend stores for `category` isn't confirmed beyond the URL routing itself, so this
 * mirrors that routing exactly (e.g. "cat1", "survey-demand") — adjust if the backend expects a
 * different convention (e.g. "CAT1", "CAT I").
 */
export const CATEGORY_TO_SLUG: Record<SfdCategory, string> = {
  "CAT I": "cat1",
  "CAT II": "cat2",
  "CAT III": "cat3",
  "Survey & Demand": "survey-demand",
  "Local Purchase": "others",
};

const SLUG_TO_CATEGORY: Record<string, SfdCategory> = Object.fromEntries(
  Object.entries(CATEGORY_TO_SLUG).map(([category, slug]) => [slug, category as SfdCategory]),
);

/**
 * The `category` value expected INSIDE the create payload body (`EquipmentTransaction.TransactionCategory`
 * choices in `sfd/models.py`) — distinct from CATEGORY_TO_SLUG, which is only the URL routing segment.
 * `SFDTransactionBaseSerializer.validate()` rejects the request if this doesn't match exactly.
 */
export const CATEGORY_TO_BODY_VALUE: Record<SfdCategory, string> = {
  "CAT I": "cat1",
  "CAT II": "cat2",
  "CAT III": "cat3",
  "Survey & Demand": "survey",
  "Local Purchase": "other",
};

/** Reverses CATEGORY_TO_SLUG for reading the `?category=` query param set by
 * sfd-overview.component.ts's category deep-links — NOT for reading API response data (see
 * categoryFromBodyValue for that; the two conventions differ for Survey & Demand/Local Purchase:
 * "survey-demand"/"others" here vs. "survey"/"other" on the wire). Falls back to "Local Purchase"
 * if unrecognized. */
export function categoryFromSlug(slug: string | null | undefined): SfdCategory {
  return (slug && SLUG_TO_CATEGORY[slug.toLowerCase()]) || "Local Purchase";
}

const BODY_VALUE_TO_CATEGORY: Record<string, SfdCategory> = Object.fromEntries(
  Object.entries(CATEGORY_TO_BODY_VALUE).map(([category, value]) => [value, category as SfdCategory]),
);

/** Reverses CATEGORY_TO_BODY_VALUE for reading the `category`/`transaction_category` field back
 * off `GET sfd-list/` and `GET approval-tracking/` rows — `SFDTransaction.TransactionCategory`
 * really does store "cat1"/"cat2"/"cat3"/"survey"/"other" (confirmed against `sfd/models.py`), not
 * the "survey-demand"/"others" URL-routing slug. Falls back to "Local Purchase" if unrecognized. */
export function categoryFromBodyValue(value: string | null | undefined): SfdCategory {
  return (value && BODY_VALUE_TO_CATEGORY[value.toLowerCase()]) || "Local Purchase";
}

/** The same conceptual "Supplier" field is named differently per category — shared by the component's cascade and the payload builder so both stay in sync. */
export function supplierFieldName(category: SfdCategory | null): string {
  if (category === "CAT III") return "Supplier Name";
  if (category === "Survey & Demand" || category === "Local Purchase") return "Equipment Supplier Name";
  return "Supplier";
}

export type FieldControlType =
  | "Dropdown"
  | "Text"
  | "Number"
  | "Date"
  | "Decimal"
  | "Checkbox"
  | "Auto Fetch";

/** "Ship Master" marks fields resolved from the picked Compartment's own master record
 * (CompartmentMaster, via onCompartmentPicked) — distinct from "CMMS" (equipment/system master
 * data) even though both are non-user-entered. */
export type SourceBadge = "CMMS" | "User" | "Ship Master";

/** Every dropdown source an action-form field can bind to. All but "location" are loaded live from the backend (see SfdActionsService.loadReferenceData) — there is no static/mock data left. */
export type OptionSetKey =
  | "equipment"
  | "model"
  | "nomenclature"
  | "oem"
  | "supplier"
  | "oemPart"
  | "location"
  | "compartment"
  | "shelfLife"
  | "section"
  | "type";

export interface ActionFieldSpec {
  name: string;
  type: FieldControlType;
  required: boolean;
  source: SourceBadge;
  editable: boolean;
  optionsKey?: OptionSetKey;
}

export type OptionSetMap = Partial<Record<OptionSetKey, DropdownOption[]>>;

/**
 * `EquipmentTransaction.Location` choice codes (`sfd/models.py`) — the one option set with a
 * fixed value/label pair defined server-side rather than sourced from a list endpoint. The "5",
 * "11", "12", "14", "21", "0" legacy/"Unknown" codes are omitted from new-entry forms.
 */
export const LOCATION_OPTIONS: DropdownOption[] = [
  { label: "Port, Aft", value: "1" },
  { label: "Port, Forward", value: "2" },
  { label: "Starboard, Forward", value: "3" },
  { label: "Starboard, Aft", value: "4" },
];

/** `liveSets` is populated by the component from `SfdActionReferenceData` (real API data, no mocks). */
export function optionsFor(key: OptionSetKey | undefined, liveSets: OptionSetMap): DropdownOption[] {
  if (!key) return [];
  if (key === "location") return LOCATION_OPTIONS;
  return liveSets[key] ?? [];
}

/** Turns a field spec's display name (e.g. "Equipment Serial No") into a safe reactive-form control key. */
export function controlKey(name: string): string {
  return name.replace(/[^a-zA-Z0-9]+/g, "_");
}

const CAT_1_2_FIELDS: ActionFieldSpec[] = [
  { name: "Equipment Name", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "equipment" },
  { name: "Model", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "model" },
  { name: "Nomenclature", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "nomenclature" },
  { name: "OEM Name", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "oem" },
  { name: "Supplier", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "supplier" },
  { name: "OEM Part No", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "oemPart" },
  { name: "Equipment Serial No", type: "Text", required: true, source: "User", editable: true },
  { name: "Compartment Name", type: "Dropdown", required: true, source: "Ship Master", editable: true, optionsKey: "compartment" },
  { name: "Deck No", type: "Text", required: true, source: "Ship Master", editable: false },
  { name: "Frame Station", type: "Text", required: true, source: "Ship Master", editable: false },
  { name: "Location", type: "Dropdown", required: true, source: "Ship Master", editable: false, optionsKey: "location" },
  { name: "Installation Date", type: "Date", required: true, source: "User", editable: true },
  { name: "Authority for Installation", type: "Text", required: true, source: "User", editable: true },
  { name: "Authority Date", type: "Date", required: true, source: "User", editable: true },
  { name: "Qty Fitted", type: "Number", required: true, source: "User", editable: true },
  { name: "Shelf Life", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "shelfLife" },
  { name: "Enter R|H for SRAR return", type: "Checkbox", required: false, source: "User", editable: false },
  { name: "R|H (Running Hours) as on date", type: "Decimal", required: false, source: "User", editable: true },
  { name: "Sub Department", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "section" },
];

const CAT_3_FIELDS: ActionFieldSpec[] = [
  { name: "Equipment Name", type: "Text", required: true, source: "User", editable: true },
  { name: "Model", type: "Dropdown", required: true, source: "User", editable: true, optionsKey: "model" },
  { name: "Nomenclature", type: "Text", required: true, source: "User", editable: false },
  { name: "OEM Name", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "oem" },
  { name: "Supplier Name", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "supplier" },
  { name: "New OEM Name", type: "Text", required: true, source: "User", editable: true },
  { name: "New OEM Supplier Name", type: "Text", required: true, source: "User", editable: true },
  { name: "New OEM Part No", type: "Text", required: true, source: "User", editable: true },
  { name: "Equipment Serial No", type: "Text", required: true, source: "User", editable: true },
  { name: "Compartment Name", type: "Dropdown", required: true, source: "Ship Master", editable: true, optionsKey: "compartment" },
  { name: "Deck No", type: "Text", required: true, source: "Ship Master", editable: false },
  { name: "Frame Station", type: "Text", required: true, source: "Ship Master", editable: false },
  { name: "Location", type: "Dropdown", required: true, source: "Ship Master", editable: false, optionsKey: "location" },
  { name: "Installation Date", type: "Date", required: true, source: "User", editable: true },
  { name: "Installation Authority", type: "Text", required: true, source: "User", editable: true },
  { name: "Authority Date", type: "Date", required: true, source: "User", editable: true },
  { name: "Qty Fitted", type: "Number", required: true, source: "User", editable: true },
  { name: "Shelf Life", type: "Dropdown", required: true, source: "CMMS", editable: true, optionsKey: "shelfLife" },
  { name: "Add R|H for SRAR return", type: "Checkbox", required: false, source: "User", editable: false },
  { name: "R|H (Running Hours) as on date", type: "Decimal", required: false, source: "User", editable: true },
  { name: "Sub Department", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "section" },
];

/**
 * Several fields below are marked `required: true` even though the latest design mockup shows them
 * without an asterisk (OEM Name, Equipment Supplier Name, OEM Part No, Deck No, Frame Station,
 * Location, Compartment Name, Qty Fitted, Sub Department). This isn't a mockup mismatch by choice —
 * `SurveySerializer.validate()` (sfd/serializers.py) explicitly rejects the request if any of these
 * is falsy/blank, and several of the base fields (deck_no, location, compartment_name,
 * frame_station_from/to) have no `required=False`/`allow_blank` at the DRF field level either.
 * Marking them optional here would just mean every submission 400s with a confusing backend error
 * instead of a clear "required" hint up front.
 *
 * There is NO "Equipment Type" field here (or on CAT I/II/III) by explicit product direction, even
 * though `SFDTransactionBaseSerializer.equipment_type` is still a plain required CharField with no
 * `required=False`/`allow_blank` — every category's create call will 400 with "equipment_type: This
 * field may not be blank." until that's relaxed server-side or a default is supplied some other way.
 */
const SURVEY_DEMAND_FIELDS: ActionFieldSpec[] = [
  { name: "Equipment Name", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "equipment" },
  { name: "Model", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "model" },
  { name: "Nomenclature", type: "Dropdown", required: true, source: "CMMS", editable: false, optionsKey: "nomenclature" },
  // Every field below through Sub Department is "Auto Fetch" (readonly, no manual override) —
  // matches the reference mockup's FIELD_SPECS table exactly. onEquipmentPicked() genuinely
  // resolves OEM Name / Equipment Supplier Name / OEM Part No / Shelf Life from the picked
  // Equipment's last transaction cascade. Equipment Serial No / Deck No / Frame Station / Location /
  // Compartment Name / Installation Date / Installation Remarks / Qty Fitted / Sub Department do
  // NOT currently have an equivalent working cascade in this app (by explicit product direction,
  // matching the reference over caution) — until one exists, these fields have no way to
  // populate, which locks the Survey & Demand / Local Purchase forms out of submission entirely.
  // Building that cascade is separate follow-up work.
  { name: "OEM Name", type: "Auto Fetch", required: true, source: "CMMS", editable: false, optionsKey: "oem" },
  { name: "Equipment Supplier Name", type: "Auto Fetch", required: true, source: "CMMS", editable: false, optionsKey: "supplier" },
  { name: "OEM Part No", type: "Auto Fetch", required: true, source: "CMMS", editable: false, optionsKey: "oemPart" },
  { name: "Equipment Serial No", type: "Auto Fetch", required: true, source: "CMMS", editable: false },
  { name: "Deck No", type: "Auto Fetch", required: true, source: "CMMS", editable: false },
  { name: "Frame Station", type: "Auto Fetch", required: true, source: "CMMS", editable: false },
  { name: "Location", type: "Auto Fetch", required: true, source: "CMMS", editable: false, optionsKey: "location" },
  // Compartment Name / Sub Department are "Dropdown" (not "Auto Fetch") in the v1 reference —
  // matches isFieldEditable()'s "only Compartment Name/Sub Department stay editable in Update
  // mode" carve-out, which the "auto" case's hardcoded [readonly]="true" would otherwise defeat.
  { name: "Compartment Name", type: "Dropdown", required: true, source: "CMMS", editable: true, optionsKey: "compartment" },
  { name: "Installation Date", type: "Auto Fetch", required: true, source: "CMMS", editable: false },
  { name: "Installation Remarks", type: "Auto Fetch", required: true, source: "CMMS", editable: false },
  { name: "Qty Fitted", type: "Auto Fetch", required: true, source: "CMMS", editable: false },
  { name: "Shelf Life", type: "Auto Fetch", required: true, source: "CMMS", editable: false, optionsKey: "shelfLife" },
  { name: "Sub Department", type: "Dropdown", required: true, source: "CMMS", editable: true, optionsKey: "section" },
  { name: "Removal Date", type: "Date", required: true, source: "User", editable: true },
  { name: "Removal Authority", type: "Text", required: true, source: "User", editable: true },
  { name: "New Eqpt Serial Number", type: "Text", required: true, source: "User", editable: true },
  { name: "Date of Installation (New Eqpt)", type: "Date", required: true, source: "User", editable: true },
  { name: "Shelf Life (New Eqpt)", type: "Number", required: true, source: "CMMS", editable: true },
  { name: "Authority for Installation", type: "Text", required: true, source: "User", editable: true },
  { name: "Authority Date", type: "Date", required: true, source: "User", editable: true },
  { name: "Do You want to add RH for SRAR Return", type: "Checkbox", required: false, source: "User", editable: true },
  { name: "R/H of new eqpt at installation", type: "Decimal", required: false, source: "User", editable: true },
];

/**
 * Local Purchase now shares the Survey & Demand field set exactly (Model, Shelf Life, Sub
 * Department, Removal Date/Authority, New Eqpt Serial Number, Shelf Life (New Eqpt), the R|H
 * checkbox, etc. all apply here too) — reused directly rather than duplicated. Explicit product
 * direction: the overlap with Survey & Demand is intentional, not a bug.
 */
const OTHERS_FIELDS: ActionFieldSpec[] = SURVEY_DEMAND_FIELDS;

export const FIELD_SPECS: Record<SfdCategory, ActionFieldSpec[]> = {
  "CAT I": CAT_1_2_FIELDS,
  "CAT II": CAT_1_2_FIELDS,
  "CAT III": CAT_3_FIELDS,
  "Survey & Demand": SURVEY_DEMAND_FIELDS,
  "Local Purchase": OTHERS_FIELDS,
};

/** Maps a rendered field name (after the Equipment→System swap) to the row key used to prefill it on Update. */
export const PREFILL_FIELD_MAP: { pattern: RegExp; key: keyof SfdActionRow }[] = [
  { pattern: /^(Equipment|System) Name$/, key: "name" },
  { pattern: /^Model$/, key: "model" },
  { pattern: /^Nomenclature$/, key: "nomen" },
  { pattern: /^(New )?OEM Name$/, key: "oem" },
  { pattern: /^(Supplier|Supplier Name|Equipment Supplier Name|New OEM Supplier Name)$/, key: "supplier" },
  { pattern: /OEM Part No$/, key: "part" },
  { pattern: /Serial No$|Serial Number$/, key: "serial" },
  { pattern: /^Deck No$/, key: "deck" },
  { pattern: /^Frame Station$/, key: "frame" },
  { pattern: /^Location$/, key: "location" },
  { pattern: /^Compartment Name$/, key: "compartment" },
  { pattern: /Installation Date$/, key: "installDate" },
  { pattern: /Authority for Installation$|Installation Authority$/, key: "authority" },
  { pattern: /^Authority Date$/, key: "authorityDate" },
  { pattern: /^Qty Fitted$/, key: "qty" },
  { pattern: /^Shelf Life$/, key: "shelfLife" },
  { pattern: /Running Hours|R\|H|R\/H/, key: "rh" },
  { pattern: /^Sub Department$/, key: "section" },
];

/** Row shape for the Remove flow's "Active Maintenance Routines & Defect Records" table — populated from `GET sfd-list/{id}/open-dependencies/` (open_defects + maintenance_routines combined). */
export interface DefectRecord {
  id: string;
  type: "Defect" | "Routine";
  desc: string;
  raised: string;
  priority: string;
  status: string;
}

export interface HistoryStat {
  label: string;
  value: string;
  tone?: ChipTone;
}

export const EQUIPMENT_HISTORY_STATS: HistoryStat[] = [
  { label: "Current Status", value: "Operational", tone: "success" },
  { label: "Running Hours", value: "14,280 hrs" },
  { label: "Pending Defects", value: "2", tone: "warning" },
  { label: "Pending Routines", value: "3", tone: "warning" },
];

export interface HistoryRow {
  a: string;
  b: string;
  tag: string;
  tone: ChipTone;
}

export interface HistorySection {
  title: string;
  rows: HistoryRow[];
}

export const EQUIPMENT_HISTORY_SECTIONS: HistorySection[] = [
  {
    title: "Previous Ship(s)",
    rows: [
      { a: "HMS Dauntless (D33)", b: "2016 – 2019", tag: "Transferred", tone: "info" },
      { a: "HMS Diamond (D34)", b: "2019 – 2022", tag: "Transferred", tone: "info" },
    ],
  },
  {
    title: "Installation History",
    rows: [
      { a: "HMS Daring (D32)", b: "Installed 14-03-22", tag: "Op Auth 4471", tone: "success" },
      { a: "HMS Dauntless (D33)", b: "Installed 02-11-19", tag: "Op Auth 3350", tone: "success" },
    ],
  },
  {
    title: "Removal History",
    rows: [{ a: "HMS Diamond (D34)", b: "Removed 28-02-22", tag: "Refit", tone: "warning" }],
  },
  {
    title: "Maintenance History",
    rows: [
      { a: "Quarterly Overhaul", b: "Completed 14-02-26", tag: "Closed", tone: "success" },
      { a: "Annual Survey", b: "Completed 10-11-25", tag: "Closed", tone: "success" },
    ],
  },
  {
    title: "Defect History",
    rows: [{ a: "Excess vibration — main bearing", b: "Rectified 20-02-26", tag: "Rectified", tone: "success" }],
  },
  {
    title: "Pending Defects",
    rows: [
      { a: "Seal seepage — LO circuit", b: "Raised 21-06-26", tag: "Open", tone: "warning" },
      { a: "Coupling alignment drift", b: "Raised 30-06-26", tag: "Open", tone: "warning" },
    ],
  },
  {
    title: "Pending Routines",
    rows: [
      { a: "Half-yearly calibration", b: "Due 15-07-26", tag: "Due Soon", tone: "warning" },
      { a: "Quarterly lubrication check", b: "Due 22-07-26", tag: "Due Soon", tone: "warning" },
      { a: "Annual insulation resistance test", b: "Due 05-08-26", tag: "Scheduled", tone: "info" },
    ],
  },
];

export interface SfdActionRow {
  code: string;
  name: string;
  nomen: string;
  dept: string;
  qty: number;
  maintop: string;
  serial: string;
  cat: SfdCategory;
  system: string;
  model: string;
  oem: string;
  supplier: string;
  part: string;
  deck: string;
  frame: string;
  location: string;
  compartment: string;
  installDate: string;
  authority: string;
  /** Optional only because the SFD_ROWS demo/fallback rows below predate this field — real API rows
   * (see mapRawRowToDisplayRow) always set it. */
  authorityDate?: string;
  shelfLife: string;
  rh: string;
  section: string;
  type: string;
  /** The record's OWN transaction type ("system" vs "equipment") — distinct from `system`, which is
   * the (possibly unrelated) parent-system NAME an equipment record belongs to. Only real API rows
   * set this (via `mapRawRowToDisplayRow`); mock rows default to `false` (Equipment). */
  isSystemRecord?: boolean;
}

export const SFD_ROWS: SfdActionRow[] = [
  { code: "INSMA-ME-0142", name: "LO Pump - ME No.1", nomen: "PUMP,LUB OIL,CENT", dept: "PGD", qty: 2, maintop: "MT-4471", serial: "LP-ME1-4471-A", cat: "CAT I", system: "Propulsion", model: "CLP-250 Mk-II", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-4471-LP", deck: "03", frame: "74–82", location: "Machinery Space", compartment: "Aux Machinery Room", installDate: "12-Mar-2024", authority: "NHQ/REFIT/2024/0142", shelfLife: "12 Years", rh: "14,280", section: "Lubrication System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0311", name: "Sea Viper Director", nomen: "DIRECTOR,FIRE CTRL", dept: "Radar", qty: 1, maintop: "MT-8820", serial: "SVD-8820-01", cat: "CAT II", system: "Radar", model: "SYLVER-A50", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-8820-DIR", deck: "05", frame: "40–46", location: "Above Bridge", compartment: "Director Platform", installDate: "22-Jan-2023", authority: "NHQ/REFIT/2023/0311", shelfLife: "20 Years", rh: "—", section: "Fire Control", type: "Sensor System" },
  { code: "INSMA-EL-0207", name: "440V Switchboard", nomen: "SWBD,440V,MAIN", dept: "Power Gen", qty: 4, maintop: "MT-1163", serial: "SWB-440-1163", cat: "CAT I", system: "Electrical", model: "MSB-440-4P", oem: "ABB Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-1163-SWB", deck: "02", frame: "60–66", location: "Machinery Space", compartment: "Main Switchboard Room", installDate: "04-Jun-2022", authority: "NHQ/REFIT/2022/0207", shelfLife: "15 Years", rh: "—", section: "Power Distribution", type: "Electrical Equipment" },
  { code: "INSMA-NV-0455", name: "Gyro Compass", nomen: "COMPASS,GYRO,MASTER", dept: "Radio", qty: 1, maintop: "MT-5502", serial: "GC-5502-M1", cat: "CAT III", system: "Navigation", model: "GC-9 Mk-III", oem: "Sperry Marine", supplier: "Naval Systems Ltd", part: "PN-5502-GC", deck: "04", frame: "50–54", location: "Bridge", compartment: "Navigation Room", installDate: "30-Sep-2025", authority: "NHQ/REFIT/2025/0455", shelfLife: "10 Years", rh: "—", section: "Navigation System", type: "Sensor System" },
  { code: "INSMA-DC-0198", name: "Fire Main Pump", nomen: "PUMP,FIRE MAIN,CENT", dept: "PGD", qty: 2, maintop: "MT-3390", serial: "FMP-3390-B", cat: "CAT II", system: "Fire Fighting", model: "FMP-500-HD", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-3390-FMP", deck: "01", frame: "20–26", location: "Machinery Space", compartment: "Fire Pump Room", installDate: "17-Aug-2023", authority: "NHQ/REFIT/2023/0198", shelfLife: "15 Years", rh: "9,120", section: "Damage Control System", type: "Rotating Machinery" },
  { code: "INSMA-EL-0276", name: "Diesel Alternator", nomen: "ALTERNATOR,DIESEL", dept: "Power Gen", qty: 3, maintop: "MT-7742", serial: "DA-7742-C", cat: "CAT I", system: "Power Generation", model: "DG-750-Mk2", oem: "Cummins Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-7742-DA", deck: "02", frame: "30–38", location: "Machinery Space", compartment: "Generator Room", installDate: "09-Nov-2022", authority: "NHQ/REFIT/2022/0276", shelfLife: "18 Years", rh: "21,450", section: "Power Generation System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0389", name: "CIWS Mount", nomen: "MOUNT,CIWS,30MM", dept: "Radar", qty: 1, maintop: "MT-9901", serial: "CIWS-9901-P", cat: "CAT III", system: "Weapon System", model: "AK-630M", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-9901-CIWS", deck: "06", frame: "10–16", location: "Foredeck", compartment: "Gun Mount Platform", installDate: "15-Feb-2025", authority: "NHQ/REFIT/2025/0389", shelfLife: "20 Years", rh: "—", section: "Weapon System", type: "Weapon Mount" },
  { code: "INSMA-ME-0142", name: "LO Pump - ME No.1", nomen: "PUMP,LUB OIL,CENT", dept: "PGD", qty: 2, maintop: "MT-4471", serial: "LP-ME1-4471-A", cat: "CAT I", system: "Propulsion", model: "CLP-250 Mk-II", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-4471-LP", deck: "03", frame: "74–82", location: "Machinery Space", compartment: "Aux Machinery Room", installDate: "12-Mar-2024", authority: "NHQ/REFIT/2024/0142", shelfLife: "12 Years", rh: "14,280", section: "Lubrication System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0311", name: "Sea Viper Director", nomen: "DIRECTOR,FIRE CTRL", dept: "Radar", qty: 1, maintop: "MT-8820", serial: "SVD-8820-01", cat: "CAT II", system: "Radar", model: "SYLVER-A50", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-8820-DIR", deck: "05", frame: "40–46", location: "Above Bridge", compartment: "Director Platform", installDate: "22-Jan-2023", authority: "NHQ/REFIT/2023/0311", shelfLife: "20 Years", rh: "—", section: "Fire Control", type: "Sensor System" },
  { code: "INSMA-EL-0207", name: "440V Switchboard", nomen: "SWBD,440V,MAIN", dept: "Power Gen", qty: 4, maintop: "MT-1163", serial: "SWB-440-1163", cat: "CAT I", system: "Electrical", model: "MSB-440-4P", oem: "ABB Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-1163-SWB", deck: "02", frame: "60–66", location: "Machinery Space", compartment: "Main Switchboard Room", installDate: "04-Jun-2022", authority: "NHQ/REFIT/2022/0207", shelfLife: "15 Years", rh: "—", section: "Power Distribution", type: "Electrical Equipment" },
  { code: "INSMA-NV-0455", name: "Gyro Compass", nomen: "COMPASS,GYRO,MASTER", dept: "Radio", qty: 1, maintop: "MT-5502", serial: "GC-5502-M1", cat: "CAT III", system: "Navigation", model: "GC-9 Mk-III", oem: "Sperry Marine", supplier: "Naval Systems Ltd", part: "PN-5502-GC", deck: "04", frame: "50–54", location: "Bridge", compartment: "Navigation Room", installDate: "30-Sep-2025", authority: "NHQ/REFIT/2025/0455", shelfLife: "10 Years", rh: "—", section: "Navigation System", type: "Sensor System" },
  { code: "INSMA-DC-0198", name: "Fire Main Pump", nomen: "PUMP,FIRE MAIN,CENT", dept: "PGD", qty: 2, maintop: "MT-3390", serial: "FMP-3390-B", cat: "CAT II", system: "Fire Fighting", model: "FMP-500-HD", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-3390-FMP", deck: "01", frame: "20–26", location: "Machinery Space", compartment: "Fire Pump Room", installDate: "17-Aug-2023", authority: "NHQ/REFIT/2023/0198", shelfLife: "15 Years", rh: "9,120", section: "Damage Control System", type: "Rotating Machinery" },
  { code: "INSMA-EL-0276", name: "Diesel Alternator", nomen: "ALTERNATOR,DIESEL", dept: "Power Gen", qty: 3, maintop: "MT-7742", serial: "DA-7742-C", cat: "CAT I", system: "Power Generation", model: "DG-750-Mk2", oem: "Cummins Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-7742-DA", deck: "02", frame: "30–38", location: "Machinery Space", compartment: "Generator Room", installDate: "09-Nov-2022", authority: "NHQ/REFIT/2022/0276", shelfLife: "18 Years", rh: "21,450", section: "Power Generation System", type: "Rotating Machinery" },
  { code: "INSMA-ME-0142", name: "LO Pump - ME No.1", nomen: "PUMP,LUB OIL,CENT", dept: "PGD", qty: 2, maintop: "MT-4471", serial: "LP-ME1-4471-A", cat: "CAT I", system: "Propulsion", model: "CLP-250 Mk-II", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-4471-LP", deck: "03", frame: "74–82", location: "Machinery Space", compartment: "Aux Machinery Room", installDate: "12-Mar-2024", authority: "NHQ/REFIT/2024/0142", shelfLife: "12 Years", rh: "14,280", section: "Lubrication System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0311", name: "Sea Viper Director", nomen: "DIRECTOR,FIRE CTRL", dept: "Radar", qty: 1, maintop: "MT-8820", serial: "SVD-8820-01", cat: "CAT II", system: "Radar", model: "SYLVER-A50", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-8820-DIR", deck: "05", frame: "40–46", location: "Above Bridge", compartment: "Director Platform", installDate: "22-Jan-2023", authority: "NHQ/REFIT/2023/0311", shelfLife: "20 Years", rh: "—", section: "Fire Control", type: "Sensor System" },
  { code: "INSMA-EL-0207", name: "440V Switchboard", nomen: "SWBD,440V,MAIN", dept: "Power Gen", qty: 4, maintop: "MT-1163", serial: "SWB-440-1163", cat: "CAT I", system: "Electrical", model: "MSB-440-4P", oem: "ABB Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-1163-SWB", deck: "02", frame: "60–66", location: "Machinery Space", compartment: "Main Switchboard Room", installDate: "04-Jun-2022", authority: "NHQ/REFIT/2022/0207", shelfLife: "15 Years", rh: "—", section: "Power Distribution", type: "Electrical Equipment" },
  { code: "INSMA-NV-0455", name: "Gyro Compass", nomen: "COMPASS,GYRO,MASTER", dept: "Radio", qty: 1, maintop: "MT-5502", serial: "GC-5502-M1", cat: "CAT III", system: "Navigation", model: "GC-9 Mk-III", oem: "Sperry Marine", supplier: "Naval Systems Ltd", part: "PN-5502-GC", deck: "04", frame: "50–54", location: "Bridge", compartment: "Navigation Room", installDate: "30-Sep-2025", authority: "NHQ/REFIT/2025/0455", shelfLife: "10 Years", rh: "—", section: "Navigation System", type: "Sensor System" },
  { code: "INSMA-DC-0198", name: "Fire Main Pump", nomen: "PUMP,FIRE MAIN,CENT", dept: "PGD", qty: 2, maintop: "MT-3390", serial: "FMP-3390-B", cat: "CAT II", system: "Fire Fighting", model: "FMP-500-HD", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-3390-FMP", deck: "01", frame: "20–26", location: "Machinery Space", compartment: "Fire Pump Room", installDate: "17-Aug-2023", authority: "NHQ/REFIT/2023/0198", shelfLife: "15 Years", rh: "9,120", section: "Damage Control System", type: "Rotating Machinery" },
  { code: "INSMA-EL-0276", name: "Diesel Alternator", nomen: "ALTERNATOR,DIESEL", dept: "Power Gen", qty: 3, maintop: "MT-7742", serial: "DA-7742-C", cat: "CAT I", system: "Power Generation", model: "DG-750-Mk2", oem: "Cummins Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-7742-DA", deck: "02", frame: "30–38", location: "Machinery Space", compartment: "Generator Room", installDate: "09-Nov-2022", authority: "NHQ/REFIT/2022/0276", shelfLife: "18 Years", rh: "21,450", section: "Power Generation System", type: "Rotating Machinery" },
{ code: "INSMA-ME-0142", name: "LO Pump - ME No.1", nomen: "PUMP,LUB OIL,CENT", dept: "PGD", qty: 2, maintop: "MT-4471", serial: "LP-ME1-4471-A", cat: "CAT I", system: "Propulsion", model: "CLP-250 Mk-II", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-4471-LP", deck: "03", frame: "74–82", location: "Machinery Space", compartment: "Aux Machinery Room", installDate: "12-Mar-2024", authority: "NHQ/REFIT/2024/0142", shelfLife: "12 Years", rh: "14,280", section: "Lubrication System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0311", name: "Sea Viper Director", nomen: "DIRECTOR,FIRE CTRL", dept: "Radar", qty: 1, maintop: "MT-8820", serial: "SVD-8820-01", cat: "CAT II", system: "Radar", model: "SYLVER-A50", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-8820-DIR", deck: "05", frame: "40–46", location: "Above Bridge", compartment: "Director Platform", installDate: "22-Jan-2023", authority: "NHQ/REFIT/2023/0311", shelfLife: "20 Years", rh: "—", section: "Fire Control", type: "Sensor System" },
  { code: "INSMA-EL-0207", name: "440V Switchboard", nomen: "SWBD,440V,MAIN", dept: "Power Gen", qty: 4, maintop: "MT-1163", serial: "SWB-440-1163", cat: "CAT I", system: "Electrical", model: "MSB-440-4P", oem: "ABB Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-1163-SWB", deck: "02", frame: "60–66", location: "Machinery Space", compartment: "Main Switchboard Room", installDate: "04-Jun-2022", authority: "NHQ/REFIT/2022/0207", shelfLife: "15 Years", rh: "—", section: "Power Distribution", type: "Electrical Equipment" },
  { code: "INSMA-NV-0455", name: "Gyro Compass", nomen: "COMPASS,GYRO,MASTER", dept: "Radio", qty: 1, maintop: "MT-5502", serial: "GC-5502-M1", cat: "CAT III", system: "Navigation", model: "GC-9 Mk-III", oem: "Sperry Marine", supplier: "Naval Systems Ltd", part: "PN-5502-GC", deck: "04", frame: "50–54", location: "Bridge", compartment: "Navigation Room", installDate: "30-Sep-2025", authority: "NHQ/REFIT/2025/0455", shelfLife: "10 Years", rh: "—", section: "Navigation System", type: "Sensor System" },
  { code: "INSMA-DC-0198", name: "Fire Main Pump", nomen: "PUMP,FIRE MAIN,CENT", dept: "PGD", qty: 2, maintop: "MT-3390", serial: "FMP-3390-B", cat: "CAT II", system: "Fire Fighting", model: "FMP-500-HD", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-3390-FMP", deck: "01", frame: "20–26", location: "Machinery Space", compartment: "Fire Pump Room", installDate: "17-Aug-2023", authority: "NHQ/REFIT/2023/0198", shelfLife: "15 Years", rh: "9,120", section: "Damage Control System", type: "Rotating Machinery" },
  { code: "INSMA-EL-0276", name: "Diesel Alternator", nomen: "ALTERNATOR,DIESEL", dept: "Power Gen", qty: 3, maintop: "MT-7742", serial: "DA-7742-C", cat: "CAT I", system: "Power Generation", model: "DG-750-Mk2", oem: "Cummins Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-7742-DA", deck: "02", frame: "30–38", location: "Machinery Space", compartment: "Generator Room", installDate: "09-Nov-2022", authority: "NHQ/REFIT/2022/0276", shelfLife: "18 Years", rh: "21,450", section: "Power Generation System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0389", name: "CIWS Mount", nomen: "MOUNT,CIWS,30MM", dept: "Radar", qty: 1, maintop: "MT-9901", serial: "CIWS-9901-P", cat: "CAT III", system: "Weapon System", model: "AK-630M", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-9901-CIWS", deck: "06", frame: "10–16", location: "Foredeck", compartment: "Gun Mount Platform", installDate: "15-Feb-2025", authority: "NHQ/REFIT/2025/0389", shelfLife: "20 Years", rh: "—", section: "Weapon System", type: "Weapon Mount" },
  { code: "INSMA-ME-0142", name: "LO Pump - ME No.1", nomen: "PUMP,LUB OIL,CENT", dept: "PGD", qty: 2, maintop: "MT-4471", serial: "LP-ME1-4471-A", cat: "CAT I", system: "Propulsion", model: "CLP-250 Mk-II", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-4471-LP", deck: "03", frame: "74–82", location: "Machinery Space", compartment: "Aux Machinery Room", installDate: "12-Mar-2024", authority: "NHQ/REFIT/2024/0142", shelfLife: "12 Years", rh: "14,280", section: "Lubrication System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0311", name: "Sea Viper Director", nomen: "DIRECTOR,FIRE CTRL", dept: "Radar", qty: 1, maintop: "MT-8820", serial: "SVD-8820-01", cat: "CAT II", system: "Radar", model: "SYLVER-A50", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-8820-DIR", deck: "05", frame: "40–46", location: "Above Bridge", compartment: "Director Platform", installDate: "22-Jan-2023", authority: "NHQ/REFIT/2023/0311", shelfLife: "20 Years", rh: "—", section: "Fire Control", type: "Sensor System" },
  { code: "INSMA-EL-0207", name: "440V Switchboard", nomen: "SWBD,440V,MAIN", dept: "Power Gen", qty: 4, maintop: "MT-1163", serial: "SWB-440-1163", cat: "CAT I", system: "Electrical", model: "MSB-440-4P", oem: "ABB Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-1163-SWB", deck: "02", frame: "60–66", location: "Machinery Space", compartment: "Main Switchboard Room", installDate: "04-Jun-2022", authority: "NHQ/REFIT/2022/0207", shelfLife: "15 Years", rh: "—", section: "Power Distribution", type: "Electrical Equipment" },
  { code: "INSMA-NV-0455", name: "Gyro Compass", nomen: "COMPASS,GYRO,MASTER", dept: "Radio", qty: 1, maintop: "MT-5502", serial: "GC-5502-M1", cat: "CAT III", system: "Navigation", model: "GC-9 Mk-III", oem: "Sperry Marine", supplier: "Naval Systems Ltd", part: "PN-5502-GC", deck: "04", frame: "50–54", location: "Bridge", compartment: "Navigation Room", installDate: "30-Sep-2025", authority: "NHQ/REFIT/2025/0455", shelfLife: "10 Years", rh: "—", section: "Navigation System", type: "Sensor System" },
  { code: "INSMA-DC-0198", name: "Fire Main Pump", nomen: "PUMP,FIRE MAIN,CENT", dept: "PGD", qty: 2, maintop: "MT-3390", serial: "FMP-3390-B", cat: "CAT II", system: "Fire Fighting", model: "FMP-500-HD", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-3390-FMP", deck: "01", frame: "20–26", location: "Machinery Space", compartment: "Fire Pump Room", installDate: "17-Aug-2023", authority: "NHQ/REFIT/2023/0198", shelfLife: "15 Years", rh: "9,120", section: "Damage Control System", type: "Rotating Machinery" },
  { code: "INSMA-EL-0276", name: "Diesel Alternator", nomen: "ALTERNATOR,DIESEL", dept: "Power Gen", qty: 3, maintop: "MT-7742", serial: "DA-7742-C", cat: "CAT I", system: "Power Generation", model: "DG-750-Mk2", oem: "Cummins Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-7742-DA", deck: "02", frame: "30–38", location: "Machinery Space", compartment: "Generator Room", installDate: "09-Nov-2022", authority: "NHQ/REFIT/2022/0276", shelfLife: "18 Years", rh: "21,450", section: "Power Generation System", type: "Rotating Machinery" },
  { code: "INSMA-ME-0142", name: "LO Pump - ME No.1", nomen: "PUMP,LUB OIL,CENT", dept: "PGD", qty: 2, maintop: "MT-4471", serial: "LP-ME1-4471-A", cat: "CAT I", system: "Propulsion", model: "CLP-250 Mk-II", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-4471-LP", deck: "03", frame: "74–82", location: "Machinery Space", compartment: "Aux Machinery Room", installDate: "12-Mar-2024", authority: "NHQ/REFIT/2024/0142", shelfLife: "12 Years", rh: "14,280", section: "Lubrication System", type: "Rotating Machinery" },
  { code: "INSMA-WE-0311", name: "Sea Viper Director", nomen: "DIRECTOR,FIRE CTRL", dept: "Radar", qty: 1, maintop: "MT-8820", serial: "SVD-8820-01", cat: "CAT II", system: "Radar", model: "SYLVER-A50", oem: "MBDA Systems", supplier: "Naval Systems Ltd", part: "PN-8820-DIR", deck: "05", frame: "40–46", location: "Above Bridge", compartment: "Director Platform", installDate: "22-Jan-2023", authority: "NHQ/REFIT/2023/0311", shelfLife: "20 Years", rh: "—", section: "Fire Control", type: "Sensor System" },
  { code: "INSMA-EL-0207", name: "440V Switchboard", nomen: "SWBD,440V,MAIN", dept: "Power Gen", qty: 4, maintop: "MT-1163", serial: "SWB-440-1163", cat: "CAT I", system: "Electrical", model: "MSB-440-4P", oem: "ABB Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-1163-SWB", deck: "02", frame: "60–66", location: "Machinery Space", compartment: "Main Switchboard Room", installDate: "04-Jun-2022", authority: "NHQ/REFIT/2022/0207", shelfLife: "15 Years", rh: "—", section: "Power Distribution", type: "Electrical Equipment" },
  { code: "INSMA-NV-0455", name: "Gyro Compass", nomen: "COMPASS,GYRO,MASTER", dept: "Radio", qty: 1, maintop: "MT-5502", serial: "GC-5502-M1", cat: "CAT III", system: "Navigation", model: "GC-9 Mk-III", oem: "Sperry Marine", supplier: "Naval Systems Ltd", part: "PN-5502-GC", deck: "04", frame: "50–54", location: "Bridge", compartment: "Navigation Room", installDate: "30-Sep-2025", authority: "NHQ/REFIT/2025/0455", shelfLife: "10 Years", rh: "—", section: "Navigation System", type: "Sensor System" },
  { code: "INSMA-DC-0198", name: "Fire Main Pump", nomen: "PUMP,FIRE MAIN,CENT", dept: "PGD", qty: 2, maintop: "MT-3390", serial: "FMP-3390-B", cat: "CAT II", system: "Fire Fighting", model: "FMP-500-HD", oem: "KSB Marine", supplier: "Naval Systems Ltd", part: "PN-3390-FMP", deck: "01", frame: "20–26", location: "Machinery Space", compartment: "Fire Pump Room", installDate: "17-Aug-2023", authority: "NHQ/REFIT/2023/0198", shelfLife: "15 Years", rh: "9,120", section: "Damage Control System", type: "Rotating Machinery" },
  { code: "INSMA-EL-0276", name: "Diesel Alternator", nomen: "ALTERNATOR,DIESEL", dept: "Power Gen", qty: 3, maintop: "MT-7742", serial: "DA-7742-C", cat: "CAT I", system: "Power Generation", model: "DG-750-Mk2", oem: "Cummins Marine", supplier: "Electro Naval Pvt Ltd", part: "PN-7742-DA", deck: "02", frame: "30–38", location: "Machinery Space", compartment: "Generator Room", installDate: "09-Nov-2022", authority: "NHQ/REFIT/2022/0276", shelfLife: "18 Years", rh: "21,450", section: "Power Generation System", type: "Rotating Machinery" },
];

export interface DeletedSfdRow {
  code: string;
  name: string;
  nomen: string;
  date: string;
  auth: string;
  reason: string;
  by: string;
}

export const DELETED_SFD_ROWS: DeletedSfdRow[] = [
  { code: "INSMA-ME-0031", name: "HP Air Compressor", nomen: "COMP,HP AIR", date: "12-04-26", auth: "NHQ/44/2026", reason: "Obsolete", by: "Lt Cdr R Menon" },
  { code: "INSMA-EL-0119", name: "Nav Light Panel", nomen: "PANEL,NAV LIGHT", date: "28-03-26", auth: "SHIP/112/2026", reason: "Damaged Beyond Repair", by: "Lt A Sharma" },
  { code: "INSMA-WE-0288", name: "Chaff Launcher", nomen: "LAUNCHER,CHAFF", date: "09-02-26", auth: "WEO/18/2026", reason: "Replaced (CAT I)", by: "Cdr V Rao" },
  { code: "INSMA-NV-0044", name: "Echo Sounder", nomen: "SOUNDER,ECHO", date: "21-01-26", auth: "NAV/07/2026", reason: "Survey & Demand", by: "Lt Cdr S Nair" },
];

export type ActivityKind = "added" | "removed" | "serialChanged" | "submitted";

export interface RecentActivityRow {
  icon: ActivityKind;
  name: string;
  tag: string;
  tone: ChipTone;
  code: string;
  detail: string;
  date: string;
  by: string;
}

/** `GET recent-activity/`'s `tag` values, mapped to this popup's icon/tone — see
 * `SfdActionsService.loadRecentActivity()`, which is where a raw row is turned into a
 * `RecentActivityRow`. */
export const RECENT_ACTIVITY_TAG_META: Record<string, { icon: ActivityKind; tone: ChipTone }> = {
  Added: { icon: "added", tone: "success" },
  Removed: { icon: "removed", tone: "danger" },
  "Serial Changed": { icon: "serialChanged", tone: "warning" },
  Submitted: { icon: "submitted", tone: "info" },
};

/** Real values from `GET approval-tracking/` are only ever "Pending"/"Approved" — "Returned"/"Rejected" are kept for tone-map completeness/forward-compat. */
export type ApprovalStatus = "Pending" | "Approved" | "Returned" | "Rejected";

/** Display row for the "View Approval Status" grid, mapped from `RawApprovalTrackingRow`. `cat`
 * is the underlying transaction's SFD category ("CAT I", "Survey & Demand", ...), resolved via
 * categoryFromBodyValue(row.transaction_category) — distinct from `row.category`
 * ("Remove"/"Change"), which is the request TYPE the backend groups by, not currently surfaced. */
export interface ApprovalSfdRow {
  id: string;
  eqp: string;
  cat: string;
  by: string;
  date: string;
  status: ApprovalStatus;
  officer: string;
  remarks: string;
  approveDate: string;
  lastUpdatedDate: string;
  /** "remove" | "change" — the exact `category` value `PUT approval-tracking/` needs to know which
   * table (RemoveEquipmentRequest/ChangeEquipmentRequest) to update. Distinct from `cat` (the
   * equipment's own SFD category). */
  requestType: "remove" | "change";
  /** Raw `SFDTransaction.category` body-value ("cat1"/"survey"/...) — round-tripped back as
   * `transaction_category` on resubmit when the edited `cat` display label doesn't map cleanly
   * back through CATEGORY_TO_BODY_VALUE (it's a free-text field in the correction form). */
  transactionCategoryRaw: string;
}

export const APPROVAL_STATUS_TONE_MAP: Record<ApprovalStatus, ChipTone> = {
  Pending: "warning",
  Approved: "success",
  Returned: "info",
  Rejected: "info",
};

/** Display label shown in the grid/detail chip — distinct from the raw `ApprovalStatus` value used for
 * filtering/tone lookup. "Rejected" is displayed as "Returned" (the two are treated as the same outcome). */
export const APPROVAL_STATUS_LABEL_MAP: Record<ApprovalStatus, string> = {
  Pending: "In Progress – INSMA Approval",
  Approved: "Approved",
  Returned: "Returned",
  Rejected: "Returned",
};

/** The 4 query params `GET sfd-list/` (and `GET sfd-list/filter-options/`) both accept. */
export type SfdListFilterParamKey = "equipment_name" | "nomenclature" | "sub_dept" | "maintop_id";

export interface ActionFilterDef {
  name: string;
  paramKey: SfdListFilterParamKey;
}

/** The 4 Active-list filter dropdowns — both their applied filter (sent as a `sfd-list/` query
 * param) and their option lists (from `sfd-list/filter-options/`, the full active dataset rather
 * than whatever page happens to be loaded) key off the same `paramKey`. */
export const ACTION_FILTER_DEFS: ActionFilterDef[] = [
  { name: "Equipment Name", paramKey: "equipment_name" },
  { name: "Nomenclature", paramKey: "nomenclature" },
  { name: "Sub Dept", paramKey: "sub_dept" },
  { name: "Maintop", paramKey: "maintop_id" },
];
