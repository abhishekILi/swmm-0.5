import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { CellCallbackParams, ColDef, RowData } from "ag-grid-community";
import { Call } from "../../../services/network/call";
import { NotificationService } from "../../../Core/services/notification/notification.service";
import { IconComponent } from "../../../shared/components/icon/icon.component";
import { ModalComponent } from "../../../shared/components/modal/modal.component";
import { MasterCard } from "../../refit-maintenance/master-card/master-card";
import { DataGrid } from "../../../shared/components/data-grid/data-grid";
import {
  AvailableUser,
  CHILD_TYPE,
  HierarchyNode,
  HierarchyNodeType,
  NODE_COLORS,
  NODE_LABELS,
  RawHierarchyNode,
} from "./divisional-organisation.model";

@Component({
  selector: "app-divisional-organisation",
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, ModalComponent, MasterCard, DataGrid],
  templateUrl: "./divisional-organisation.html",
  styleUrl: "./divisional-organisation.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DivisionalOrganisation implements OnInit {
  private readonly call = inject(Call);
  private readonly notify = inject(NotificationService);

  readonly nodeLabels = NODE_LABELS;
  readonly nodeColors = NODE_COLORS;

  readonly loading = signal(true);
  readonly hierarchy = signal<HierarchyNode | null>(null);
  readonly isEditMode = signal(false);
  readonly zoomLevel = signal(1);
  readonly panX = signal(0);
  readonly panY = signal(0);
  readonly isPanning = signal(false);
  private dragStartX = 0;
  private dragStartY = 0;
  private panStartX = 0;
  private panStartY = 0;

  // Node add/edit modal
  readonly showNodeModal = signal(false);
  readonly modalNodeType = signal<HierarchyNodeType | null>(null);
  readonly modalParentDbId = signal<number | null>(null);
  readonly modalEditingNode = signal<HierarchyNode | null>(null);
  readonly modalDivisionName = signal("");
  readonly modalSelectedUserId = signal<number | null>(null);
  readonly modalPhotoFile = signal<File | null>(null);
  readonly modalPhotoPreview = signal<string | null>(null);
  readonly modalUsers = signal<AvailableUser[]>([]);
  readonly modalError = signal("");
  readonly saving = signal(false);

  // Sailor list modal
  readonly showSailorModal = signal(false);
  readonly sailorModalDivision = signal<HierarchyNode | null>(null);

  readonly sailorColumnDefs = computed<ColDef[]>(() => {
    const columns: ColDef[] = [
      { field: "name", headerName: "Name", flex: 1 },
      { field: "rank", headerName: "Rank" },
      { field: "designation", headerName: "Designation" },
      { field: "personalNumber", headerName: "Personal Number" },
    ];
    if (!this.isEditMode()) return columns;

    return [
      ...columns,
      {
        field: "isRegulator",
        headerName: "Regulator",
        width: 110,
        sortable: false,
        filter: false,
        cellRenderer: (params: { value: boolean }) =>
          `<input type="checkbox" class="do-grid-checkbox" ${params.value ? "checked" : ""} readonly />`,
        onCellClicked: (params: CellCallbackParams) => {
          const sailor = params.data as HierarchyNode;
          this.toggleSailorRegulator(sailor, !sailor.isRegulator);
        },
      },
      {
        field: "id",
        headerName: "Actions",
        width: 100,
        sortable: false,
        filter: false,
        cellRenderer: () => `<button type="button" class="do-grid-delete-btn">Delete</button>`,
        onCellClicked: (params: CellCallbackParams) => {
          this.deleteNode(params.data as HierarchyNode);
        },
      },
    ];
  });

  // Add sailor modal
  readonly showAddSailorModal = signal(false);
  readonly addSailorDivision = signal<HierarchyNode | null>(null);
  readonly addSailorUsers = signal<AvailableUser[]>([]);
  readonly addSailorSearch = signal("");
  readonly addSailorSelectedRows = signal<AvailableUser[]>([]);

  readonly addSailorFilteredUsers = computed(() => {
    const search = this.addSailorSearch().trim().toLowerCase();
    if (!search) return this.addSailorUsers();
    return this.addSailorUsers().filter((u) =>
      [u.name, u.rank, u.designation, u.personal_number].some((v) =>
        (v || "").toLowerCase().includes(search),
      ),
    );
  });

  readonly addSailorColumnDefs: ColDef[] = [
    { field: "name", headerName: "Name", flex: 1 },
    { field: "rank", headerName: "Rank" },
    { field: "designation", headerName: "Designation" },
    { field: "personal_number", headerName: "Personal Number" },
  ];

  readonly modalTitle = computed(() => {
    const type = this.modalNodeType();
    if (!type) return "";
    return `${this.modalEditingNode() ? "Edit" : "Add"} ${this.nodeLabels[type]}`;
  });

  ngOnInit(): void {
    this.loadHierarchy();
  }

  async loadHierarchy(): Promise<void> {
    this.loading.set(true);
    try {
      const res = await firstValueFrom(this.call.getHierarchyTree());
      this.hierarchy.set(res.hierarchy ? this.hydrate(res.hierarchy) : null);
    } catch {
      this.notify.error("Failed to load divisional organisation.");
    } finally {
      this.loading.set(false);
    }
  }

  private hydrate(raw: RawHierarchyNode, depth = 0): HierarchyNode {
    return {
      id: "db-" + raw.dbId,
      dbId: raw.dbId,
      type: raw.type,
      name: raw.name || "",
      rank: raw.rank || "",
      designation: raw.designation || "",
      personalNumber: raw.personalNumber || "",
      photoUrl: this.resolvePhotoUrl(raw.photoUrl),
      divisionName: raw.divisionName || "",
      isRegulator: !!raw.isRegulator,
      selectedUserId: raw.selectedUserId ?? null,
      collapsed: depth > 2,
      children: (raw.children || []).map((c) => this.hydrate(c, depth + 1)),
    };
  }

  resolvePhotoUrl(url?: string | null): string | null {
    if (!url) return null;
    if (url.startsWith("http")) return url;
    return `${this.call.baseUrl}${url.replace(/^\//, "")}`;
  }

  toggleMode(): void {
    this.isEditMode.set(!this.isEditMode());
  }

  toggleCollapse(node: HierarchyNode): void {
    node.collapsed = !node.collapsed;
    this.hierarchy.set(this.hierarchy() ? { ...this.hierarchy()! } : null);
  }

  childType(type: HierarchyNodeType): HierarchyNodeType | undefined {
    return CHILD_TYPE[type];
  }

  colorFor(type: HierarchyNodeType): string {
    return NODE_COLORS[type];
  }

  labelFor(type: HierarchyNodeType | undefined): string {
    return type ? NODE_LABELS[type] : "";
  }

  zoomIn(): void {
    this.zoomLevel.set(Math.min(this.zoomLevel() + 0.1, 3));
  }

  zoomOut(): void {
    this.zoomLevel.set(Math.max(this.zoomLevel() - 0.1, 0.3));
  }

  resetZoom(): void {
    this.zoomLevel.set(1);
    this.panX.set(0);
    this.panY.set(0);
  }

  onWheelZoom(event: WheelEvent): void {
    event.preventDefault();
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    const oldZoom = this.zoomLevel();
    const contentX = (mouseX - this.panX()) / oldZoom;
    const contentY = (mouseY - this.panY()) / oldZoom;

    const delta = event.deltaY < 0 ? 0.1 : -0.1;
    const newZoom = Math.min(Math.max(oldZoom + delta, 0.3), 3);

    this.zoomLevel.set(newZoom);
    this.panX.set(mouseX - contentX * newZoom);
    this.panY.set(mouseY - contentY * newZoom);
  }

  onCanvasMouseDown(event: MouseEvent): void {
    this.isPanning.set(true);
    this.dragStartX = event.clientX;
    this.dragStartY = event.clientY;
    this.panStartX = this.panX();
    this.panStartY = this.panY();
  }

  onCanvasMouseMove(event: MouseEvent): void {
    if (!this.isPanning()) return;
    this.panX.set(this.panStartX + (event.clientX - this.dragStartX));
    this.panY.set(this.panStartY + (event.clientY - this.dragStartY));
  }

  onCanvasMouseUp(): void {
    this.isPanning.set(false);
  }

  onPhotoError(node: HierarchyNode): void {
    node.photoUrl = null;
  }

  // ── Add / Edit node modal ──────────────────────────────────────────
  addCO(): void {
    if (this.hierarchy()) {
      this.notify.warning("A Commanding Officer already exists.");
      return;
    }
    this.openNodeModal("co", null, null);
  }

  addChild(parent: HierarchyNode): void {
    const type = this.childType(parent.type);
    if (!type) return;
    this.openNodeModal(type, parent.dbId, null);
  }

  editNode(node: HierarchyNode): void {
    this.openNodeModal(node.type, null, node);
  }

  private async openNodeModal(
    type: HierarchyNodeType,
    parentDbId: number | null,
    editing: HierarchyNode | null,
  ): Promise<void> {
    this.modalNodeType.set(type);
    this.modalParentDbId.set(parentDbId);
    this.modalEditingNode.set(editing);
    this.modalDivisionName.set(editing?.divisionName || "");
    this.modalSelectedUserId.set(editing?.selectedUserId ?? null);
    this.modalPhotoFile.set(null);
    this.modalPhotoPreview.set(editing?.photoUrl || null);
    this.modalError.set("");
    this.modalUsers.set([]);
    this.showNodeModal.set(true);

    if (type !== "division") {
      try {
        const res = await firstValueFrom(
          this.call.getAvailableHierarchyUsers(editing?.dbId ?? undefined),
        );
        this.modalUsers.set(res.users || []);
      } catch {
        this.notify.error("Failed to load available personnel.");
      }
    }
  }

  closeNodeModal(): void {
    this.showNodeModal.set(false);
    this.modalNodeType.set(null);
    this.modalEditingNode.set(null);
  }

  onPhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.modalPhotoFile.set(file);
    if (file) {
      const reader = new FileReader();
      reader.onload = () => this.modalPhotoPreview.set(reader.result as string);
      reader.readAsDataURL(file);
    }
  }

  selectedUserDetails(): AvailableUser | undefined {
    return this.modalUsers().find((u) => u.id === this.modalSelectedUserId());
  }

  async saveNode(): Promise<void> {
    const type = this.modalNodeType();
    if (!type) return;

    if (type === "division") {
      if (!this.modalDivisionName().trim()) {
        this.modalError.set("Division name is required.");
        return;
      }
    } else if (!this.modalSelectedUserId()) {
      this.modalError.set("Please select a name.");
      return;
    }

    const formData = new FormData();
    formData.set("node_type", type);
    formData.set("is_commander_officer", type === "co" ? "1" : "0");

    const isEditing = !!this.modalEditingNode()?.dbId;
    if (!isEditing && this.modalParentDbId()) {
      formData.set("parent", String(this.modalParentDbId()));
    }

    if (type === "division") {
      formData.set("division_name", this.modalDivisionName().trim());
    } else {
      formData.set("user", String(this.modalSelectedUserId()));
    }

    const photo = this.modalPhotoFile();
    if (photo) formData.append("photo", photo);

    this.saving.set(true);
    try {
      const editing = this.modalEditingNode();
      if (editing?.dbId) {
        await firstValueFrom(this.call.updateHierarchyNode(editing.dbId, formData));
      } else {
        await firstValueFrom(this.call.createHierarchyNode(formData));
      }
      this.notify.success("Saved successfully.");
      this.closeNodeModal();
      await this.loadHierarchy();
    } catch {
      this.notify.error("Failed to save. Please try again.");
    } finally {
      this.saving.set(false);
    }
  }

  async deleteNode(node: HierarchyNode, event?: Event): Promise<void> {
    event?.stopPropagation();
    if (!node.dbId) return;
    if (!confirm(`Delete this ${this.nodeLabels[node.type]}? This will also remove everything below it.`)) return;

    try {
      await firstValueFrom(this.call.deleteHierarchyNode(node.dbId));
      this.notify.success("Deleted successfully.");
      await this.loadHierarchy();
    } catch {
      this.notify.error("Failed to delete.");
    }
  }

  // ── Sailor list modal (per division) ───────────────────────────────
  openSailorModal(division: HierarchyNode, event: Event): void {
    event.stopPropagation();
    this.sailorModalDivision.set(division);
    this.showSailorModal.set(true);
  }

  closeSailorModal(): void {
    this.showSailorModal.set(false);
    this.sailorModalDivision.set(null);
  }

  async toggleSailorRegulator(sailor: HierarchyNode, checked: boolean): Promise<void> {
    if (!sailor.dbId) return;
    try {
      await firstValueFrom(this.call.toggleSailorRegulator(sailor.dbId, checked));
      sailor.isRegulator = checked;
      this.notify.success("Regulator status updated.");
    } catch {
      this.notify.error("Failed to update regulator status.");
    }
  }

  // ── Add sailor(s) to a division ─────────────────────────────────────
  async openAddSailorModal(division: HierarchyNode): Promise<void> {
    this.addSailorDivision.set(division);
    this.addSailorSearch.set("");
    this.addSailorSelectedRows.set([]);
    this.showAddSailorModal.set(true);
    try {
      const res = await firstValueFrom(this.call.getAvailableHierarchyUsers());
      this.addSailorUsers.set(res.users || []);
    } catch {
      this.notify.error("Failed to load available personnel.");
    }
  }

  closeAddSailorModal(): void {
    this.showAddSailorModal.set(false);
    this.addSailorDivision.set(null);
  }

  onAddSailorSelectionChanged(rows: RowData[]): void {
    this.addSailorSelectedRows.set(rows as unknown as AvailableUser[]);
  }

  async confirmAddSailors(): Promise<void> {
    const division = this.addSailorDivision();
    const selected = this.addSailorSelectedRows();
    if (!division?.dbId || selected.length === 0) return;

    this.saving.set(true);
    try {
      for (const user of selected) {
        const formData = new FormData();
        formData.set("node_type", "sailor");
        formData.set("user", String(user.id));
        formData.set("parent", String(division.dbId));
        formData.set("is_commander_officer", "0");
        await firstValueFrom(this.call.createHierarchyNode(formData));
      }
      this.notify.success("Sailor(s) added.");
      this.closeAddSailorModal();
      await this.loadHierarchy();
    } catch {
      this.notify.error("Failed to add sailor(s).");
    } finally {
      this.saving.set(false);
    }
  }
}
