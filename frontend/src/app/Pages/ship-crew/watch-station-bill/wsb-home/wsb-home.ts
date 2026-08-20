import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { KeyValuePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { Router } from "@angular/router";
import { ColDef } from "ag-grid-community";
import { firstValueFrom } from "rxjs";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { ActionRendererComponent } from "../../../../shared/components/data-grid/grid-action-icons";
import { GridStatusChipRenderer } from "../../../../shared/components/data-grid/grid-status-chip-renderer";
import { ModalComponent } from "../../../../shared/components/modal/modal.component";
import { KpiCard } from "../../../../shared/components/kpi-card/kpi-card";
import { IconComponent } from "../../../../shared/components/icon/icon.component";
import { SelectInput, DropdownOption } from "../../../../shared/components/select-input/select-input";
import { HelpGuidance } from "../../../inventory/shared/components/help-guidance/help-guidance";
import { NotificationService } from "../../../../Core/services/notification/notification.service";
import { PrintColumn, ReportExportService } from "../../../../Core/services/generic-export-service/generic-export.service";
import { CrewApiService } from "../../services/crew-api.service";
import { PersonnelStatusTab } from "../../personnel-status/personnel-status.model";
import {
  Civilian,
  CrewPersonnel,
  DeptStrength,
  MasterEntry,
  MasterType,
  PersonType,
  RankClassification,
  RankOption,
  SailingAssignmentRow,
  SailingDetail,
  SailingSummary,
  SailorClass,
  WatchbillDashboardCounts,
} from "../../models/crew.model";

const CREW_BASE = "/afterAuth/Ship_Crew_and_HR";

type WsbTab = "dashboard" | "sailings" | "history" | "references";
type SailingView = "list" | "detail";
type SailingDetailTab = "personnel" | "assignments";
type ReferenceTab = MasterType | "civilians" | "classification";

interface NewCivilianForm {
  name: string;
  personType: PersonType;
  role: string;
  desig: string;
  rank: string;
  serviceNo: string;
  fleet: string;
  ship: string;
  refId: string;
  contact: string;
  remarks: string;
}

const MASTER_LABELS: Record<MasterType, string> = {
  action: "Action Station",
  defence: "Defence Station",
  cruising: "Cruising Station",
  shelter: "Shelter Station",
  emergency: "Emergency Station",
};

const PERSON_TYPE_LABELS: Record<PersonType, string> = {
  civilian: "Civilian",
  officer: "Officer",
  fleet_officer: "Fleet Officer",
  fleet_staff: "Fleet Staff",
  fleet_commander: "Fleet Commander",
  sailor: "Sailor",
};

interface PersonTypeUiConfig {
  banner: string;
  appointmentLabel: string;
  rankLabel: string;
  serviceNoLabel: string;
  showFleetShip: boolean;
}

const CIVILIAN_BANNER = "Civilian officials will be included in sailing watch bills.";
const SHARED_POOL_BANNER =
  "This person is added to the shared pool and can then be selected when adding personnel to any sailing.";

const PERSON_TYPE_UI: Record<Exclude<PersonType, "civilian">, PersonTypeUiConfig> = {
  officer: {
    banner: "Officers are included in the ship's company and watch bills.",
    appointmentLabel: "Appointment / Designation",
    rankLabel: "Rank",
    serviceNoLabel: "Service / Personal No.",
    showFleetShip: false,
  },
  fleet_officer: {
    banner: "Fleet Officers embarked from another command / fleet.",
    appointmentLabel: "Appointment",
    rankLabel: "Rank",
    serviceNoLabel: "Service / Personal No.",
    showFleetShip: true,
  },
  fleet_staff: {
    banner: "Fleet Staff members embarked for operational duties.",
    appointmentLabel: "Role / Appointment",
    rankLabel: "Rank / Grade",
    serviceNoLabel: "Service / Emp No.",
    showFleetShip: true,
  },
  fleet_commander: {
    banner: "Fleet Commander embarked — will appear as senior authority in the bill.",
    appointmentLabel: "Command Appointment",
    rankLabel: "Rank",
    serviceNoLabel: "Service / Personal No.",
    showFleetShip: true,
  },
  sailor: {
    banner: "Sailors are included in the ship's company and watch/action station assignments.",
    appointmentLabel: "Trade / Branch",
    rankLabel: "Rank",
    serviceNoLabel: "Service / Personal No.",
    showFleetShip: false,
  },
};

const CIVILIAN_ROLE_OPTIONS: DropdownOption[] = [
  "Barber",
  "CIV Bearer",
  "MES Boy",
  "Canteen Manager",
  "NAAFI Staff",
  "Dhobi",
  "Cook (Civ)",
  "Other",
].map((value) => ({ label: value, value }));

const SAILOR_CLASS_OPTIONS: DropdownOption[] = [
  { label: "Junior", value: "Junior" },
  { label: "Senior", value: "Senior" },
];

@Component({
  selector: "app-wsb-home",
  standalone: true,
  imports: [FormsModule, KeyValuePipe, DataGrid, ModalComponent, KpiCard, SelectInput, HelpGuidance, IconComponent],
  templateUrl: "./wsb-home.html",
  styleUrl: "./wsb-home.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WsbHome implements OnInit {
  private readonly api = inject(CrewApiService);
  private readonly notifications = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly exportService = inject(ReportExportService);

  readonly masterTypes: MasterType[] = ["action", "defence", "cruising", "shelter", "emergency"];
  readonly masterLabels = MASTER_LABELS;
  readonly personTypeLabels = PERSON_TYPE_LABELS;
  readonly personTypes = Object.keys(PERSON_TYPE_LABELS) as PersonType[];

  readonly activeTab = signal<WsbTab>("dashboard");

  // Dashboard
  readonly dashboardCounts = signal<WatchbillDashboardCounts>({ total: 0, present: 0, absent: 0 });
  readonly deptStrength = signal<DeptStrength[]>([]);

  deptStrengthPercent(dept: DeptStrength): number {
    return dept.total > 0 ? Math.round((dept.present / dept.total) * 100) : 0;
  }

  deptStrengthLevel(dept: DeptStrength): "high" | "medium" | "low" {
    const pct = this.deptStrengthPercent(dept);
    if (pct >= 90) return "high";
    if (pct >= 70) return "medium";
    return "low";
  }
  readonly activeSailingsCount = signal(0);
  readonly completedSailingsCount = signal(0);

  // Sailings
  readonly sailings = signal<SailingSummary[]>([]);
  readonly sailingView = signal<SailingView>("list");
  readonly currentSailing = signal<SailingDetail | null>(null);
  readonly sailingDetailTab = signal<SailingDetailTab>("personnel");
  readonly showNewSailingModal = signal(false);
  readonly assignmentRows = signal<SailingAssignmentRow[]>([]);
  readonly assignEditMode = signal(false);
  readonly coOptions = signal<DropdownOption[]>([]);
  readonly templateSailingOptions = signal<DropdownOption[]>([]);

  newSailingName = "";
  newSailingArea = "";
  newSailingStart = "";
  newSailingTime = "";
  newSailingCo: string | null = "";
  copyFromSailingId: number | null = null;

  readonly sailingColumnDefs: ColDef[] = [
    { field: "name", headerName: "Sailing / Operation", flex: 1.2 },
    { field: "area", headerName: "Area of Operation", flex: 1 },
    { field: "start", headerName: "Departure Date", width: 140 },
    { field: "co", headerName: "Commanding Officer", flex: 1 },
    { field: "personnelCount", headerName: "Embarked", width: 110 },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      cellRenderer: GridStatusChipRenderer,
      cellRendererParams: {
        labelMap: { active: "Active", completed: "Completed" },
        toneMap: { active: "success", completed: "neutral" },
      },
    },
    {
      headerName: "Action",
      field: "id",
      width: 160,
      sortable: false,
      filter: false,
      // Without this, clicking an action icon still leaves ag-grid's default cell-focus
      // rectangle drawn around the whole cell — reads like an input box got selected.
      suppressCellFocus: true,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: unknown) => {
          const sailing = row as SailingSummary;
          return [
            { icon: "edit", label: "Edit", color: "#2563eb", action: () => this.openSailingDetail(sailing.id) },
            {
              icon: "check",
              label: "Complete",
              color: "#16a34a",
              action: () => this.completeSailing(sailing.id, sailing.name),
            },
            {
              icon: "delete",
              label: "Delete",
              color: "#dc2626",
              action: () => this.deleteSailing(sailing.id, sailing.name),
            },
          ];
        },
      },
    },
  ];

  readonly assignmentFields: { key: keyof SailingAssignmentRow; label: string }[] = [
    { key: "w3", label: "W3" },
    { key: "w2", label: "W2" },
    { key: "action", label: "Action Stn" },
    { key: "defence", label: "Defence Stn" },
    { key: "cruising", label: "Cruising Stn" },
    { key: "shelter", label: "Shelter Stn" },
    { key: "emergency", label: "Emergency Stn" },
    { key: "bloodGroup", label: "Blood Group" },
    { key: "mess", label: "Mess" },
    { key: "remarks", label: "Remarks" },
  ];

  // Add personnel modal
  readonly showAddPersonnelModal = signal(false);
  readonly availablePersonnel = signal<CrewPersonnel[]>([]);
  readonly selectedPersonnelIds = signal<Set<number>>(new Set());

  // History
  readonly historySailings = signal<SailingSummary[]>([]);
  readonly historyDetail = signal<SailingDetail | null>(null);
  readonly historyColumnDefs: ColDef[] = [
    { field: "name", headerName: "Sailing / Operation", flex: 1.2 },
    { field: "area", headerName: "Area", flex: 1 },
    { field: "start", headerName: "Departure Date", width: 140 },
    { field: "completedAt", headerName: "Completed Date", width: 140 },
    { field: "co", headerName: "Commanding Officer", flex: 1 },
    { field: "personnelCount", headerName: "Embarked", width: 110 },
    {
      headerName: "View",
      field: "id",
      width: 100,
      sortable: false,
      filter: false,
      suppressCellFocus: true,
      cellRenderer: () => `<button type="button" class="wsb-history-view-btn">View</button>`,
      onCellClicked: (params) => void this.viewHistoryDetail((params.data as SailingSummary).id),
    },
  ];

  // References
  readonly referenceTab = signal<ReferenceTab>("action");
  readonly masterEntries = signal<MasterEntry[]>([]);
  readonly civilians = signal<Civilian[]>([]);
  readonly showAddCivilianModal = signal(false);
  readonly showAddMasterModal = signal(false);
  /** `referenceTab()` is `MasterType | "civilians" | "classification"` — this resolves the
   * label only for the plain master-list branch, where the template guarantees a `MasterType`. */
  readonly activeMasterLabel = computed(() => {
    const tab = this.referenceTab();
    return tab === "civilians" || tab === "classification" ? "" : this.masterLabels[tab];
  });
  readonly personTypeUi = PERSON_TYPE_UI;
  readonly civilianBanner = CIVILIAN_BANNER;
  readonly sharedPoolBanner = SHARED_POOL_BANNER;
  readonly civilianRoleOptions = CIVILIAN_ROLE_OPTIONS;
  readonly rankOptions = signal<DropdownOption[]>([]);
  newMasterName = "";
  newCivilian: NewCivilianForm = {
    name: "",
    personType: "civilian",
    role: "",
    desig: "",
    rank: "",
    serviceNo: "",
    fleet: "",
    ship: "",
    refId: "",
    contact: "",
    remarks: "",
  };

  // References — Junior/Senior Sailor Classification
  readonly rankClassifications = signal<RankClassification[]>([]);
  readonly showAddClassificationModal = signal(false);
  readonly sailorClassOptions = SAILOR_CLASS_OPTIONS;
  newClassificationRank: string | null = null;
  newClassificationValue: SailorClass | null = "Junior";

  ngOnInit(): void {
    void this.loadDashboard();
    void this.loadSailings();
  }

  // ── Top-level tabs ───────────────────────────────────────────
  selectTab(tab: WsbTab): void {
    this.activeTab.set(tab);
    if (tab === "dashboard") void this.loadDashboard();
    if (tab === "sailings") void this.loadSailings();
    if (tab === "history") void this.loadHistory();
    if (tab === "references") this.selectReferenceTab(this.referenceTab());
  }

  private async loadDashboard(): Promise<void> {
    const data = await firstValueFrom(this.api.getWatchbillDashboard());
    this.dashboardCounts.set(data.counts);
    this.deptStrength.set(data.deptStrength);
    this.activeSailingsCount.set(data.activeSailingsCount);
    this.completedSailingsCount.set(data.completedSailingsCount);
  }

  /** Mirrors the Ship Crew dashboard's own "View more" links to `personnel_status/?tab=...`. */
  viewMorePersonnel(tab: PersonnelStatusTab): void {
    void this.router.navigate([`${CREW_BASE}/personnel-status`], { queryParams: { tab } });
  }

  viewMoreSailings(): void {
    this.selectTab("sailings");
  }

  viewMoreHistory(): void {
    this.selectTab("history");
  }

  // ── Sailings — list ──────────────────────────────────────────
  private async loadSailings(): Promise<void> {
    this.sailings.set(await firstValueFrom(this.api.getSailings()));
  }

  openNewSailingModal(): void {
    this.newSailingName = "";
    this.newSailingArea = "";
    this.newSailingStart = "";
    const now = new Date();
    this.newSailingTime = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    this.newSailingCo = "";
    this.copyFromSailingId = null;
    this.coOptions.set([]);
    this.templateSailingOptions.set([]);
    this.showNewSailingModal.set(true);
    void this.loadNewSailingOptions();
  }

  private async loadNewSailingOptions(): Promise<void> {
    const [personnel, active, completed] = await Promise.all([
      firstValueFrom(this.api.getPersonnel()).catch(() => []),
      firstValueFrom(this.api.getSailings()).catch(() => []),
      firstValueFrom(this.api.getHistorySailings()).catch(() => []),
    ]);
    this.coOptions.set(
      personnel.map((p) => {
        const label = `${p.rank} ${p.firstName} ${p.lastName}`.trim();
        return { label, value: label };
      }),
    );
    this.templateSailingOptions.set(
      [...active, ...completed].map((s) => ({ label: `${s.name} (${s.start.slice(0, 10)})`, value: s.id })),
    );
  }

  async createSailing(): Promise<void> {
    if (!this.newSailingName.trim() || !this.newSailingStart || !this.newSailingTime) {
      this.notifications.error("Sailing name, departure date and departure time are required.");
      return;
    }
    const sailing = await firstValueFrom(
      this.api.createSailing({
        name: this.newSailingName.trim(),
        area: this.newSailingArea.trim() || undefined,
        start: this.newSailingStart,
        startTime: this.newSailingTime,
        co: (this.newSailingCo ?? "").trim() || undefined,
        copyFromSailingId: this.copyFromSailingId,
      }),
    );
    this.showNewSailingModal.set(false);
    await this.loadSailings();
    await this.openSailingDetail(sailing.id);
  }

  async openSailingDetail(id: number): Promise<void> {
    const detail = await firstValueFrom(this.api.getSailingDetail(id));
    if (!detail) return;
    this.currentSailing.set(detail);
    this.sailingView.set("detail");
    this.sailingDetailTab.set("personnel");
    this.assignEditMode.set(false);
    this.assignmentRows.set(Object.values(detail.departments).flat());
  }

  backToSailingsList(): void {
    this.sailingView.set("list");
    this.currentSailing.set(null);
    void this.loadSailings();
  }

  selectSailingDetailTab(tab: SailingDetailTab): void {
    this.sailingDetailTab.set(tab);
    const sailing = this.currentSailing();
    if (tab === "assignments" && sailing) {
      this.assignmentRows.set(Object.values(sailing.departments).flat());
    }
  }

  get sailingPersonnelRows(): SailingAssignmentRow[] {
    const sailing = this.currentSailing();
    return sailing ? Object.values(sailing.departments).flat() : [];
  }

  async completeSailing(id?: number, name?: string): Promise<void> {
    const targetId = id ?? this.currentSailing()?.id;
    const targetName = name ?? this.currentSailing()?.name;
    if (!targetId) return;
    if (!confirm(`Mark "${targetName}" as COMPLETE? It will be archived and locked.`)) return;
    await firstValueFrom(this.api.completeSailing(targetId, new Date().toISOString().slice(0, 10)));
    if (this.sailingView() === "detail") {
      this.backToSailingsList();
    } else {
      await this.loadSailings();
    }
  }

  async deleteSailing(id: number, name: string): Promise<void> {
    if (!confirm(`Delete sailing "${name}"? This cannot be undone.`)) return;
    await firstValueFrom(this.api.deleteSailing(id));
    await this.loadSailings();
  }

  // ── Sailings — add personnel ─────────────────────────────────
  async openAddPersonnelModal(): Promise<void> {
    this.availablePersonnel.set(await firstValueFrom(this.api.getPersonnel()));
    this.selectedPersonnelIds.set(new Set());
    this.showAddPersonnelModal.set(true);
  }

  isPersonnelAlreadyAdded(pno: string): boolean {
    return this.sailingPersonnelRows.some((row) => row.pno === pno);
  }

  togglePersonnelSelection(id: number): void {
    const set = new Set(this.selectedPersonnelIds());
    if (set.has(id)) set.delete(id);
    else set.add(id);
    this.selectedPersonnelIds.set(set);
  }

  async addSelectedPersonnel(): Promise<void> {
    const sailing = this.currentSailing();
    if (!sailing || !this.selectedPersonnelIds().size) return;
    await firstValueFrom(this.api.addPersonnelToSailing(sailing.id, [...this.selectedPersonnelIds()]));
    this.showAddPersonnelModal.set(false);
    await this.openSailingDetail(sailing.id);
  }

  async removePersonnel(sailingPersonnelId: number): Promise<void> {
    const sailing = this.currentSailing();
    if (!sailing) return;
    if (!confirm("Remove this person from the sailing?")) return;
    await firstValueFrom(this.api.removePersonnelFromSailing(sailingPersonnelId));
    await this.openSailingDetail(sailing.id);
  }

  // ── Assignments ───────────────────────────────────────────────
  toggleAssignEdit(): void {
    const wasEditing = this.assignEditMode();
    this.assignEditMode.set(!wasEditing);
    if (wasEditing) void this.saveAssignments();
  }

  async saveAssignments(): Promise<void> {
    const sailing = this.currentSailing();
    if (!sailing) return;
    await firstValueFrom(this.api.saveAssignments(sailing.id, this.assignmentRows()));
  }

  updateAssignmentField(pno: string, field: keyof SailingAssignmentRow, value: string): void {
    this.assignmentRows.update((rows) => rows.map((row) => (row.pno === pno ? { ...row, [field]: value } : row)));
  }

  // ── History ───────────────────────────────────────────────────
  private async loadHistory(): Promise<void> {
    this.historySailings.set(await firstValueFrom(this.api.getHistorySailings()));
  }

  async viewHistoryDetail(id: number): Promise<void> {
    this.historyDetail.set(await firstValueFrom(this.api.getSailingDetail(id)));
  }

  closeHistoryDetail(): void {
    this.historyDetail.set(null);
  }

  // ── References — Masters ─────────────────────────────────────
  selectReferenceTab(tab: ReferenceTab): void {
    this.referenceTab.set(tab);
    this.newMasterName = "";
    if (tab === "civilians") void this.loadCivilians();
    else if (tab === "classification") void this.loadRankClassifications();
    else void this.loadMasterList(tab);
  }

  private async loadMasterList(type: MasterType): Promise<void> {
    this.masterEntries.set(await firstValueFrom(this.api.getMasterList(type)));
  }

  openAddMasterModal(): void {
    this.newMasterName = "";
    this.showAddMasterModal.set(true);
  }

  async addMasterEntry(): Promise<void> {
    const tab = this.referenceTab();
    if (tab === "civilians" || tab === "classification") return;
    if (!this.newMasterName.trim()) {
      this.notifications.error("Value is required.");
      return;
    }
    await firstValueFrom(this.api.addMasterEntry(tab, this.newMasterName.trim()));
    this.newMasterName = "";
    this.showAddMasterModal.set(false);
    await this.loadMasterList(tab);
  }

  async deleteMasterEntry(id: number): Promise<void> {
    const tab = this.referenceTab();
    if (tab === "civilians" || tab === "classification") return;
    if (!confirm("Delete this entry?")) return;
    await firstValueFrom(this.api.deleteMasterEntry(tab, id));
    await this.loadMasterList(tab);
  }

  // ── References — Junior/Senior Sailor Classification ─────────
  private async loadRankClassifications(): Promise<void> {
    const [entries] = await Promise.all([firstValueFrom(this.api.getRankClassifications()), this.loadRankOptions()]);
    this.rankClassifications.set(entries);
  }

  /** Shared with the Add Civilian/Officer modal's Rank field — loaded once, cheap to re-fetch. */
  private async loadRankOptions(): Promise<void> {
    const ranks: RankOption[] = await firstValueFrom(this.api.getRanks()).catch(() => []);
    this.rankOptions.set(ranks.map((rank) => ({ label: rank.name, value: rank.name })));
  }

  openAddClassificationModal(): void {
    this.newClassificationRank = null;
    this.newClassificationValue = "Junior";
    this.showAddClassificationModal.set(true);
    if (!this.rankOptions().length) void this.loadRankOptions();
  }

  async addClassification(): Promise<void> {
    if (!this.newClassificationRank || !this.newClassificationValue) {
      this.notifications.error("Rank and Classification are required.");
      return;
    }
    await firstValueFrom(this.api.addRankClassification(this.newClassificationRank, this.newClassificationValue));
    this.showAddClassificationModal.set(false);
    await this.loadRankClassifications();
  }

  async deleteClassification(id: number): Promise<void> {
    if (!confirm("Delete this classification entry?")) return;
    await firstValueFrom(this.api.deleteRankClassification(id));
    await this.loadRankClassifications();
  }

  // ── References — Civilian / Officer pool ─────────────────────
  private async loadCivilians(): Promise<void> {
    this.civilians.set(await firstValueFrom(this.api.getCivilians()));
  }

  selectCivilianType(type: PersonType): void {
    this.newCivilian.personType = type;
  }

  get selectedTypeUi(): PersonTypeUiConfig | null {
    const type = this.newCivilian.personType;
    return type === "civilian" ? null : PERSON_TYPE_UI[type];
  }

  openAddCivilianModal(): void {
    this.newCivilian = {
      name: "",
      personType: "civilian",
      role: "",
      desig: "",
      rank: "",
      serviceNo: "",
      fleet: "",
      ship: "",
      refId: "",
      contact: "",
      remarks: "",
    };
    this.showAddCivilianModal.set(true);
    if (!this.rankOptions().length) void this.loadRankOptions();
  }

  /** "Add Embarking Officers" reuses the same shared-pool modal as "Add Civilian", just
   * pre-selecting the Fleet Officer type — there's no separate embarking-officer concept on the
   * backend, `CivilianOfficial.person_type` already covers it. */
  openAddEmbarkingOfficerModal(): void {
    this.openAddCivilianModal();
    this.newCivilian.personType = "fleet_officer";
  }

  printDeptList(): void {
    const sailing = this.currentSailing();
    if (!sailing) return;
    const columns: PrintColumn[] = [
      { header: "Dept", field: "dept" },
      { header: "Rank", field: "rank" },
      { header: "Name", field: "name" },
      { header: "Personal No.", field: "pno" },
    ];
    this.exportService.printRows(
      `${sailing.name} — Full Department List`,
      columns,
      this.sailingPersonnelRows as unknown as Record<string, unknown>[],
    );
  }

  printBillPdf(): void {
    const sailing = this.currentSailing();
    if (!sailing) return;
    const columns: PrintColumn[] = [
      { header: "Dept", field: "dept" },
      { header: "Name", field: "name" },
      { header: "Rank", field: "rank" },
      { header: "Personal No", field: "pno" },
      ...this.assignmentFields.map((f) => ({ header: f.label, field: f.key as string })),
    ];
    this.exportService.printRows(
      `${sailing.name} — Watch and Station Bill`,
      columns,
      this.assignmentRows() as unknown as Record<string, unknown>[],
    );
  }

  private historyDetailRows(): SailingAssignmentRow[] {
    const detail = this.historyDetail();
    return detail ? Object.values(detail.departments).flat() : [];
  }

  printHistoryDeptList(): void {
    const detail = this.historyDetail();
    if (!detail) return;
    const columns: PrintColumn[] = [
      { header: "Dept", field: "dept" },
      { header: "Rank", field: "rank" },
      { header: "Name", field: "name" },
      { header: "Personal No.", field: "pno" },
    ];
    this.exportService.printRows(
      `${detail.name} — Full Department List`,
      columns,
      this.historyDetailRows() as unknown as Record<string, unknown>[],
    );
  }

  printHistoryBillPdf(): void {
    const detail = this.historyDetail();
    if (!detail) return;
    const columns: PrintColumn[] = [
      { header: "Dept", field: "dept" },
      { header: "Name", field: "name" },
      { header: "Rank", field: "rank" },
      { header: "Personal No", field: "pno" },
      ...this.assignmentFields.map((f) => ({ header: f.label, field: f.key as string })),
    ];
    this.exportService.printRows(
      `${detail.name} — Watch and Station Bill`,
      columns,
      this.historyDetailRows() as unknown as Record<string, unknown>[],
    );
  }

  async addCivilian(): Promise<void> {
    const form = this.newCivilian;
    if (!form.name.trim()) {
      this.notifications.error("Full Name is required.");
      return;
    }
    if (form.personType === "civilian") {
      if (!form.role.trim()) {
        this.notifications.error("Role / Designation is required.");
        return;
      }
    } else if (!form.desig.trim() || !form.rank.trim() || !form.serviceNo.trim()) {
      const ui = PERSON_TYPE_UI[form.personType];
      this.notifications.error(`${ui.appointmentLabel}, ${ui.rankLabel} and ${ui.serviceNoLabel} are required.`);
      return;
    }

    await firstValueFrom(
      this.api.addCivilian({
        name: form.name.trim(),
        personType: form.personType,
        role: form.role.trim(),
        desig: form.desig.trim() || undefined,
        rank: form.rank.trim() || undefined,
        serviceNo: form.serviceNo.trim() || undefined,
        fleet: form.fleet.trim() || undefined,
        ship: form.ship.trim() || undefined,
        refId: form.refId.trim() || undefined,
        contact: form.contact.trim() || undefined,
        remarks: form.remarks.trim() || undefined,
      }),
    );
    this.showAddCivilianModal.set(false);
    await this.loadCivilians();
  }

  async removeCivilian(id: number): Promise<void> {
    if (!confirm("Remove this person from the pool?")) return;
    await firstValueFrom(this.api.removeCivilian(id));
    await this.loadCivilians();
  }
}
