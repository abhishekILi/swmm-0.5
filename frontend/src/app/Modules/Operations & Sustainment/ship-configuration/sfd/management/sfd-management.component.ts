import {
  Component,
  computed,
  signal,
  effect,
  inject,
  untracked,
  OnDestroy,
  ChangeDetectionStrategy,
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { NgTemplateOutlet } from "@angular/common";

import {
  FormBuilder,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";
import { ActivatedRoute } from "@angular/router";
import { NotificationService } from "../../../../../Core/services/notification/notification.service";

import {
  DataGrid,
  ActionRendererComponent,
  GridAction,
  GridStatusChipRenderer,
  DatePickerComponent,
  DetailDrawer,
  DrawerStat,
  InputField,
  ModalComponent,
  SelectInput,
  DropdownOption,
  StatusChip,
  ChipTone,
  TextareaInput,
  IconComponent
} from "../../../../../shared/components";



import { NetworkStatusService } from "../../../../../Core/services/common/network-status.service";
import { SfdActionsService } from "../services/management-services/sfd-actions.service";
import { SfdAddFormDraftService } from "./sfd-add-form-draft.service";
import {
  CascadingDropdownValues,
  RawEquipmentTransactionRow,
  RawRemovalDetails,
  RawUpdateSrNoDetails,
  SfdActionReferenceData,
  SfdListFilterOptions,
} from "../services/management-services/sfd-actions.models";

import {
  ACTION_FILTER_DEFS,
  ActionFieldSpec,
  APPROVAL_STATUS_LABEL_MAP,
  APPROVAL_STATUS_TONE_MAP,
  ApprovalSfdRow,
  ApprovalStatus,
  categoryFromBodyValue,
  categoryFromSlug,
  controlKey,
  DefectRecord,
  DeletedSfdRow,
  EQUIPMENT_HISTORY_SECTIONS,
  EQUIPMENT_HISTORY_STATS,
  FIELD_SPECS,
  LOCATION_OPTIONS,
  OptionSetMap,
  PREFILL_FIELD_MAP,
  RecentActivityRow,
  SFD_CATEGORIES,
  SfdActionRow,
  SfdCategory,
  SfdListFilterParamKey,
  optionsFor,
  supplierFieldName,
} from "./sfd-actions-fields.config";

type MgmtView = "list" | "add" | "deleted" | "approval" | "approvalDetail";
type SfdType = "Equipment" | "System";
type RecModalMode = "update" | "serial";
type FieldKind = "select" | "text" | "number" | "date" | "check" | "serial" | "auto" | "frameRange";
type RemoveStage = "loading" | "choose" | "defects" | "form";
type RemoveOption = "close" | "associate" | null;
type FilterValue = string | number | boolean | null | undefined;

interface DisplayField {
  key: string;
  rawName: string;
  label: string;
  required: boolean;
  badge: string;
  badgeColor: string;
  placeholder: string;
  kind: FieldKind;
  options: DropdownOption[];
  /** Deck No / Location / Frame Station are always populated by the Compartment Name cascade
   * (see onCompartmentPicked) — never hand-typed, in Add mode or Update mode alike. */
  readonly: boolean;
}

interface DisplayFieldValue {
  label: string;
  value: string;
  badge: "CMMS" | "User";
  badgeColor: string;
}

const TONE_COLOR: Record<ChipTone, string> = {
  success: "#22C55E",
  warning: "#F59E0B",
  danger: "#F82C36",
  info: "#4AA8FF",
  neutral: "#9db6cc",
};

function isSerialSpec(s: ActionFieldSpec): boolean {
  return s.type === "Text" && /Serial No$|Serial Number$/i.test(s.name);
}

/** Backend `DateTimeField`s come back as full ISO datetimes — `<input type="date">` needs the
 * bare `yyyy-MM-dd` prefix, or the control silently shows blank. */
function toDateInputValue(value: string | null | undefined): string {
  return value ? value.slice(0, 10) : "";
}

const CASCADE_DATE_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** ISO `YYYY-MM-DD` (get_equipment/'s `installation_date`) → "DD-MMM-YYYY", matching
 * app-date-picker's own display format — Survey & Demand/Local Purchase's Installation Date is
 * Auto Fetch (a plain read-only value, not an app-date-picker), so nothing else reformats it.
 * Parsed directly off the string rather than `new Date(...)`, which would read a bare date as UTC
 * midnight and can shift the displayed day by one depending on the local timezone. */
function formatCascadeDate(value: string | null | undefined): string {
  if (!value) return "";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) return value;
  const [, yyyy, mm, dd] = match;
  const mmm = CASCADE_DATE_MONTHS[Number(mm) - 1];
  return mmm ? `${dd}-${mmm}-${yyyy}` : value;
}

function isRhSpec(s: ActionFieldSpec): boolean {
  return s.type === "Decimal" && /Running Hours|R\|H|R\/H/i.test(s.name);
}

function isFrameRangeSpec(s: ActionFieldSpec): boolean {
  return /^Frame Station$/i.test(s.name);
}

/** CAT III's "OEM Name" dropdown option that stands in for "not in the list" — picking it is what
 * reveals the free-typed "New OEM Name" field below (see showNewOemName/optionsForSpec). Any real
 * manufacturer pick keeps "New OEM Name" hidden (and its control removed from addForm entirely). */
const NEW_OEM_NAME_OPTION = "Not Listed – Add New OEM";

function isNewOemNameSpec(s: ActionFieldSpec): boolean {
  return s.name === "New OEM Name";
}

/** Same "not in the list" sentinel idea as NEW_OEM_NAME_OPTION, for CAT III's "Supplier Name"
 * dropdown / "New OEM Supplier Name" field pair. */
const NEW_OEM_SUPPLIER_OPTION = "Not Listed – Add New Supplier";

function isNewOemSupplierNameSpec(s: ActionFieldSpec): boolean {
  return s.name === "New OEM Supplier Name";
}

/** Deck No, Location and Frame Station are never hand-typed — they're resolved from the picked
 * Compartment's own master record (`onCompartmentPicked`/`loadCompartmentCascade`), same across
 * every category (CAT I/II/III, Survey & Demand, Local Purchase all share this field set). */
function isAutoFetchedField(name: string): boolean {
  return /^Deck No$|^Location$|^Frame Station$/i.test(name);
}

/** Any CMMS-sourced field other than the Equipment/System Name pick itself (which is what
 * *triggers* the cascade — everything else here is a cascade *result*: Model, OEM Name, Supplier,
 * OEM Part No, Shelf Life, Sub Department, and — for Survey & Demand/Local Purchase specifically,
 * where it's equipment-cascade-derived rather than its own separate pick — Compartment Name too.
 * By explicit product direction these render as locked, auto-filled displays once Equipment Name
 * is picked, rather than the still-clickable dropdowns v1 leaves them as. Add mode only: in
 * Update mode this is superseded by isFieldEditable()'s own "only Compartment Name/Sub Department
 * stay editable" rule (CAT I/II/III's own Compartment Name has source "Ship Master", not "CMMS" —
 * it's the trigger for its own separate cascade (onCompartmentPicked) and must stay interactive
 * in both modes).
 *
 * Nomenclature is deliberately excluded — unlike the rest, one equipment can have several
 * distinct nomenclatures across its fitted history, so it stays a normal pick (scoped to that
 * equipment's own nomenclatures, see pickedEquipmentUniversalId) rather than auto-filling; picking
 * one is what then resolves the specific record the rest of this cascade comes from (see
 * onNomenclaturePicked). */
function isCmmsCascadeLockedField(spec: ActionFieldSpec): boolean {
  return spec.source === "CMMS" && !/^(Equipment|System) Name$|^Nomenclature$/.test(spec.name);
}

/**
 * SFD Actions screen — the core SFD workflow. Switches between the active-record
 * list (with working filters), the category-driven dynamic Add/Update form, the
 * 3-stage equipment Remove wizard, a Record Edit modal (update/change-serial),
 * an Equipment History drawer, and the read-only Deleted/Approval lists.
 * Mock data only — all submissions are simulated via toast, matching the SFD
 * prototype's "no real persistence" behavior.
 */
@Component({
  selector: "app-sfd-management",
  standalone: true,
  imports: [
    NgTemplateOutlet,
    ReactiveFormsModule,
    FormsModule,
    DataGrid,
    StatusChip,
    InputField,
    SelectInput,
    DatePickerComponent,
    ModalComponent,
    DetailDrawer,
    TextareaInput,
    IconComponent,
  ],
  templateUrl: "./sfd-management.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrls: ["./sfd-management.component.css"],
})
export class SfdManagementComponent implements OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly networkStatus = inject(NetworkStatusService);
  private readonly sfdActions = inject(SfdActionsService);
  private readonly notification = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly addFormDraft = inject(SfdAddFormDraftService);

  // Consumed once by the form-rebuild effect right after it recreates `addForm` for a restored
  // draft's category/type — see the constructor and effect A below.
  private pendingDraftFormValues: Record<string, unknown> | null = null;

  // Preserves the "R|H (Running Hours) as on date" value across a No-then-Yes-again toggle of
  // "Enter R|H for SRAR return" — see effect B below.
  private cachedRhValue = "";

  readonly view = signal<MgmtView>("list");

  /** "View Full Form" from a Returned/Change Approval Tracking request — shows the exact same
   * category-driven add/edit form (sfdFormTemplate, shared via ngTemplateOutlet) as a modal on top
   * of whatever view() is currently showing, instead of navigating away from it. See
   * openFullFormFromApproval/closeFullFormModal, and back()/submitAdd()'s branches on this flag. */
  readonly fullFormModalOpen = signal(false);

  readonly categories = SFD_CATEGORIES;

  // --- Live reference data (backs every dropdown in the Add/Update form) --------------------
  readonly referenceData = signal<SfdActionReferenceData | null>(null);

  readonly liveOptionSets = computed<OptionSetMap>(() => {
    const ref = this.referenceData();
    if (!ref) return {};
    // Every dropdown's value is its display LABEL, not a universal_id/PK — SfdActionsService
    // resolves the label back to the real join key (universal_id_*, or compartment_id) inside
    // buildActionPayload, keeping that backend-specific lookup logic out of this component.
    return {
      equipment: ref.equipment.map((e) => ({ label: e.label, value: e.label })),
      model: ref.models.map((m) => ({ label: m.label, value: m.label })),
      nomenclature: ref.nomenclatures.map((n) => ({ label: n.label, value: n.label })),
      oem: ref.manufacturers.map((m) => ({ label: m.label, value: m.label })),
      supplier: ref.suppliers.map((s) => ({ label: s.label, value: s.label })),
      oemPart: Array.from(new Set(ref.oemPartNumbers.map((p) => p.label))).map((p) => ({ label: p, value: p })),
      compartment: ref.compartments.map((c) => ({ label: c.name, value: c.name })),
      shelfLife: ref.shelfLives.map((s) => ({ label: `${s}`, value: s })),
      section: ref.equipmentSections.map((s) => ({ label: s.label, value: s.label })),
      type: ref.equipmentTypes.map((t) => ({ label: t.label, value: t.label })),
    };
  });

  // --- Active list --------------------------------------------------------
  // Backed by the real, paginated `GET sfd-list/`. `category`/`type` are now real fields on each
  // row, so Update correctly routes to the category the record was actually created under. A few
  // display-only `SfdActionRow` fields still have no backend equivalent (no INSMA code, no
  // maintop name): `code` falls back to the numeric `equipment_ship_id`, `maintop` to the raw
  // `maintop_id`.
  readonly sfdRows = signal<SfdActionRow[]>([]);
  readonly listCount = computed(() => this.sfdRows().length);
  readonly activeTotalCount = signal(0);
  readonly activePageSize = signal(10);
  readonly activePage = signal(1);

  private mapRawRowToDisplayRow(row: RawEquipmentTransactionRow, ref: SfdActionReferenceData | null): SfdActionRow {
    const equipmentMatch = ref?.equipment.find((e) => e.universalId === row.universal_id_m_equipment);
    const sectionMatch = ref?.equipmentSections.find((s) => s.universalId === row.universal_id_m_sub_department);
    const typeMatch = ref?.equipmentTypes.find((t) => t.universalId === row.universal_id_ch_master_equipment_type);
    // Model has no direct field on `GET sfd-list/` (unlike oem_part_no below) — it only resolves
    // via reference data, keyed by the SAME universal_id_m_equipment as the picked Equipment/System
    // (see SfdActionReferenceData.models / the identical onEquipmentPicked() cascade in the Add form).
    const modelMatch = ref?.models.find((m) => m.universalId === row.universal_id_m_equipment);
    // Manufacturer (OEM Name) / Supplier are each transaction's OWN pick, not the equipment's — so
    // they resolve against the row's own universal_id_m_manufacturer/universal_id_m_supplier, not
    // universal_id_m_equipment.
    const manufacturerMatch = ref?.manufacturers.find((m) => m.universalId === row.universal_id_m_manufacturer);
    const supplierMatch = ref?.suppliers.find((s) => s.universalId === row.universal_id_m_supplier);
    // For an EQUIPMENT-type row, "System Name" means "which system is this equipment part of" — a
    // separate parent link (`universal_id_m_equipment_parent`), not the row's own type. Only a
    // SYSTEM-type row's "system" is the record itself (its own display name).
    const systemParentMatch = ref?.systems.find((s) => s.universalId === row.universal_id_m_equipment_parent);
    const displayName =
      equipmentMatch?.label || row.new_equipment_name || row.new_system_name || row.nomenclature || "—";

    return {
      code: String(row.equipment_ship_id),
      name: displayName,
      nomen: row.nomenclature ?? "",
      dept: sectionMatch?.label ?? "—",
      qty: row.no_of_fits ?? 0,
      maintop: row.maintop_id != null ? String(row.maintop_id) : "—",
      serial: row.equipment_sr_no ?? "",
      cat: categoryFromBodyValue(row.category),
      system: row.type === "system" ? displayName : systemParentMatch?.label || row.new_system_name || "",
      // "new_*" fallbacks cover CAT III (New Induction), where these are free-text fields instead
      // of CMMS picks — same fallback pattern already used above for `displayName`.
      model: modelMatch?.label ?? "",
      oem: manufacturerMatch?.label || row.new_manufacturer_name || "",
      supplier: supplierMatch?.label || row.new_supplier_name || "",
      part: row.oem_part_no || row.new_oem_part_no || "",
      deck: row.deck_no ?? "",
      frame: row.frame_station ?? "",
      location: row.location_code ?? "",
      compartment: row.location_on_board ?? "",
      installDate: row.installation_date ?? "",
      authority: row.authority_of_installation ?? "",
      authorityDate: row.authority_date ?? "",
      shelfLife: row.service_life != null ? String(row.service_life) : "",
      rh: row.rh_at_installation != null ? String(row.rh_at_installation) : "",
      section: sectionMatch?.label ?? "",
      type: typeMatch?.label ?? "",
      isSystemRecord: row.type === "system",
    };
  }

  /** Equipment Name/Nomenclature/Sub Dept/Maintop as `sfd-list/` query params — only the ones
   * currently applied, since the backend treats an omitted param as "don't filter on this". */
  private activeListFilterParams(): Partial<Record<SfdListFilterParamKey, string>> {
    const filters = this.actFilters();
    const params: Partial<Record<SfdListFilterParamKey, string>> = {};
    for (const f of ACTION_FILTER_DEFS) {
      const v = filters[f.name];
      if (v) params[f.paramKey] = v;
    }
    return params;
  }

  async loadActiveList(page = 1, pageSize = this.activePageSize()): Promise<void> {
    try {
      const response = await this.sfdActions.loadTransactionList({
        page,
        page_size: pageSize,
        ...this.activeListFilterParams(),
      });
      const ref = this.referenceData();
      this.sfdRows.set(response.results.map((row) => this.mapRawRowToDisplayRow(row, ref)));
      this.activeTotalCount.set(response.count);
      this.activePage.set(page);
      this.activePageSize.set(pageSize);
    } catch (err) {
      console.error("[SfdActions] sfd-list/ failed — no SFD rows will be shown", err);
      this.sfdRows.set([]);
      this.activeTotalCount.set(0);
    }
  }

  onActiveListPageRequested(event: { page: number; pageSize: number }): void {
    this.loadActiveList(event.page, event.pageSize);
  }

  readonly actFiltersOpen = signal(false);
  readonly actFilters = signal<Record<string, string>>({});
  readonly actFilterOptions = signal<SfdListFilterOptions | null>(null);
  readonly searchTerm = signal("");

  private static readonly SEARCH_ROW_KEYS: (keyof SfdActionRow)[] = [
    "code",
    "name",
    "nomen",
    "dept",
    "maintop",
    "serial",
  ];

  /** Equipment Name/Nomenclature/Sub Dept/Maintop are now applied server-side (see
   * `loadActiveList`) — `sfdRows()` already reflects them, so only the free-text search box still
   * needs a client-side pass. */
  readonly filteredSfdRows = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return this.sfdRows();
    return this.sfdRows().filter((row) =>
      SfdManagementComponent.SEARCH_ROW_KEYS.some((key) => String(row[key] ?? "").toLowerCase().includes(term)),
    );
  });

  /** Option lists come from `sfd-list/filter-options/` (the full active dataset), not whatever
   * page happens to be loaded in the grid — otherwise a value that exists but isn't on the
   * current page could never be selected as a filter. */
  readonly actFilterFields = computed(() => {
    const filters = this.actFilters();
    const opts = this.actFilterOptions();
    return ACTION_FILTER_DEFS.map((f) => ({
      name: f.name,
      value: filters[f.name] ?? "",
      placeholder: `Select ${f.name}`,
      options: (opts?.[f.paramKey] ?? []).map((o): DropdownOption => ({ label: o.label, value: o.value })),
    }));
  });

  readonly actAppliedCount = computed(
    () => ACTION_FILTER_DEFS.filter((f) => !!this.actFilters()[f.name]).length,
  );
  readonly actHasFilters = computed(() => this.actAppliedCount() > 0);

  toggleActFilters(): void {
    this.actFiltersOpen.update((v) => !v);
  }

  setActFilter(name: string, value: FilterValue): void {
    this.actFilters.update((f) => ({ ...f, [name]: value ? String(value) : "" }));
    this.loadActiveList(1, this.activePageSize());
  }

  setSearchTerm(value: string): void {
    this.searchTerm.set(value);
  }

  clearActFilters(): void {
    this.actFilters.set({});
    this.searchTerm.set("");
    this.loadActiveList(1, this.activePageSize());
  }

  readonly sfdCols = [
    { headerName: "INSMA Code", field: "code", flex: 1, minWidth: 130, cellStyle: { color: "#4AA8FF", fontWeight: 600 } },
    { headerName: "Equipment Name", field: "name", flex: 2, minWidth: 200 },
    { headerName: "Nomenclature", field: "nomen", flex: 1.2 },
    { headerName: "Sub Dept", field: "dept", flex: 1.5 },
    { headerName: "Qty", field: "qty", width: 90 },
    { headerName: "Maintop", field: "maintop", flex: 1 },
    {
      headerName: "Actions",
      width: 130,
      pinned: "right" as const,
      cellRenderer: ActionRendererComponent,
      cellStyle: { display: "flex", justifyContent: "center", alignItems: "center" },
      cellRendererParams: {
        actions: (r: SfdActionRow): GridAction[] => [
          {
            icon: "edit",
            label: "Update SFD — Edit this record's Ship Fit Definition",
            color: "#2563eb",
            action: () => this.openUpdate(r),
          },
          {
            icon: "delete",
            label: "Remove — Raise a removal request for this equipment",
            color: "#dc2626",
            action: () => this.confirmDeletePrompt(r),
          },
          // Hidden for now — keep for when Change Serial is re-enabled in the Actions grid.
          // {
          //   icon: "refresh",
          //   label: "Change Serial — Update the equipment's serial number",
          //   color: "#16a34a",
          //   action: () => this.openRecordEdit(r, "serial"),
          // },
        ],
      },
    },
  ];

  // --- Add / Update view --------------------------------------------------
  readonly sfdType = signal<SfdType | null>(null);
  readonly category = signal<SfdCategory | null>(null);
  readonly editRow = signal<SfdActionRow | null>(null);
  readonly checkVals = signal<Record<string, "Yes" | "No">>({});

  // `previewCategory`/`previewType` can resolve to the SAME value across an open/close cycle
  // (e.g. closing out of a real CAT I edit falls back to the CAT I *preview*) — plain signals only
  // notify dependents on an actual value change, so the form-rebuild effect wouldn't rerun on its
  // own and every typed value would still be sitting in `addForm`. This counter is bumped on every
  // openAdd()/openUpdate()/back() so effect A below always has something new to react to,
  // regardless of whether the category/type resolve to the same string.
  private readonly formGeneration = signal(0);

  /** Bumped after onEquipmentPicked()/onNomenclaturePicked() finish applying cascade values —
   * displayFields() reads this to force a recompute of isCmmsCascadeLockedField's per-field "did
   * the cascade actually find a value" check, since FormControl values themselves aren't signals
   * Angular would otherwise pick up. */
  private readonly cascadeTick = signal(0);

  /** Set on Equipment/System Name pick — scopes the Nomenclature dropdown to only that
   * equipment's own nomenclatures (see optionsForSpec), since one equipment can have several. */
  private readonly pickedEquipmentUniversalId = signal<string | null>(null);

  /** CAT I/II/III only: set once a Nomenclature pick resolves to a record with a known
   * compartment (see onNomenclaturePicked) — locks "Compartment Name" to that auto-filled value
   * the same way the other CMMS cascade fields lock, instead of leaving it open for
   * onCompartmentPicked's normal manual pick. */
  private readonly compartmentAutoMapped = signal(false);

  /** CAT III only: tracks "OEM Name"'s current value so displayFields()/the control-add effect
   * below can show "New OEM Name" only once the NEW_OEM_NAME_OPTION sentinel is picked — kept in
   * sync by subscribeCascadeHandlers (ongoing user picks) and re-seeded from the freshly
   * rebuilt/prefilled addForm inside the form-rebuild effect (covers Add/Update/draft-restore). */
  private readonly oemNameSelection = signal<string>("");
  private readonly showNewOemName = computed(() => this.oemNameSelection() === NEW_OEM_NAME_OPTION);

  // Preserves a typed "New OEM Name" value across a sentinel-then-real-OEM-then-sentinel-again
  // round trip — same cache-and-restore idea as cachedRhValue below.
  private cachedNewOemNameValue = "";

  /** CAT III only: same idea as oemNameSelection/showNewOemName above, for "Supplier Name" /
   * "New OEM Supplier Name". */
  private readonly supplierNameSelection = signal<string>("");
  private readonly showNewOemSupplierName = computed(
    () => this.supplierNameSelection() === NEW_OEM_SUPPLIER_OPTION,
  );
  private cachedNewOemSupplierNameValue = "";

  /** In Update mode, only Compartment Name / Sub Department stay editable — everything else is
   * locked to its existing value. Always true in Add mode (editRow is null there). */
  isFieldEditable(rawName: string): boolean {
    return !this.editRow() || rawName === "Compartment Name" || rawName === "Sub Department";
  }

  /** Update mode only: Compartment Name / Sub Department get an accent-highlighted border so the
   * two fields that stay editable are unmistakable next to every other, now-locked field. Add mode
   * never highlights — every field is already editable there, so nothing needs to stand out. */
  isFieldHighlightedEditable(rawName: string): boolean {
    return !!this.editRow() && (rawName === "Compartment Name" || rawName === "Sub Department");
  }

  /** Editing an existing record: its category came straight from the API (row.cat) and is fixed —
   * every OTHER category locks immediately, no interaction needed. Add mode is more lenient: a
   * category only locks the others once the user has actually started filling the form in
   * (`addForm.dirty` only flips from real user interaction — Update mode's own prefill via
   * patchValue() doesn't set it, which is exactly why Update needs the separate editRow() check). */
  isCategoryLocked(id: SfdCategory): boolean {
    if (this.category() === null || this.category() === id) return false;
    return !!this.editRow();
  }

  // Flips true the first time Submit is clicked on the current Add/Update form. Before that, a
  // blank mandatory field only shows a red PLACEHOLDER (see fieldPlaceholderInvalid()) — the full
  // error treatment (red border + inline message) only appears once a submit has actually failed.
  readonly submitAttempted = signal(false);

  /** Live red-placeholder-only check for a dynamic `addForm` field — true the moment it's blank
   * and required, regardless of whether the user has touched it or clicked Submit. */
  fieldPlaceholderInvalid(key: string): boolean {
    const control = this.addForm.get(key);
    return !!control && control.invalid;
  }

  /** Full red-border + inline-message check — only once Submit has been clicked and failed. */
  fieldInvalid(key: string): boolean {
    return this.submitAttempted() && this.fieldPlaceholderInvalid(key);
  }

  /** frameFromControl/frameToControl live outside addForm, so they need their own required-check
   * (mirrors the blank-check in submitAdd()) instead of Angular's built-in control validity. */
  private frameNumericValue(value: string): number | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const n = Number(trimmed);
    return Number.isFinite(n) ? n : null;
  }

  /** True when this ONE field (From or To), taken alone, is a problem: required-but-blank, or a
   * zero/negative number. The "To must be > From" relational rule is separate — see frameRangeOrder*.
   * Locked (Update mode, disabled) never flags — an existing value the user can't touch isn't an error. */
  frameFieldBlank(value: string): boolean {
    if (this.frameFromControl.disabled) return false;
    if (!value.trim()) return !!this.frameRangeFieldSpec()?.required;
    const n = this.frameNumericValue(value);
    return n !== null && n <= 0;
  }

  frameFieldInvalid(value: string): boolean {
    return this.submitAttempted() && this.frameFieldBlank(value);
  }

  /** True only once both From/To are valid positive numbers but To is LESS than From (equal is
   * fine — a single-frame station) — doesn't fire while either side is still blank/zero/negative,
   * since frameFieldBlank() already flags those individually. */
  frameRangeOrderBlank(): boolean {
    if (this.frameFromControl.disabled) return false;
    const from = this.frameNumericValue(this.frameFromControl.value);
    const to = this.frameNumericValue(this.frameToControl.value);
    if (from === null || to === null || from <= 0 || to <= 0) return false;
    return to < from;
  }

  frameRangeOrderInvalid(): boolean {
    return this.submitAttempted() && this.frameRangeOrderBlank();
  }

  /** serialControl also lives outside addForm — same reasoning as frameFieldBlank()/Invalid(). */
  serialRequiredBlank(): boolean {
    if (this.serialControl.disabled) return false;
    return !!this.serialFieldSpec()?.required && !this.serialValue().trim();
  }

  serialRequiredInvalid(): boolean {
    return this.submitAttempted() && this.serialRequiredBlank();
  }

  // "Updating existing SFD record" banner — shown for a few seconds only, not for the whole
  // edit session (editRow itself must stay populated the whole time for form prefill).
  readonly showEditingBanner = signal(false);
  private editingBannerTimer: ReturnType<typeof setTimeout> | undefined;

  private flashEditingBanner(): void {
    clearTimeout(this.editingBannerTimer);
    this.showEditingBanner.set(true);
    this.editingBannerTimer = setTimeout(() => this.showEditingBanner.set(false), 6000);
  }

  private clearEditingBanner(): void {
    clearTimeout(this.editingBannerTimer);
    this.showEditingBanner.set(false);
  }

  readonly serialControl = new FormControl("", { nonNullable: true });
  readonly serialValue = signal("");
  readonly netOnline = this.networkStatus.online;

  readonly frameFromControl = new FormControl("", { nonNullable: true });
  readonly frameToControl = new FormControl("", { nonNullable: true });

  readonly historyDrawerOpen = signal(false);
  readonly historyDrawerStats: DrawerStat[] = EQUIPMENT_HISTORY_STATS.map((s) => ({
    value: s.value,
    label: s.label,
    color: s.tone ? TONE_COLOR[s.tone] : undefined,
  }));
  readonly historySections = EQUIPMENT_HISTORY_SECTIONS;

  addForm: FormGroup = this.fb.group({});

  // Before the user picks Equipment/System, "Add SFD" shows a disabled preview of the CAT I /
  // Equipment form (see `mgmt__section--disabled` in the template) so the page doesn't look empty.
  // The CAT I fallback only applies while `sfdType` itself is still null (the untouched landing
  // state) — once a real Transaction Type is picked, this behaves exactly as before: no fields
  // until a category is actually clicked. The real `sfdType`/`category` signals always stay
  // `null` until clicked, so neither radio renders as selected and submission stays correctly gated.
  readonly previewType = computed<SfdType>(() => this.sfdType() ?? "Equipment");
  readonly previewCategory = computed<SfdCategory | null>(
    () => this.category() ?? (this.sfdType() ? null : "CAT I"),
  );

  readonly activeCategoryCard = computed(() => {
    const cat = this.previewCategory();
    return cat ? this.categories.find((c) => c.id === cat) ?? null : null;
  });

  private readonly categorySpecs = computed<ActionFieldSpec[]>(() => {
    const cat = this.previewCategory();
    return cat ? FIELD_SPECS[cat] : [];
  });

  private readonly rhCheckboxSpec = computed<ActionFieldSpec | null>(
    () => this.categorySpecs().find((s) => s.type === "Checkbox") ?? null,
  );

  private readonly rhFieldSpec = computed<ActionFieldSpec | null>(
    () => this.categorySpecs().find(isRhSpec) ?? null,
  );

  readonly serialFieldSpec = computed<ActionFieldSpec | null>(
    () => this.categorySpecs().find(isSerialSpec) ?? null,
  );

  /** frameFromControl/frameToControl live outside addForm (see the constructor's control-building
   * loop), so Validators.required on the spec can't reach them — this drives its own blank-check. */
  private readonly frameRangeFieldSpec = computed<ActionFieldSpec | null>(
    () => this.categorySpecs().find(isFrameRangeSpec) ?? null,
  );

  private readonly rhVisible = computed(() => {
    const spec = this.rhCheckboxSpec();
    return !spec || this.checkVals()[spec.name] === "Yes";
  });

  readonly showAvail = computed(
    () => !!this.serialFieldSpec() && this.serialValue().trim().length >= 3 && this.netOnline(),
  );
  readonly showUnavail = computed(
    () => !!this.serialFieldSpec() && this.serialValue().trim().length >= 3 && !this.netOnline(),
  );
  readonly showHistoryOffline = this.showUnavail;

  readonly effectiveHistoryOpen = computed(() => this.historyDrawerOpen() && this.showAvail());
  readonly historyValue = computed(() => this.serialValue().trim() || "—");

  readonly displayFields = computed<DisplayField[]>(() => {
    const type = this.previewType();
    const specs = this.categorySpecs();
    if (!specs.length) return [];

    const rhVisible = this.rhVisible();
    const newOemNameVisible = this.showNewOemName();
    const newOemSupplierNameVisible = this.showNewOemSupplierName();
    this.cascadeTick();

    const fields: DisplayField[] = specs
      .filter((s) => !(isRhSpec(s) && !rhVisible))
      .filter((s) => !(isNewOemNameSpec(s) && !newOemNameVisible))
      .filter((s) => !(isNewOemSupplierNameSpec(s) && !newOemSupplierNameVisible))
      .map((s) => this.toDisplayField(s, type));

    if (type === "Equipment") {
      // Sourced from the SAME `system_name` list (`ref.systems`) as the Equipment Name cascade in
      // onEquipmentPicked() sets this field's value from — options must come from that same list,
      // not a fixed picklist, or the picked value can't match any option and the dropdown renders
      // as unselected even though the underlying FormControl is actually set correctly.
      const sysField: DisplayField = {
        key: "sysName",
        rawName: "System Name",
        label: "System Name",
        required: true,
        badge: "CMMS",
        badgeColor: "#F59E0B",
        placeholder: "Select System Name",
        kind: "select",
        options: this.referenceData()?.systems.map((s) => ({ label: s.label, value: s.label })) ?? [],
        readonly: false,
      };
      const idx = fields.findIndex((f) => /^(Equipment|System) Name$/.test(f.rawName));
      if (idx >= 0) fields.splice(idx + 1, 0, sysField);
      else fields.unshift(sysField);
    }

    return fields;
  });

  constructor() {
    // Restore an in-progress Add/Update draft left behind by a previous instance of this
    // component — e.g. the user switched to another Ship Configuration tab (or used browser
    // back/forward) while mid-form, which destroys and recreates this component from scratch.
    // sfdType/category/checkVals must be set here, before the effects below are registered, so
    // their first run already sees the restored values; the raw control values are stashed and
    // applied once that first run has rebuilt `addForm` to match.
    const draft = this.addFormDraft.peek();
    if (draft) {
      this.editRow.set(draft.editRow);
      this.checkVals.set(draft.checkVals);
      this.serialControl.setValue(draft.serialValue);
      this.frameFromControl.setValue(draft.frameFrom);
      this.frameToControl.setValue(draft.frameTo);
      this.pendingDraftFormValues = draft.formValues;
      this.sfdType.set(draft.sfdType);
      this.category.set(draft.category);
      this.view.set("add");
      if (draft.editRow) this.flashEditingBanner();
    }

    this.route.queryParams.pipe(takeUntilDestroyed()).subscribe(params => {
      if (params['view'] === 'add') {
        // Deep-linked from the SFD Overview "Add / Update SFD" quick action — when a
        // Transaction Type (+ category) is supplied, open the Add form with them already
        // selected instead of the blank CAT I / Equipment preview.
        const type = params['type'];
        if (type === 'Equipment' || type === 'System') {
          this.addFormDraft.clear();
          this.editRow.set(null);
          this.submitAttempted.set(false);
          this.sfdType.set(type);
          this.category.set(categoryFromSlug(params['category']));
          this.checkVals.set({});
          this.serialControl.setValue('');
          this.frameFromControl.setValue('');
          this.frameToControl.setValue('');
          this.formGeneration.update((n) => n + 1);
        }
        this.view.set('add');
      } else if (params['view'] === 'approval') {
        this.viewApproval();
      }
    });
    effect(() => {
      const cat = this.previewCategory();
      const type = this.previewType();
      this.formGeneration(); // tracked on purpose — see the field comment above its declaration
      const rhVisible = untracked(() => this.rhVisible());
      const specs = cat ? FIELD_SPECS[cat].filter((s) => rhVisible || !isRhSpec(s)) : [];

      this.addForm = this.fb.group(this.buildControlsForSpecs(specs, type, cat));
      this.cachedRhValue = ""; // a genuinely new category/type shape — don't leak the old one's R|H value
      this.cachedNewOemNameValue = ""; // same — don't leak the old form's "New OEM Name" text either
      this.cachedNewOemSupplierNameValue = ""; // same — for "New OEM Supplier Name"
      this.applyPrefillIfEditing();
      this.applyPendingDraftFormValues();
      // Seeds showNewOemName()/showNewOemSupplierName() off the freshly built/prefilled/draft-restored
      // "OEM Name"/"Supplier Name" values — subscribeCascadeHandlers below only picks up value
      // changes from here on, not this initial state.
      this.oemNameSelection.set(String(this.addForm.get(controlKey("OEM Name"))?.value ?? ""));
      this.supplierNameSelection.set(String(this.addForm.get(controlKey("Supplier Name"))?.value ?? ""));

      // Editing an existing record: only Compartment Name / Sub Department stay editable — every
      // other field is locked to its prefilled value. Add mode is untouched (editRow is null there).
      this.applyEditLockdown(specs);

      // Cascading dropdowns via GET get_equipment/ (see SfdActionsService.loadEquipmentCascade /
      // loadCompartmentCascade) — picking an Equipment/System or a Compartment fetches the CMMS
      // values tied to it. Subscribed per rebuilt form since `addForm` is replaced on every
      // category/type change; the old controls are discarded along with their subscriptions.
      this.subscribeCascadeHandlers();
    });

    // Toggling "Enter R|H for SRAR return" (Yes/No) only adds/removes the R|H control in place on
    // the CURRENT form instance — it never rebuilds `addForm` — so every other field the user has
    // already filled in stays exactly as-is. The R|H control's OWN value is cached across a
    // No-then-Yes-again round trip too (`cachedRhValue`), instead of coming back blank.
    effect(() => {
      const spec = this.rhFieldSpec();
      const visible = this.rhVisible();
      if (!spec) return;
      const key = controlKey(spec.name);
      if (visible) {
        if (!this.addForm.contains(key)) {
          // Reaching here means the "Enter/Add R|H for SRAR return" toggle is Yes, so this value
          // is always mandatory while shown — `spec.required` is unconditionally false in
          // FIELD_SPECS since visibility itself already gates the "No" case (see toDisplayField).
          this.addForm.addControl(key, new FormControl(this.cachedRhValue, [Validators.required]));
        }
      } else {
        const existing = this.addForm.get(key);
        if (existing) {
          this.cachedRhValue = String(existing.value ?? "");
          this.addForm.removeControl(key);
        }
      }
    });

    // CAT III only: "New OEM Name" only makes sense once "OEM Name" is set to the "not in the
    // list" sentinel (NEW_OEM_NAME_OPTION) — same add/remove-control-in-place pattern as the R|H
    // toggle above, so the field neither renders nor blocks submission with a stale required
    // validator while hidden, and a typed value survives a sentinel → real OEM → sentinel round trip.
    effect(() => {
      const spec = this.categorySpecs().find(isNewOemNameSpec) ?? null;
      if (!spec) return;
      const key = controlKey(spec.name);
      const visible = this.showNewOemName();
      if (visible) {
        if (!this.addForm.contains(key)) {
          this.addForm.addControl(
            key,
            new FormControl(
              { value: this.cachedNewOemNameValue, disabled: !this.isFieldEditable(spec.name) },
              [Validators.required],
            ),
          );
        }
      } else {
        const existing = this.addForm.get(key);
        if (existing) {
          this.cachedNewOemNameValue = String(existing.value ?? "");
          this.addForm.removeControl(key);
        }
      }
    });

    // Same idea as the "New OEM Name" effect above, for "New OEM Supplier Name" once "Supplier
    // Name" is set to NEW_OEM_SUPPLIER_OPTION.
    effect(() => {
      const spec = this.categorySpecs().find(isNewOemSupplierNameSpec) ?? null;
      if (!spec) return;
      const key = controlKey(spec.name);
      const visible = this.showNewOemSupplierName();
      if (visible) {
        if (!this.addForm.contains(key)) {
          this.addForm.addControl(
            key,
            new FormControl(
              { value: this.cachedNewOemSupplierNameValue, disabled: !this.isFieldEditable(spec.name) },
              [Validators.required],
            ),
          );
        }
      } else {
        const existing = this.addForm.get(key);
        if (existing) {
          this.cachedNewOemSupplierNameValue = String(existing.value ?? "");
          this.addForm.removeControl(key);
        }
      }
    });

    this.serialControl.valueChanges.pipe(takeUntilDestroyed()).subscribe((v) => {
      this.serialValue.set(v);
    });

    this.initializeActiveList();
  }

  /** The Active list request and reference-data request race — if the list comes back first, every
   * row's model/OEM Name/Supplier/Sub Dept/Equipment Type (all reference-data lookups) render blank
   * since `mapRawRowToDisplayRow` had nothing to join against yet. Re-map once reference data
   * actually lands so those columns correct themselves instead of staying blank until some unrelated
   * page change happens to trigger a fresh loadActiveList(). Extracted out of the constructor body
   * so the async calls aren't written directly inline there. */
  private initializeActiveList(): void {
    this.sfdActions.loadReferenceData().then((ref) => {
      this.referenceData.set(ref);
      this.loadActiveList(this.activePage(), this.activePageSize());
    });
    this.sfdActions.loadSfdListFilterOptions().then((opts) => this.actFilterOptions.set(opts));
    this.loadActiveList();
  }

  /** Builds the per-field controls for the currently-previewed category/type shape (extracted from
   * the form-rebuild effect purely to keep that effect's own cognitive complexity down). */
  private buildControlsForSpecs(
    specs: ActionFieldSpec[],
    type: SfdType,
    cat: SfdCategory | null,
  ): Record<string, FormControl> {
    const controls: Record<string, FormControl> = {};
    for (const s of specs) {
      if (
        s.type === "Checkbox" ||
        isSerialSpec(s) ||
        isFrameRangeSpec(s) ||
        isNewOemNameSpec(s) ||
        isNewOemSupplierNameSpec(s)
      )
        continue;
      // "Auto Fetch" fields still get a real control — they're populated by onEquipmentPicked()'s
      // cascade and need to participate in getRawValue() for the submit payload, same as any other
      // field. The template renders them read-only since the source badge is CMMS, not user entry.
      controls[controlKey(s.name)] = new FormControl("", s.required ? [Validators.required] : []);
    }
    if (type === "Equipment" && cat) {
      controls["sysName"] = new FormControl("", [Validators.required]);
    }
    return controls;
  }

  /** Applies a draft restored on this instance's construction (see the constructor's draft-restore
   * block) to the freshly-rebuilt `addForm`, once. */
  private applyPendingDraftFormValues(): void {
    if (!this.pendingDraftFormValues) return;
    this.addForm.patchValue(this.pendingDraftFormValues);
    this.pendingDraftFormValues = null;
  }

  /** Editing an existing record: only Compartment Name / Sub Department stay editable — every other
   * field is locked to its prefilled value. Add mode is untouched (editRow is null there). */
  private applyEditLockdown(specs: ActionFieldSpec[]): void {
    if (!this.editRow()) return;
    for (const s of specs) {
      if (s.type === "Checkbox" || isSerialSpec(s) || isFrameRangeSpec(s)) continue;
      if (!this.isFieldEditable(s.name)) {
        this.addForm.get(controlKey(s.name))?.disable();
      }
    }
    this.addForm.get("sysName")?.disable();
  }

  /** Cascading dropdowns via GET get_equipment/ (see SfdActionsService.loadEquipmentCascade /
   * loadCompartmentCascade) — picking an Equipment/System or a Compartment fetches the CMMS values
   * tied to it. Subscribed per rebuilt form since `addForm` is replaced on every category/type
   * change; the old controls are discarded along with their subscriptions. */
  private subscribeCascadeHandlers(): void {
    this.addForm
      .get(controlKey("Equipment Name"))
      ?.valueChanges.subscribe((label: string) => this.onEquipmentPicked(label));
    this.addForm
      .get(controlKey("Nomenclature"))
      ?.valueChanges.subscribe((label: string) => this.onNomenclaturePicked(label));
    this.addForm
      .get(controlKey("Compartment Name"))
      ?.valueChanges.subscribe((label: string) => this.onCompartmentPicked(label));
    this.addForm
      .get(controlKey("OEM Name"))
      ?.valueChanges.subscribe((label: string) => this.oemNameSelection.set(label ?? ""));
    this.addForm
      .get(controlKey("Supplier Name"))
      ?.valueChanges.subscribe((label: string) => this.supplierNameSelection.set(label ?? ""));
  }

  /** Save the in-progress Add/Update form as a draft when this component is torn down mid-edit
   * (tab switch, browser back/forward) — restored by the constructor above if the user comes
   * back. Deliberately NOT cleared here; only an explicit abandon ("Back to List") or a
   * successful submit should drop a draft. */
  ngOnDestroy(): void {
    if (this.view() !== "add") return;
    this.addFormDraft.save({
      sfdType: this.sfdType(),
      category: this.category(),
      checkVals: this.checkVals(),
      formValues: this.addForm.getRawValue(),
      serialValue: this.serialValue(),
      frameFrom: this.frameFromControl.value,
      frameTo: this.frameToControl.value,
      editRow: this.editRow(),
    });
  }

  /**
   * Equipment/System pick — Model and OEM Part No are keyed by the SAME `universal_id_m_equipment`
   * as the pick, so they resolve instantly from the already-loaded dropdown data. Everything else
   * that used to come from this pick (OEM Name, Supplier, Shelf Life, System Name's mapping lock,
   * and — for Survey & Demand/Local Purchase — Equipment Serial No/Deck No/Frame Station/Location/
   * Compartment Name/Installation Date/Installation Remarks/Qty Fitted/Sub Department) now waits
   * for {@link onNomenclaturePicked} instead: an equipment can have several distinct nomenclatures
   * across its fitted history, so a specific record can't be resolved from the equipment alone.
   * This pick's only other job is scoping the Nomenclature dropdown to this equipment's own
   * nomenclatures (see pickedEquipmentUniversalId/optionsForSpec).
   */
  private async onEquipmentPicked(label: string): Promise<void> {
    // CAT III's "Equipment Name" is free-typed (new equipment, nothing in CMMS to match against
    // yet) — Model/Nomenclature/OEM Part No are all separately free-typed/user-picked there too,
    // so none of this equipment-match cascade applies; every keystroke would otherwise clear them.
    if (this.category() === "CAT III") return;

    const ref = this.referenceData();
    const isSystem = this.sfdType() === "System";
    const matchList = isSystem ? ref?.systems : ref?.equipment;
    const match = label ? matchList?.find((e) => e.label === label) : undefined;

    this.pickedEquipmentUniversalId.set(match?.universalId ?? null);
    // Whatever Nomenclature used to be picked no longer applies to the newly (un)picked equipment
    // — clearing it also clears everything onNomenclaturePicked had cascaded from it (OEM Name/
    // Supplier/Shelf Life/Survey & Demand-Local Purchase's extra fields), but NOT System Name —
    // that's this pick's own job below, and stays put across nomenclature changes once set.
    this.addForm.get(controlKey("Nomenclature"))?.setValue("");

    if (!match) {
      this.setFormValue("Model", "");
      this.setFormValue("OEM Part No", "");
      const sysControl = this.addForm.get("sysName");
      sysControl?.enable();
      sysControl?.setValue("");
      this.cascadeTick.update((n) => n + 1);
      return;
    }

    const modelMatch = ref?.models.find((m) => m.universalId === match.universalId);
    this.setFormValue("Model", modelMatch?.label);

    const oemPartMatch = ref?.oemPartNumbers.find((p) => p.universalId === match.universalId);
    this.setFormValue("OEM Part No", oemPartMatch?.label);

    // Whether this equipment is already mapped to a system depends only on the equipment itself,
    // not which nomenclature ends up picked — resolved here (equipment-only, no nomenclature) so
    // it's set once and doesn't get re-evaluated (and potentially overwritten) on every
    // nomenclature change afterward.
    try {
      if (!isSystem && ref) {
        // This same catalog entry can itself double as a system (a separate CMMS classification
        // from the mapping check below) — pre-fills System Name with it before the mapping check
        // potentially overrides it with an actually-mapped system instead.
        const systemMatch = ref.systems.find((s) => s.universalId === match.universalId);
        if (systemMatch) this.addForm.get("sysName")?.setValue(systemMatch.label);

        const cascade = await this.sfdActions.loadEquipmentCascade(match.universalId);
        if (cascade) this.applyEquipmentMappingLock(cascade, ref);
      }
    } finally {
      this.cascadeTick.update((n) => n + 1);
    }
  }

  /**
   * Nomenclature pick — now that both the equipment and which of its nomenclatures are known, the
   * specific matching record can actually be resolved (`GET get_equipment/`, filtered by both).
   * OEM Name/Supplier/Shelf Life auto-fill from it if found; Survey & Demand/Local Purchase
   * additionally auto-fetch Equipment Serial No/Deck No/Frame Station/Location/Compartment Name/
   * Installation Date/Installation Remarks/Qty Fitted/Sub Department from that same response.
   * CAT I/II/III don't get those from here — Deck No/Frame Station/Location normally come from the
   * separate Compartment-pick cascade (`onCompartmentPicked`) — except Compartment Name itself,
   * which auto-fills and locks here too if this record already has one on record (an equipment
   * that's been fitted with this nomenclature before very likely goes in the same compartment
   * again), leaving the normal manual Compartment pick for whenever it doesn't.
   */
  private async onNomenclaturePicked(label: string): Promise<void> {
    // CAT III's "Nomenclature" is free-typed (new equipment, no CMMS history to pick from) — every
    // keystroke would otherwise fire this and wipe whatever OEM Name/Supplier/Shelf Life the user
    // already picked manually, none of which cascade from Nomenclature in this category at all.
    if (this.category() === "CAT III") return;

    const isSurveyOrLocalPurchase = this.category() === "Survey & Demand" || this.category() === "Local Purchase";
    const equipmentUid = this.pickedEquipmentUniversalId();

    if (!label || !equipmentUid) {
      this.clearNomenclatureCascadeFields(isSurveyOrLocalPurchase);
      return;
    }
    // Every path below has already applied whatever cascade values it could — bump this once
    // regardless of which one that ends up being, so displayFields() re-checks each CMMS field's
    // now-current value (see isCmmsCascadeLockedField's use in toDisplayField()).
    try {
      await this.applyNomenclaturePickedCascade(equipmentUid, label, isSurveyOrLocalPurchase);
    } finally {
      this.cascadeTick.update((n) => n + 1);
    }
  }

  private async applyNomenclaturePickedCascade(
    equipmentUid: string,
    nomenclature: string,
    isSurveyOrLocalPurchase: boolean,
  ): Promise<void> {
    const ref = this.referenceData();
    if (!ref) return;

    // System Name's mapping lock is resolved once, at Equipment pick (see onEquipmentPicked) —
    // deliberately NOT re-touched here, so a manually-picked System Name for an unmapped equipment
    // stays exactly as the user left it regardless of which Nomenclature they pick afterward.
    const cascade = await this.sfdActions.loadEquipmentCascade(equipmentUid, nomenclature);
    if (!cascade) return;

    if (cascade.oem_name_id) {
      const manufacturerMatch = ref.manufacturers.find((m) => m.universalId === cascade.oem_name_id);
      this.setFormValue("OEM Name", manufacturerMatch?.label);
    }
    if (cascade.supplier_id) {
      const supplierMatch = ref.suppliers.find((s) => s.universalId === cascade.supplier_id);
      this.setFormValue(supplierFieldName(this.category()), supplierMatch?.label);
    }
    if (cascade.shelf_life_id != null) {
      this.setFormValue("Shelf Life", cascade.shelf_life_id);
    }

    if (isSurveyOrLocalPurchase) {
      this.applySurveyOrLocalPurchaseCascade(cascade, ref);
    } else {
      this.applyCat123CompartmentCascade(cascade, ref);
    }
  }

  /** Equipment mode only: an already-installed equipment that's already mapped to a parent system
   *  (Configuration > System-Equipment Mapping) must keep that same system here — "System Name"
   *  locks to it instead of allowing a different one to be picked. An equipment with no mapping
   *  yet leaves "System Name" open for a normal pick; the backend maps this new record to
   *  whichever system is picked as part of creating it (see _create_sfd_transaction), so no extra
   *  step is needed here beyond letting the user choose. */
  private applyEquipmentMappingLock(cascade: CascadingDropdownValues, ref: SfdActionReferenceData): void {
    const sysControl = this.addForm.get("sysName");
    if (cascade.is_mapped && cascade.mapped_system_id) {
      const mappedSystem = ref.systems.find((s) => s.universalId === cascade.mapped_system_id);
      if (mappedSystem) {
        sysControl?.setValue(mappedSystem.label);
        sysControl?.disable();
      }
    } else {
      sysControl?.enable();
    }
  }

  /** CAT I/II/III only, called from {@link applyNomenclaturePickedCascade}: if this equipment +
   *  nomenclature has a compartment on record already, auto-fill and lock Compartment Name (and
   *  the Deck No/Frame Station/Location that come with it) the same way the rest of the CMMS
   *  cascade locks — see compartmentAutoMapped. Otherwise leaves Compartment Name exactly as
   *  onCompartmentPicked's normal manual pick already handles it. */
  private applyCat123CompartmentCascade(cascade: CascadingDropdownValues, ref: SfdActionReferenceData): void {
    // cascade.compartrment is free text off the matched ShipEquipment record (location_on_board)
    // — it won't always exactly match a real CompartmentMaster name. Locking the field on a value
    // that can't actually be selected leaves it looking blank AND uninteractive, with no way to
    // fill it in (the same dead-end class of bug as OEM Part No elsewhere in this cascade) — only
    // lock when it resolves to a real, pickable compartment.
    const compartmentMatch = ref.compartments.find((c) => c.name === cascade.compartrment);
    this.compartmentAutoMapped.set(!!compartmentMatch);
    if (!compartmentMatch) return;

    this.setFormValue("Compartment Name", compartmentMatch.name);
    this.setFormValue("Deck No", cascade.deck_no);
    if (cascade.location) {
      const locationMatch = LOCATION_OPTIONS.find((o) => o.value === cascade.location);
      this.setFormValue("Location", locationMatch?.label ?? cascade.location);
    }
    if (cascade.frame_station) {
      const [frameFrom, frameTo] = cascade.frame_station.split(/[–-]/);
      this.frameFromControl.setValue((frameFrom || "").trim());
      this.frameToControl.setValue((frameTo || "").trim());
    }
  }

  /** "X"-clear branch of {@link onNomenclaturePicked} — resets every field that cascades from a
   *  Nomenclature pick specifically. Leaves Equipment Name/Model/OEM Part No AND System Name
   *  untouched — the former don't depend on Nomenclature at all, and the latter is deliberately
   *  only ever set/reset by onEquipmentPicked (see its doc). */
  private clearNomenclatureCascadeFields(isSurveyOrLocalPurchase: boolean): void {
    const clear = (fieldName: string) => this.addForm.get(controlKey(fieldName))?.setValue("");
    clear("OEM Name");
    clear(supplierFieldName(this.category()));
    clear("Shelf Life");
    this.compartmentAutoMapped.set(false);
    this.cascadeTick.update((n) => n + 1);
    if (!isSurveyOrLocalPurchase) return;
    clear("Equipment Serial No");
    clear("Deck No");
    // Frame Station lives outside addForm (frameFromControl/frameToControl), same as CAT I/II/III
    // — clear() above is a no-op for it, unlike every other field in this list.
    this.frameFromControl.setValue("");
    this.frameToControl.setValue("");
    clear("Location");
    clear("Compartment Name");
    clear("Installation Date");
    clear("Installation Remarks");
    clear("Qty Fitted");
    clear("Sub Department");
  }

  /** Sets a cascaded form field only when the resolved value is present — leaves the existing
   *  input untouched otherwise (used throughout the Equipment/System-pick cascade). */
  private setFormValue(fieldName: string, value: unknown): void {
    if (value == null || value === "") return;
    this.addForm.get(controlKey(fieldName))?.setValue(value);
  }

  /** Survey & Demand / Local Purchase-only tail of {@link onEquipmentPicked} — Deck No / Frame
   *  Station / Location / Compartment Name / Installation Date / Installation Remarks / Qty
   *  Fitted / Sub Department, all sourced from the same `get_equipment/` cascade response. */
  private applySurveyOrLocalPurchaseCascade(cascade: CascadingDropdownValues, ref: SfdActionReferenceData): void {
    this.setFormValue("Equipment Serial No", cascade.equipment_sr_no);
    this.setFormValue("Deck No", cascade.deck_no);
    // Frame Station lives outside addForm (frameFromControl/frameToControl), same as CAT I/II/III's
    // Compartment-pick cascade (onCompartmentPicked) — get_equipment/ returns it as one combined
    // string ("74-82"), so split it the same way openUpdate() splits an existing row's `frame`.
    if (cascade.frame_station) {
      const [frameFrom, frameTo] = cascade.frame_station.split(/[–-]/);
      this.frameFromControl.setValue((frameFrom || "").trim());
      this.frameToControl.setValue((frameTo || "").trim());
    }
    // Auto Fetch renders as a plain read-only value (not a select), so unlike CAT I/II/III's
    // Location dropdown, this needs the human label resolved up front — the raw "1"-"4" code has
    // nowhere else to become "Port, Aft" for display.
    if (cascade.location) {
      const locationMatch = LOCATION_OPTIONS.find((o) => o.value === cascade.location);
      this.setFormValue("Location", locationMatch?.label ?? cascade.location);
    }
    this.setFormValue("Compartment Name", cascade.compartrment);
    this.setFormValue("Installation Date", formatCascadeDate(cascade.installation_date));
    this.setFormValue("Installation Remarks", cascade.installation_remarks);
    this.setFormValue("Qty Fitted", cascade.qty_fitted);
    if (cascade.sub_department) {
      const sectionMatch = ref.equipmentSections.find((s) => s.universalId === cascade.sub_department);
      this.setFormValue("Sub Department", sectionMatch?.label ?? cascade.sub_department);
    }
  }

  /** Compartment-mode cascade — deck/frame/location resolved from the picked compartment's own master record. */
  private async onCompartmentPicked(label: string): Promise<void> {
    if (!label) return;
    const match = this.referenceData()?.compartments.find((c) => c.name === label);
    if (!match) return;

    const cascade = await this.sfdActions.loadCompartmentCascade(match.id);
    if (!cascade) {
      // Previously a silent no-op — Deck No/Frame Station/Location would just sit unmapped with no
      // indication why, looking identical to "nothing happened yet". Surface it so the user knows to
      // fill those three in manually instead of assuming the pick didn't register.
      this.notification.error(
        "Couldn't fetch Deck No / Frame Station / Location for this compartment. Please fill them in manually.",
      );
      return;
    }
    if (cascade.deck_no) this.addForm.get(controlKey("Deck No"))?.setValue(cascade.deck_no);
    if (cascade.location_code) this.addForm.get(controlKey("Location"))?.setValue(cascade.location_code);
    if (cascade.frame_station_from) this.frameFromControl.setValue(cascade.frame_station_from);
    if (cascade.frame_station_to) this.frameToControl.setValue(cascade.frame_station_to);
  }

  private toDisplayField(
    spec: ActionFieldSpec,
    type: SfdType | null,
  ): DisplayField {
    // "Eqpt" is the Survey & Demand form's own abbreviation for "Equipment" (e.g. "New Eqpt Serial
    // Number", "Date of Installation (New Eqpt)") — swapped to "System" the same as the full word.
    const label =
      type === "System" ? spec.name.replaceAll("Equipment", "System").replaceAll("Eqpt", "System") : spec.name;
    // Deck No / Location / Frame Station are always Compartment-cascade-derived regardless of
    // category (name-based, since CAT I/II/III mark them "Ship Master" typed Dropdown/Text, not
    // "Auto Fetch") — every other auto-fetched field (Survey & Demand's OEM Name etc.) is typed
    // "Auto Fetch" directly in FIELD_SPECS, so that alone is enough to catch them.
    const autoFetched = isAutoFetchedField(spec.name) || spec.type === "Auto Fetch";
    // In Add mode, every other CMMS-cascade field (Model, Nomenclature, OEM Name, Supplier, OEM
    // Part No, Shelf Life, Sub Department, and Survey & Demand/Local Purchase's Compartment Name)
    // locks the same way once Equipment Name is picked — see isCmmsCascadeLockedField's doc for
    // why Update mode is excluded (isFieldEditable()'s own carve-out takes over there instead).
    // Only once the cascade actually found a value, though — CMMS not having e.g. an OEM Part No
    // recorded for this equipment shouldn't lock the field empty with no way to fill it in by hand.
    const hasCascadeValue = !!this.addForm.get(controlKey(spec.name))?.value;
    // CAT I/II/III's own Compartment Name (source "Ship Master", so isCmmsCascadeLockedField
    // doesn't already cover it) locks the same value-gated way once applyCat123CompartmentCascade
    // finds a compartment already on record for this equipment + nomenclature — see
    // compartmentAutoMapped's doc.
    const compartmentAutoLocked =
      spec.name === "Compartment Name" && !this.editRow() && this.compartmentAutoMapped();
    const cmmsLocked =
      autoFetched || compartmentAutoLocked || (isCmmsCascadeLockedField(spec) && !this.editRow() && hasCascadeValue);
    // FIELD_SPECS marks the R|H value field `required: false` unconditionally — it's only ever
    // rendered at all once "Enter/Add R|H for SRAR return" is Yes (see rhVisible/displayFields),
    // at which point it must actually be mandatory; when that toggle is No the field (and this
    // required-ness) doesn't apply since the field is filtered out of displayFields entirely.
    const required = isRhSpec(spec) ? true : spec.required;

    return {
      key: controlKey(spec.name),
      rawName: spec.name,
      label,
      required,
      badge: cmmsLocked ? `${spec.source} (auto-fetched)` : spec.source,
      badgeColor: this.badgeColorForSpec(spec),
      placeholder: this.placeholderForSpec(spec, label),
      kind: this.kindForSpec(spec),
      options: this.optionsForSpec(spec, type),
      readonly: cmmsLocked,
    };
  }

  private badgeColorForSpec(spec: ActionFieldSpec): string {
    if (spec.source === "User") return "#22C55E";
    if (spec.source === "Ship Master") return "#4AA8FF";
    return "#F59E0B";
  }

  private placeholderForSpec(spec: ActionFieldSpec, label: string): string {
    if (spec.type === "Dropdown") return `Select ${label.replace(/ Name$/, "")}`;
    if (spec.type === "Checkbox") return "No";
    // Same "Select X" wording as every interactive dropdown/text field, not the old
    // "Auto-fetched from CMMS" text — the field-source badge already says CMMS (auto-fetched);
    // the placeholder doesn't need to repeat it in different words.
    if (spec.type === "Auto Fetch") return `Select ${label.replace(/ Name$/, "")}`;
    // app-date-picker displays selected dates as DD-MMM-YYYY (e.g. "02-Jun-2026") — matches that
    // format in the placeholder too, rather than the native <input type="date"> dd/mm/yyyy hint
    // this used to pair with.
    if (spec.type === "Date") return "DD-MMM-YYYY";
    return `Enter ${label}`;
  }

  private kindForSpec(spec: ActionFieldSpec): FieldKind {
    if (spec.type === "Dropdown") return "select";
    if (spec.type === "Checkbox") return "check";
    if (isSerialSpec(spec)) return "serial";
    // Checked before the "Auto Fetch" type: Frame Station is typed "Auto Fetch" in
    // Survey & Demand/Local Purchase's FIELD_SPECS (it's still CMMS-sourced/read-only), but it must
    // render as the same two-input From/To pair CAT I/II/III use — a single read-only box can't hold
    // a range, and buildControlsForSpecs() never gives it an addForm control either way.
    if (isFrameRangeSpec(spec)) return "frameRange";
    if (spec.type === "Auto Fetch") return "auto";
    if (spec.type === "Date") return "date";
    if (spec.type === "Number" || spec.type === "Decimal") return "number";
    return "text";
  }

  private optionsForSpec(spec: ActionFieldSpec, type: SfdType | null): DropdownOption[] {
    const isMainEquipmentField = spec.optionsKey === "equipment" && /^(Equipment|System) Name$/.test(spec.name);
    if (isMainEquipmentField && type === "System") {
      return this.referenceData()?.systems.map((s) => ({ label: s.label, value: s.label })) ?? [];
    }
    if (spec.name === "Nomenclature" && spec.optionsKey === "nomenclature") {
      // Scoped to the picked Equipment/System's own nomenclatures — one equipment can have
      // several across its fitted history, so this is never the full global list (see
      // pickedEquipmentUniversalId's doc). Empty (not the unfiltered list) until something's
      // picked, so there's nothing plausible-but-wrong to select before Equipment Name is set.
      const equipmentUid = this.pickedEquipmentUniversalId();
      if (!equipmentUid) return [];
      const ref = this.referenceData();
      const seen = new Set<string>();
      return (ref?.nomenclatures ?? [])
        .filter((n) => n.universalId === equipmentUid)
        .filter((n) => (seen.has(n.label) ? false : (seen.add(n.label), true)))
        .map((n) => ({ label: n.label, value: n.label }));
    }
    if (spec.name === "OEM Name" && this.previewCategory() === "CAT III") {
      // The sentinel that reveals "New OEM Name" below (see showNewOemName) — only CAT III has
      // that field, so only its own "OEM Name" dropdown offers a way to pick "not in this list".
      return [...optionsFor(spec.optionsKey, this.liveOptionSets()), { label: NEW_OEM_NAME_OPTION, value: NEW_OEM_NAME_OPTION }];
    }
    if (spec.name === "Supplier Name" && this.previewCategory() === "CAT III") {
      // Same sentinel idea, for "New OEM Supplier Name" below (see showNewOemSupplierName).
      return [
        ...optionsFor(spec.optionsKey, this.liveOptionSets()),
        { label: NEW_OEM_SUPPLIER_OPTION, value: NEW_OEM_SUPPLIER_OPTION },
      ];
    }
    return optionsFor(spec.optionsKey, this.liveOptionSets());
  }

  private applyPrefillIfEditing(): void {
    const row = this.editRow();
    if (!row) return;

    const patch: Record<string, unknown> = {};
    // "auto" (CMMS auto-fetched) fields are locked in Update mode same as everything else, but
    // unlike the rest they were never patched with the record's own value here — they're only
    // ever filled by the Equipment-pick cascade, which can't fire in Update mode since Equipment
    // Name is itself locked. Left alone they render permanently blank instead of showing what the
    // record actually has, even though PREFILL_FIELD_MAP already covers all of them below.
    for (const f of this.displayFields()) {
      if (f.kind === "check" || f.kind === "serial" || f.kind === "frameRange") continue;
      const match = PREFILL_FIELD_MAP.find((m) => m.pattern.test(f.label));
      if (match && this.addForm.contains(f.key)) {
        const val = row[match.key];
        if (val !== undefined) patch[f.key] = val;
      }
    }
    if (this.addForm.contains("sysName")) patch["sysName"] = row.system;
    this.addForm.patchValue(patch);
  }

  setSfdType(t: SfdType): void {
    // Editing an existing record: its Equipment/System type is fixed, so the other radio is locked.
    if (this.editRow() && this.sfdType() !== t) return;
    this.sfdType.set(t);
    this.category.set("CAT I");
    this.checkVals.set({});
    this.serialControl.setValue("");
    this.frameFromControl.setValue("");
    this.frameToControl.setValue("");
    this.pickedEquipmentUniversalId.set(null);
    this.compartmentAutoMapped.set(false);
  }

  selectCategory(id: string): void {
    if (this.isCategoryLocked(id as SfdCategory)) return;
    this.category.set(id as SfdCategory);
    this.checkVals.set({});
    this.serialControl.setValue("");
    this.frameFromControl.setValue("");
    this.frameToControl.setValue("");
    this.pickedEquipmentUniversalId.set(null);
    this.compartmentAutoMapped.set(false);
  }

  setCheckVal(name: string, val: "Yes" | "No"): void {
    if (this.editRow()) return; // locked in Update mode — only Compartment Name/Sub Department are editable
    this.checkVals.update((v) => ({ ...v, [name]: val }));
  }

  openHistory(): void {
    this.historyDrawerOpen.set(true);
  }

  closeHistory(): void {
    this.historyDrawerOpen.set(false);
  }

  openAdd(): void {
    this.addFormDraft.clear();
    this.clearEditingBanner();
    this.submitAttempted.set(false);
    this.editRow.set(null);
    this.sfdType.set(null);
    this.category.set(null);
    this.checkVals.set({});
    this.serialControl.setValue("");
    this.serialControl.enable();
    this.frameFromControl.setValue("");
    this.frameToControl.setValue("");
    this.frameFromControl.enable();
    this.frameToControl.enable();
    this.pickedEquipmentUniversalId.set(null);
    this.compartmentAutoMapped.set(false);
    this.formGeneration.update((n) => n + 1);
    this.view.set("add");
  }

  /** Shared by openUpdate() (full-page) and openFullFormFromApproval() (modal) — both need the
   * exact same addForm/category/type/serial/frame prefill+lock behavior for an existing record,
   * differing only in whether they navigate view() or open fullFormModalOpen(). */
  private prefillFormForRow(row: SfdActionRow): void {
    this.addFormDraft.clear();
    this.submitAttempted.set(false);
    this.editRow.set(row);
    // `row.system` is the equipment's PARENT system name (for display) and can be truthy for
    // ordinary Equipment records too — `isSystemRecord` is the one reliable signal for which
    // radio this record actually is.
    this.sfdType.set(row.isSystemRecord ? "System" : "Equipment");
    this.category.set(row.cat);
    const checkSpec = FIELD_SPECS[row.cat].find((s) => s.type === "Checkbox");
    this.checkVals.set(checkSpec ? { [checkSpec.name]: "Yes" } : {});
    this.serialControl.setValue(row.serial || "");
    const [frameFrom, frameTo] = (row.frame || "").split(/[–-]/);
    this.frameFromControl.setValue((frameFrom || "").trim());
    this.frameToControl.setValue((frameTo || "").trim());
    // Update mode: lock everything except Compartment Name/Sub Department — Equipment Serial No
    // and Frame Station live outside `addForm` (see the constructor), so they're locked here
    // rather than in the effect that handles the rest of the form's fields.
    this.serialControl.disable();
    this.frameFromControl.disable();
    this.frameToControl.disable();
    this.formGeneration.update((n) => n + 1);
  }

  openUpdate(row: SfdActionRow): void {
    this.prefillFormForRow(row);
    this.view.set("add");
    this.flashEditingBanner();
  }

  /**
   * "View Full Form" on a Returned + Change Approval Tracking request — per explicit product
   * direction, done entirely frontend-side with no new backend endpoint. The Approval Tracking API
   * only exposes summary fields (no equipment_ship_id for the pending request), so this locates the
   * SAME equipment/category's record in the Active list (a Change request amends equipment that's
   * still active while the correction is pending) and reuses openUpdate()'s exact prefill + the same
   * submitAdd()/PUT sfd-list/{id}/ update path — just surfaced as a modal instead of navigating
   * away from the Approval Detail screen.
   */
  async openFullFormFromApproval(row: ApprovalSfdRow): Promise<void> {
    const ref = this.referenceData();
    if (!ref) return;
    try {
      const response = await this.sfdActions.loadTransactionList({ equipment_name: row.eqp });
      const match = response.results
        .map((r) => this.mapRawRowToDisplayRow(r, ref))
        .find((r) => r.cat === row.cat);
      if (!match) {
        this.notification.error(
          "Couldn't locate the full record for this request in the Active list — it may not be fitted yet.",
        );
        return;
      }
      this.prefillFormForRow(match);
      this.fullFormModalOpen.set(true);
    } catch {
      this.notification.error("Failed to load the full record for this request. Please try again.");
    }
  }

  closeFullFormModal(): void {
    this.addFormDraft.clear();
    this.clearEditingBanner();
    this.submitAttempted.set(false);
    this.editRow.set(null);
    this.sfdType.set(null);
    this.category.set(null);
    this.checkVals.set({});
    this.serialControl.setValue("");
    this.frameFromControl.setValue("");
    this.frameToControl.setValue("");
    this.formGeneration.update((n) => n + 1);
    this.fullFormModalOpen.set(false);
  }

  async submitAdd(): Promise<void> {
    this.submitAttempted.set(true);
    if (this.addForm.invalid) {
      this.addForm.markAllAsTouched();
      this.notification.error("Please fill in all required fields before submitting.");
      return;
    }
    if (this.serialFieldSpec()?.required && !this.serialValue().trim()) {
      this.notification.error(`${this.serialFieldSpec()!.name} is required.`);
      return;
    }
    if (!this.validateFrameRangeForSubmit()) return;
    const category = this.category();
    const type = this.sfdType();
    const ref = this.referenceData();
    if (!category || !type || !ref) return;

    const editing = this.editRow();
    const result = await this.sfdActions.submitAction({
      category,
      sfdType: type === "System" ? "system" : "equipment",
      formValue: this.addForm.getRawValue(),
      serial: this.serialValue(),
      frame: { from: this.frameFromControl.value, to: this.frameToControl.value },
      checkVals: this.checkVals(),
      ref,
      isEditing: !!editing,
      recordId: editing?.code,
    });
    if (!result.ok) {
      this.notification.error(result.error ?? "Unable to submit. Please try again.");
      return;
    }

    const label = type === "System" ? "System" : "Equipment";
    // Capture before back() — it flips fullFormModalOpen() back to false as part of closing.
    const wasFullFormModal = this.fullFormModalOpen();
    this.back();
    this.loadActiveList(this.activePage(), this.activePageSize());
    if (wasFullFormModal) {
      // Resubmitting the full form from Approval Tracking's "View Full Form" — same follow-up as
      // submitApprovalDetailEdit()'s own resubmit: return to the tracking grid and refresh it so
      // the request's new status/updated_date show immediately.
      this.closeApprovalDetail();
      this.approvalRows.set(await this.sfdActions.loadApprovalTracking());
    }
    this.notification.success(`${editing ? "Update" : "Addition"} for this ${label} submitted for INSMA approval`);
  }

  /** Frame Station From/To validation for submitAdd() — raises the matching notification and
   * returns false when invalid, so the caller can just `if (!this.validateFrameRangeForSubmit()) return;`. */
  private validateFrameRangeForSubmit(): boolean {
    if (!this.frameRangeFieldSpec()) return true;
    if (this.frameFieldBlank(this.frameFromControl.value) || this.frameFieldBlank(this.frameToControl.value)) {
      const isBlank = !this.frameFromControl.value.trim() || !this.frameToControl.value.trim();
      this.notification.error(
        isBlank
          ? `${this.frameRangeFieldSpec()!.name} is required.`
          : `${this.frameRangeFieldSpec()!.name} must be greater than 0.`,
      );
      return false;
    }
    if (this.frameRangeOrderBlank()) {
      this.notification.error(`${this.frameRangeFieldSpec()!.name}: "To" cannot be less than "From".`);
      return false;
    }
    return true;
  }

  back(): void {
    // sfdFormTemplate's Cancel/"Back to List" buttons call this same method whether they're
    // rendered full-page or inside the "View Full Form" modal — in the modal, closing just closes
    // it and leaves the underlying Approval Detail screen's view() alone.
    if (this.fullFormModalOpen()) {
      this.closeFullFormModal();
      return;
    }
    this.addFormDraft.clear();
    this.clearEditingBanner();
    this.submitAttempted.set(false);
    this.view.set("list");
    this.editRow.set(null);
    this.sfdType.set(null);
    this.category.set(null);
    this.checkVals.set({});
    this.serialControl.setValue("");
    this.frameFromControl.setValue("");
    this.frameToControl.setValue("");
    this.formGeneration.update((n) => n + 1);
    this.historyDrawerOpen.set(false);
  }

  viewDeleted(): void {
    this.view.set("deleted");
  }

  async viewApproval(): Promise<void> {
    this.view.set("approval");
    try {
      this.approvalRows.set(await this.sfdActions.loadApprovalTracking());
    } catch (err) {
      console.warn("[SfdActions] approval-tracking/ not reachable", err);
    }
  }

  // --- Remove (3-stage wizard: choose how to handle active maintenance/defects, then the
  // Removal Details form) — submits via the real POST sfd-list/{id}/remove/. Whether the "choose"
  // step is needed is decided by a real dependency check (open-dependencies/), not a mock list. ---
  readonly removeRow = signal<SfdActionRow | null>(null);
  readonly removeStage = signal<RemoveStage>("loading");
  readonly removeOption = signal<RemoveOption>(null);
  readonly removeDefectRows = signal<DefectRecord[]>([]);
  readonly removeDetails = signal<RawRemovalDetails | null>(null);

  readonly removeForm = this.fb.group({
    removalDate: ["", Validators.required],
    authority: ["", Validators.required],
    remarks: ["", Validators.required],
  });

  async confirmDeletePrompt(row: SfdActionRow): Promise<void> {
    this.removeRow.set(row);
    this.removeStage.set("loading"); // stay neutral until open-dependencies resolves — never flash "choose" first
    this.removeOption.set(null);
    this.removeForm.reset({ removalDate: "", authority: "", remarks: "" });
    this.removeDefectRows.set([]);
    this.removeDetails.set(null);
    let dependencies: DefectRecord[] = [];
    let details: RawRemovalDetails | null = null;
    try {
      [dependencies, details] = await Promise.all([
        this.sfdActions.loadOpenDependencies(row.code),
        this.sfdActions.loadRemovalDetails(row.code),
      ]);
    } catch (err) {
      // Both calls already resolve to a safe fallback on their own errors — this only guards against
      // something unexpected slipping through, so Remove still lands on the Removal Details form
      // instead of being stranded on the default "choose" stage with no data.
      console.warn("[SfdActions] Remove pre-checks failed — defaulting to the Removal Details form", err);
    }
    if (this.removeRow() !== row) return; // closed/replaced while the check was in flight
    this.removeDefectRows.set(dependencies);
    this.removeDetails.set(details);
    this.removeStage.set(dependencies.length ? "choose" : "form");
  }

  closeRemove(): void {
    this.removeRow.set(null);
    this.removeStage.set("loading");
    this.removeOption.set(null);
    this.removeDetails.set(null);
  }

  setRemoveOption(option: "close" | "associate"): void {
    this.removeOption.set(option);
  }

  removeContinue(): void {
    const option = this.removeOption();
    if (!option) return;
    this.removeStage.set(option === "close" ? "defects" : "form");
  }

  removeBackChoose(): void {
    this.removeStage.set("choose");
  }

  /** True when any of the Removal Details form's four read-only fields (Equipment Nomenclature,
   * Equipment Serial No., Sub Department, Location on Board) has no value to show — same
   * fallback chain as the template and `submitRemove()`'s payload, so the Submit button disables
   * exactly when that payload would otherwise go out with a blank identifying field. */
  removalDetailsMissing(): boolean {
    const row = this.removeRow();
    if (!row) return true;
    const details = this.removeDetails();
    return (
      !(details?.equipment_nomenclature || row.nomen) ||
      !(details?.equipment_sr_no || row.serial) ||
      !(details?.sub_dept || row.dept) ||
      !(details?.compartment_name || row.compartment)
    );
  }

  onDefectAction(defect: DefectRecord): void {
    this.notification.success(
      `Opening ${defect.id} in ${defect.type === "Defect" ? "DART" : "Routines"}...`,
    );
  }

  async submitRemove(): Promise<void> {
    const row = this.removeRow();
    if (!row || this.removeForm.invalid) {
      this.removeForm.markAllAsTouched();
      this.notification.error("Removal Date, Authority for Removal and Remarks are required.");
      return;
    }

    const details = this.removeDetails();
    const formValue = this.removeForm.getRawValue();
    const result = await this.sfdActions.submitRemoval(row, {
      removalDate: formValue.removalDate ?? "",
      authority: formValue.authority ?? "",
      remarks: formValue.remarks ?? "",
      equipmentNomenclature: details?.equipment_nomenclature || row.nomen,
      equipmentSrNo: details?.equipment_sr_no || row.serial,
      subDept: details?.sub_dept || row.dept,
      compartmentName: details?.compartment_name || row.compartment,
    });
    if (!result.ok) {
      this.notification.error(result.error ?? "Unable to submit this removal. Please try again.");
      return;
    }

    this.closeRemove();
    this.loadActiveList(this.activePage(), this.activePageSize());
    this.notification.success(`Removal of ${row.name} submitted for INSMA approval`);
  }

  // --- Record Edit modal -----------------------------------------------------
  readonly recModalOpen = signal(false);
  readonly recModalMode = signal<RecModalMode>("update");
  readonly recModalRow = signal<SfdActionRow | null>(null);
  readonly recModalDetails = signal<RawUpdateSrNoDetails | null>(null);

  readonly recForm = this.fb.group({
    serial: [""],
    qty: [""],
    removalAuthority: [""],
    removalDate: [""],
    installationDate: [""],
  });

  readonly recModalTitle = computed(() =>
    this.recModalMode() === "serial" ? "Change Serial Number" : "Update SFD Record",
  );
  readonly recModalSub = computed(() =>
    this.recModalMode() === "serial"
      ? "Update the equipment serial number for this record"
      : "Edit this record and submit the change for INSMA approval",
  );

  async openRecordEdit(row: SfdActionRow, mode: RecModalMode): Promise<void> {
    this.recModalRow.set(row);
    this.recModalMode.set(mode);
    this.recModalDetails.set(null);
    this.recForm.reset({
      serial: row.serial || "",
      qty: String(row.qty),
      removalAuthority: "",
      removalDate: "",
      installationDate: "",
    });
    this.recModalOpen.set(true);

    if (mode !== "serial") return;
    const details = await this.sfdActions.loadUpdateSrNoDetails(row.code);
    if (this.recModalRow() !== row) return; // closed/replaced while the fetch was in flight
    this.recModalDetails.set(details);
    if (details) {
      this.recForm.patchValue({
        serial: details.current_sr_no || row.serial || "",
        removalAuthority: details.removal_authority || "",
        removalDate: toDateInputValue(details.removal_date),
        installationDate: toDateInputValue(details.installation_date),
      });
    }
  }

  closeRecordEdit(): void {
    this.recModalOpen.set(false);
    this.recModalRow.set(null);
    this.recModalDetails.set(null);
  }

  async saveRecordEdit(): Promise<void> {
    const row = this.recModalRow();
    const mode = this.recModalMode();
    if (!row) return;

    const formValue = this.recForm.getRawValue();

    if (mode === "serial") {
      if (!formValue.serial?.trim()) {
        this.notification.error("New Equipment Serial No is required.");
        return;
      }
      if (!formValue.removalAuthority?.trim() || !formValue.removalDate || !formValue.installationDate) {
        this.notification.error("Removal Authority, Removal Date and Installation Date are required.");
        return;
      }
    }

    const details = this.recModalDetails();
    const result = await this.sfdActions.submitRecordEdit(row, mode, {
      serial: formValue.serial ?? "",
      qty: formValue.qty ?? "",
      equipmentNomenclature: details?.equipment_nomenclature || row.nomen,
      currentSrNo: details?.current_sr_no || row.serial,
      subDept: details?.sub_dept || row.dept,
      maintopNo: details?.maintop_no || row.maintop,
      removalAuthority: formValue.removalAuthority ?? "",
      removalDate: formValue.removalDate ?? "",
      installationDate: formValue.installationDate ?? "",
    });
    if (!result.ok) {
      this.notification.error(result.error ?? "Unable to save changes. Please try again.");
      return;
    }

    this.closeRecordEdit();
    this.loadActiveList(this.activePage(), this.activePageSize());
    const msg =
      mode === "serial"
        ? `Serial number change for ${row.name} submitted for INSMA approval`
        : `Update for ${row.name} submitted for INSMA approval`;
    this.notification.success(msg);
  }

  // --- Record View modal (Active list row click) — read-only "Ship Fit Details" ------------
  readonly recordViewOpen = signal(false);
  readonly recordViewRow = signal<SfdActionRow | null>(null);

  readonly recordViewFields = computed<DisplayFieldValue[]>(() => {
    const row = this.recordViewRow();
    if (!row) return [];
    const field = (
      label: string,
      value: string | number | null | undefined,
      badge: "CMMS" | "User",
    ): DisplayFieldValue => ({
      label,
      value: value === undefined || value === null || value === "" ? "—" : String(value),
      badge,
      badgeColor: badge === "User" ? "#22C55E" : "#F59E0B",
    });
    return [
      field("Equipment Name", row.name, "CMMS"),
      field("System Name", row.system, "CMMS"),
      field("Model", row.model, "CMMS"),
      field("Nomenclature", row.nomen, "CMMS"),
      field("OEM Name", row.oem, "CMMS"),
      field("Supplier", row.supplier, "CMMS"),
      field("OEM Part No", row.part, "CMMS"),
      field("Equipment Serial No", row.serial, "User"),
      field("Maintop No.", row.maintop, "CMMS"),
      field("Compartment Name", row.compartment, "CMMS"),
      field("Location", row.location, "CMMS"),
      field("Frame Station", row.frame, "User"),
      field("Deck No", row.deck, "User"),
      field("Installation Date", row.installDate, "User"),
      field("Authority for Installation", row.authority, "User"),
      field("Authority Date", row.authorityDate, "User"),
      field("Qty Fitted", row.qty, "User"),
      field("Shelf Life", row.shelfLife, "CMMS"),
      field("Sub Department", row.dept, "CMMS"),
    ];
  });

  openRecordView(row: SfdActionRow): void {
    this.recordViewRow.set(row);
    this.recordViewOpen.set(true);
  }

  onActiveRowClicked(row: unknown): void {
    this.openRecordView(row as SfdActionRow);
  }

  closeRecordView(): void {
    this.recordViewOpen.set(false);
    this.recordViewRow.set(null);
  }

  // --- Deleted / Approval views -------------------------------------------
  readonly deletedRows = signal<DeletedSfdRow[]>([]);

  // --- Recent Activity popup (SFD Management header) -----------------------------------------
  readonly recentActivityOpen = signal(false);
  readonly recentActivityLoading = signal(false);
  readonly recentActivityRows = signal<RecentActivityRow[]>([]);

  async openRecentActivity(): Promise<void> {
    this.recentActivityOpen.set(true);
    this.recentActivityLoading.set(true);
    try {
      this.recentActivityRows.set(await this.sfdActions.loadRecentActivity());
    } finally {
      this.recentActivityLoading.set(false);
    }
  }

  closeRecentActivity(): void {
    this.recentActivityOpen.set(false);
  }

  readonly deletedCols = [
    { headerName: "INSMA Code", field: "code", flex: 1, minWidth: 130, cellStyle: { color: "#4AA8FF", fontWeight: 600 } },
    { headerName: "Equipment Name", field: "name", flex: 1.5 },
    { headerName: "Nomenclature", field: "nomen", flex: 1 },
    { headerName: "Removal Date", field: "date", flex: 1 },
    { headerName: "Removal Authority", field: "auth", flex: 1.2 },
    { headerName: "Reason", field: "reason", flex: 1.5 },
    { headerName: "Removed By", field: "by", flex: 1 },
  ];

  readonly approvalRows = signal<ApprovalSfdRow[]>([]);

  // Every column below gets an explicit minWidth sized to its own header text — the shared
  // grid's defaultColDef.minWidth (120px) is too narrow for headers like "Last Updated Date" or
  // "Equipment Name" once 10+ flex columns compete for space, so they were ellipsis-truncating
  // ("Equipment...", "SFD Categ...") instead of the grid just scrolling horizontally.
  readonly approvalCols = [
    { headerName: "Request ID", field: "id", flex: 1, minWidth: 130, cellStyle: { color: "#4AA8FF", fontWeight: 600 } },
    { headerName: "Equipment Name", field: "eqp", flex: 1.8, minWidth: 170 },
    { headerName: "SFD Category", field: "cat", flex: 1, minWidth: 150 },
    { headerName: "Submitted By", field: "by", flex: 1, minWidth: 150 },
    { headerName: "Submitted Date", field: "date", flex: 1, minWidth: 150 },
    {
      headerName: "Current Status",
      field: "status",
      flex: 1.8,
      minWidth: 210,
      cellRenderer: GridStatusChipRenderer,
      cellRendererParams: { toneMap: APPROVAL_STATUS_TONE_MAP, labelMap: APPROVAL_STATUS_LABEL_MAP },
    },
    { headerName: "INSMA Officer", field: "officer", flex: 1, minWidth: 150 },
    { headerName: "Approval Date", field: "approveDate", flex: 1, minWidth: 150 },
    { headerName: "INSMA Remarks", field: "remarks", flex: 1.5, minWidth: 160 },
    { headerName: "Last Updated Date", field: "lastUpdatedDate", flex: 1, minWidth: 170 },
    {
      headerName: "Actions",
      width: 110,
      pinned: "right" as const,
      cellStyle: { display: "flex", justifyContent: "center", alignItems: "center" },
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: [
          { icon: "view", label: "View", color: "#4AA8FF", action: (r: ApprovalSfdRow) => this.openApprovalDetail(r) },
        ],
      },
    },
  ];

  // --- Approval Detail view — opened inline (not a popup) from the Actions "View" icon or a row
  // click on the Approval grid, mirroring the SFD prototype's in-page detail screen. Read-only
  // while the request is in progress or already approved; only a "Returned" request can be
  // corrected and resubmitted (there is still no live resubmit endpoint, so the save is mocked).
  readonly approvalDetailRow = signal<ApprovalSfdRow | null>(null);

  // Only populated/used when the request is "Returned" — Equipment Name/SFD Category/Submitted By/
  // Submitted Date become editable so the submitter can correct them before resubmitting. INSMA
  // Remarks stays read-only (it's INSMA's own note); `correctionNote` is a separate submitter-side
  // note with nowhere to persist yet (no dedicated field on `ApprovalSfdRow`/the backend today).
  readonly approvalEditForm = this.fb.group({
    eqp: [""],
    cat: [""],
    by: [""],
    date: [""],
    correctionNote: [""],
  });

  readonly approvalIsEditable = computed(() => this.approvalDetailRow()?.status === "Returned");

  openApprovalDetail(row: ApprovalSfdRow): void {
    this.approvalDetailRow.set(row);
    this.approvalEditForm.reset({ eqp: row.eqp, cat: row.cat, by: row.by, date: row.date, correctionNote: "" });
    this.view.set("approvalDetail");
  }

  onApprovalRowClicked(row: unknown): void {
    this.openApprovalDetail(row as ApprovalSfdRow);
  }

  closeApprovalDetail(): void {
    this.approvalDetailRow.set(null);
    this.view.set("approval");
  }

  async submitApprovalDetailEdit(): Promise<void> {
    const row = this.approvalDetailRow();
    if (!row) return;
    const formValue = this.approvalEditForm.getRawValue();
    const result = await this.sfdActions.submitApprovalCorrection(row, {
      eqp: formValue.eqp || row.eqp,
      cat: formValue.cat || row.cat,
      by: formValue.by || row.by,
      date: formValue.date || row.date,
      correctionNote: formValue.correctionNote || "",
    });
    if (!result.ok) {
      this.notification.error(result.error ?? "Unable to resubmit this request. Please try again.");
      return;
    }
    this.closeApprovalDetail();
    // Reload from the server rather than patch the local row — the backend also stamps
    // updated_date/amendment_note and flips status to "Pending" itself.
    this.approvalRows.set(await this.sfdActions.loadApprovalTracking());
    this.notification.success(`Request ${row.id} resubmitted for INSMA approval`);
  }

  approvalStatusTone(status: ApprovalStatus): ChipTone {
    return APPROVAL_STATUS_TONE_MAP[status];
  }

  approvalStatusLabel(status: ApprovalStatus): string {
    return APPROVAL_STATUS_LABEL_MAP[status];
  }

  // --- Approval Tracking search/filter toolbar — same "search box + Filters + Reset Filters"
  // pattern as the Active list's toolbar (toggleActFilters/clearActFilters), reused here rather
  // than reinvented since approvalRows() is already fully loaded client-side (no server paging to
  // coordinate), so filtering is a plain computed instead of a re-fetch. ---
  readonly approvalSearchTerm = signal("");
  readonly approvalFiltersOpen = signal(false);
  readonly approvalCategoryFilter = signal("");
  readonly approvalStatusFilter = signal("");

  readonly approvalCategoryOptions = computed<DropdownOption[]>(() => {
    const values = new Set(this.approvalRows().map((r) => r.cat));
    return Array.from(values).map((v) => ({ label: v, value: v }));
  });

  readonly approvalStatusOptions = computed<DropdownOption[]>(() => {
    const values = new Set(this.approvalRows().map((r) => r.status));
    return Array.from(values).map((v) => ({ label: v, value: v }));
  });

  readonly filteredApprovalRows = computed(() => {
    const term = this.approvalSearchTerm().trim().toLowerCase();
    const cat = this.approvalCategoryFilter();
    const status = this.approvalStatusFilter();
    return this.approvalRows().filter((row) => {
      if (cat && row.cat !== cat) return false;
      if (status && row.status !== status) return false;
      if (!term) return true;
      return [row.id, row.eqp, row.by].some((v) => v.toLowerCase().includes(term));
    });
  });

  readonly approvalAppliedCount = computed(
    () => [this.approvalCategoryFilter(), this.approvalStatusFilter()].filter(Boolean).length,
  );
  readonly approvalHasFilters = computed(() => this.approvalAppliedCount() > 0);

  setApprovalSearchTerm(value: string): void {
    this.approvalSearchTerm.set(value);
  }

  toggleApprovalFilters(): void {
    this.approvalFiltersOpen.update((v) => !v);
  }

  setApprovalCategoryFilter(value: FilterValue): void {
    this.approvalCategoryFilter.set(value ? String(value) : "");
  }

  setApprovalStatusFilter(value: FilterValue): void {
    this.approvalStatusFilter.set(value ? String(value) : "");
  }

  clearApprovalFilters(): void {
    this.approvalSearchTerm.set("");
    this.approvalCategoryFilter.set("");
    this.approvalStatusFilter.set("");
  }
}
