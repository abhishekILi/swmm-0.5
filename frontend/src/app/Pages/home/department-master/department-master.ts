import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { ColDef, RowData } from "ag-grid-community";
import { Call } from "../../../services/network/call";
import { NotificationService } from "../../../Core/services/notification/notification.service";
import { ModalComponent } from "../../../shared/components/modal/modal.component";
import { MasterCard } from "../../refit-maintenance/master-card/master-card";
import { IconComponent } from "../../../shared/components/icon/icon.component";
import { ExportToolbar } from "../../../shared/components/export-toolbar/export-toolbar";
import { DataGrid } from "../../../shared/components/data-grid/data-grid";
import { ActionRendererComponent } from "../../../shared/components/data-grid/grid-action-icons";
import {
  CoMessageApi,
  CommandMessage,
  CrewDetail,
  LoginPageImage,
  LoginPageImageApi,
  MasterNavGroup,
  MemberDetailApi,
  QuoteApi,
  QuoteOfTheDay,
  ShipRole,
  ShipRoleApi,
  UpcomingEvent,
  UpcomingEventApi,
} from "./department-master.model";

function toCrewDetail(api: MemberDetailApi, serNo: number): CrewDetail {
  return {
    id: api.id,
    serNo,
    fullName: api.name,
    designation: api.designation,
    rank: api.rank,
    image: api.image_path,
  };
}

function toQuoteOfTheDay(api: QuoteApi, serNo: number): QuoteOfTheDay {
  return {
    id: api.id,
    serNo,
    quote: api.quoteText,
    uploadedDate: api.addedDate,
    active: api.is_active,
  };
}

function toCommandMessage(api: CoMessageApi, serNo: number): CommandMessage {
  return {
    id: api.id,
    serNo,
    message: api.message,
    uploadedDate: api.uploaded_date,
    validTillDate: api.valid_till_date,
  };
}

function toUpcomingEvent(api: UpcomingEventApi, serNo: number): UpcomingEvent {
  return {
    id: api.id,
    serNo,
    eventName: api.title,
    startDate: api.start_date,
    endDate: api.end_date,
    document: api.document,
    uploadedDate: api.created_at,
  };
}

function toLoginPageImage(api: LoginPageImageApi): LoginPageImage {
  return {
    id: api.id,
    image: api.image,
    uploadedAt: api.uploaded_at,
  };
}

function toShipRole(api: ShipRoleApi, serNo: number): ShipRole {
  return {
    id: api.id,
    serNo,
    title: api.role_title ?? "",
    description: api.current_text,
    uploadedDate: api.uploaded_date,
    images: api.images,
  };
}

@Component({
  selector: "app-department-master",
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent, MasterCard, IconComponent, ExportToolbar, DataGrid],
  templateUrl: "./department-master.html",
  styleUrl: "./department-master.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DepartmentMasterComponent implements OnInit {
  private readonly call = inject(Call);
  private readonly notify = inject(NotificationService);

  readonly navGroups: MasterNavGroup[] = [
    {
      title: "Dashboard",
      items: [
        { key: "quote-of-the-day", label: "Quote of The Day", icon: "message-square-text" },
        { key: "ship-role", label: "Ship Role", icon: "ship" },
        { key: "message-from-command", label: "Message From Command", icon: "send" },
        { key: "upcoming-event-updates", label: "Upcoming Event Updates", icon: "bell" },
        { key: "crew-details", label: "Crew Details", icon: "users" },
      ],
    },
    {
      title: "Login Page",
      items: [{ key: "login-page-image", label: "Login Page Image", icon: "image" }],
    },
  ];

  readonly activeKey = signal("crew-details");

  readonly activeLabel = computed(
    () => this.navGroups.flatMap((g) => g.items).find((i) => i.key === this.activeKey())?.label ?? "",
  );

  readonly searchText = signal("");
  readonly pageSize = signal(10);

  readonly crewLoading = signal(true);
  readonly crewList = signal<CrewDetail[]>([]);

  readonly filteredCrew = computed(() => {
    const search = this.searchText().trim().toLowerCase();
    const rows = this.crewList();
    if (!search) return rows;
    return rows.filter((c) =>
      [c.fullName, c.designation, c.rank].some((v) => v.toLowerCase().includes(search)),
    );
  });

  readonly crewColumnDefs: ColDef[] = [
    { field: "serNo", headerName: "Ser No.", maxWidth: 100 },
    { field: "fullName", headerName: "Full Name", flex: 2, minWidth: 180 },
    { field: "designation", headerName: "Designation", flex: 2, minWidth: 160 },
    { field: "rank", headerName: "Rank", flex: 1, minWidth: 140 },
    {
      field: "image",
      headerName: "Image",
      maxWidth: 110,
      sortable: false,
      filter: false,
      cellRenderer: (params: { value: string | null }) =>
        params.value
          ? `<img src="${params.value}" alt="" style="width:64px;height:40px;border-radius:6px;object-fit:cover;" />`
          : "-",
    },
    {
      headerName: "Actions",
      minWidth: 110,
      maxWidth: 110,
      sortable: false,
      filter: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: RowData) => [
          {
            icon: "edit",
            label: "Edit",
            color: "#2563eb",
            action: () => this.openEditModal(row as unknown as CrewDetail),
          },
          {
            icon: "delete",
            label: "Delete",
            color: "#dc2626",
            action: () => this.deleteCrew(row as unknown as CrewDetail),
          },
        ],
      },
    },
  ];

  readonly showFormModal = signal(false);
  readonly editingCrew = signal<CrewDetail | null>(null);
  readonly formFullName = signal("");
  readonly formDesignation = signal("");
  readonly formRank = signal("");
  readonly formCrewImage = signal<File | null>(null);
  readonly formError = signal("");
  readonly savingCrew = signal(false);

  readonly quoteLoading = signal(true);
  readonly quoteList = signal<QuoteOfTheDay[]>([]);

  readonly quoteColumnDefs: ColDef[] = [
    { field: "serNo", headerName: "Ser No.", maxWidth: 100, filter: false },
    { field: "quote", headerName: "Quote", flex: 2, minWidth: 220, filter: "agTextColumnFilter", floatingFilter: true },
    {
      field: "uploadedDate",
      headerName: "Uploaded Date",
      flex: 1,
      minWidth: 160,
      filter: "agTextColumnFilter",
      floatingFilter: true,
    },
    {
      headerName: "Actions",
      minWidth: 150,
      maxWidth: 150,
      sortable: false,
      filter: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: RowData) => {
          const quote = row as unknown as QuoteOfTheDay;
          return [
            {
              icon: quote.active ? "ban" : "check",
              label: quote.active ? "Active" : "Activate",
              color: quote.active ? "#F82C36" : "#16a34a",
              action: () => this.activateQuote(quote),
              disabled: quote.active,
            },
            {
              icon: "edit",
              label: "Edit",
              color: "#2563eb",
              action: () => this.openEditQuoteModal(quote),
            },
            {
              icon: "delete",
              label: "Delete",
              color: "#dc2626",
              action: () => this.deleteQuote(quote),
            },
          ];
        },
      },
    },
  ];

  readonly showQuoteModal = signal(false);
  readonly editingQuote = signal<QuoteOfTheDay | null>(null);
  readonly formQuote = signal("");
  readonly quoteFormError = signal("");
  readonly savingQuote = signal(false);

  readonly MAX_SHIP_ROLE_IMAGES = 5;
  readonly shipRoleLoading = signal(true);
  readonly shipRoleList = signal<ShipRole[]>([]);

  readonly shipRoleColumnDefs: ColDef[] = [
    { field: "serNo", headerName: "Ser No.", maxWidth: 100, filter: false },
    { field: "title", headerName: "Ship Role Title", flex: 2, minWidth: 180, filter: "agTextColumnFilter", floatingFilter: true },
    { field: "description", headerName: "Description", flex: 2, minWidth: 220, filter: "agTextColumnFilter", floatingFilter: true },
    {
      field: "uploadedDate",
      headerName: "Uploaded Date",
      flex: 1,
      minWidth: 160,
      filter: "agTextColumnFilter",
      floatingFilter: true,
    },
    {
      field: "images",
      headerName: "Images",
      maxWidth: 100,
      sortable: false,
      filter: false,
      cellRenderer: (params: { value: { image: string }[] }) =>
        params.value?.length
          ? `<img src="${params.value[0].image}" alt="" style="width:28px;height:28px;border-radius:6px;object-fit:cover;" />`
          : "-",
    },
    {
      headerName: "Actions",
      minWidth: 120,
      maxWidth: 120,
      sortable: false,
      filter: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: RowData) => [
          {
            icon: "edit",
            label: "Edit",
            color: "#2563eb",
            action: () => this.openEditShipRoleModal(row as unknown as ShipRole),
          },
          {
            icon: "view",
            label: "Preview",
            color: "#2563eb",
            action: () => this.openImagePreview(row as unknown as ShipRole),
          },
          {
            icon: "delete",
            label: "Delete",
            color: "#dc2626",
            action: () => this.deleteShipRole(row as unknown as ShipRole),
          },
        ],
      },
    },
  ];

  readonly commandMessageLoading = signal(true);
  readonly commandMessageList = signal<CommandMessage[]>([]);

  readonly commandMessageColumnDefs: ColDef[] = [
    { field: "serNo", headerName: "Ser No.", maxWidth: 100, filter: false },
    {
      field: "message",
      headerName: "Command Message",
      flex: 2,
      minWidth: 220,
      filter: "agTextColumnFilter",
      floatingFilter: true,
    },
    {
      field: "uploadedDate",
      headerName: "Uploaded Date",
      flex: 1,
      minWidth: 160,
      filter: "agTextColumnFilter",
      floatingFilter: true,
    },
    {
      field: "validTillDate",
      headerName: "Valid Till",
      flex: 1,
      minWidth: 160,
      filter: "agTextColumnFilter",
      floatingFilter: true,
    },
    {
      headerName: "Actions",
      minWidth: 120,
      maxWidth: 120,
      sortable: false,
      filter: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: RowData) => [
          {
            icon: "edit",
            label: "Edit",
            color: "#2563eb",
            action: () => this.openEditCommandMessageModal(row as unknown as CommandMessage),
          },
          {
            icon: "delete",
            label: "Delete",
            color: "#dc2626",
            action: () => this.deleteCommandMessage(row as unknown as CommandMessage),
          },
        ],
      },
    },
  ];

  readonly showCommandMessageModal = signal(false);
  readonly editingCommandMessage = signal<CommandMessage | null>(null);
  readonly formCommandMessage = signal("");
  readonly formCommandMessageValidTill = signal("");
  readonly commandMessageFormError = signal("");
  readonly savingCommandMessage = signal(false);

  readonly eventLoading = signal(true);
  readonly eventList = signal<UpcomingEvent[]>([]);

  readonly eventColumnDefs: ColDef[] = [
    { field: "serNo", headerName: "Ser No.", maxWidth: 100, filter: false },
    { field: "eventName", headerName: "Event Name", flex: 2, minWidth: 200, filter: "agTextColumnFilter", floatingFilter: true },
    {
      field: "uploadedDate",
      headerName: "Uploaded Date",
      flex: 1,
      minWidth: 160,
      filter: "agTextColumnFilter",
      floatingFilter: true,
    },
    {
      headerName: "Event Date",
      flex: 1,
      minWidth: 160,
      filter: "agTextColumnFilter",
      floatingFilter: true,
      valueGetter: (params: { data: unknown }) => {
        const row = params.data as UpcomingEvent;
        return row.endDate && row.endDate !== row.startDate
          ? `${row.startDate} - ${row.endDate}`
          : row.startDate;
      },
    },
    {
      headerName: "Actions",
      minWidth: 150,
      maxWidth: 150,
      sortable: false,
      filter: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: RowData) => [
          {
            icon: "view",
            label: "Preview",
            color: "#2563eb",
            action: () => this.openEventPreview(row as unknown as UpcomingEvent),
          },
          {
            icon: "edit",
            label: "Edit",
            color: "#2563eb",
            action: () => this.openEditEventModal(row as unknown as UpcomingEvent),
          },
          {
            icon: "delete",
            label: "Delete",
            color: "#dc2626",
            action: () => this.deleteEvent(row as unknown as UpcomingEvent),
          },
        ],
      },
    },
  ];

  readonly showEventModal = signal(false);
  readonly editingEvent = signal<UpcomingEvent | null>(null);
  readonly eventDayType = signal<"single" | "multiple">("single");
  readonly formEventDate = signal("");
  readonly formEventStartDate = signal("");
  readonly formEventEndDate = signal("");
  readonly formEventName = signal("");
  readonly formEventDocument = signal<File | null>(null);
  readonly eventFormError = signal("");
  readonly savingEvent = signal(false);

  readonly showEventPreviewModal = signal(false);
  readonly previewEvent = signal<UpcomingEvent | null>(null);

  readonly showImagePreviewModal = signal(false);
  readonly previewShipRole = signal<ShipRole | null>(null);

  readonly showShipRoleModal = signal(false);
  readonly editingShipRole = signal<ShipRole | null>(null);
  readonly formShipRoleTitle = signal("");
  readonly formShipRoleDescription = signal("");
  readonly formShipRoleImages = signal<File[]>([]);
  readonly shipRoleFormError = signal("");
  readonly savingShipRole = signal(false);

  readonly loginImageLoading = signal(true);
  readonly loginImageList = signal<LoginPageImage[]>([]);
  readonly currentLoginImage = computed(() => this.loginImageList()[0] ?? null);

  readonly showLoginImageModal = signal(false);
  readonly formLoginImage = signal<File | null>(null);
  readonly loginImageFormError = signal("");
  readonly savingLoginImage = signal(false);

  ngOnInit(): void {
    void this.loadCrewList();
    void this.loadQuotes();
    void this.loadShipRoles();
    void this.loadCommandMessages();
    void this.loadEvents();
    void this.loadLoginImages();
  }

  async loadCrewList(): Promise<void> {
    this.crewLoading.set(true);
    try {
      const res = await firstValueFrom(this.call.getMemberDetails());
      this.crewList.set((res || []).map((api, idx) => toCrewDetail(api, idx + 1)));
    } catch {
      this.notify.error("Failed to load crew details.");
    } finally {
      this.crewLoading.set(false);
    }
  }

  async loadQuotes(): Promise<void> {
    this.quoteLoading.set(true);
    try {
      const res = await firstValueFrom(this.call.getQuotes());
      this.quoteList.set((res || []).map((api, idx) => toQuoteOfTheDay(api, idx + 1)));
    } catch {
      this.notify.error("Failed to load quotes.");
    } finally {
      this.quoteLoading.set(false);
    }
  }

  async loadShipRoles(): Promise<void> {
    this.shipRoleLoading.set(true);
    try {
      const res = await firstValueFrom(this.call.getShipRoles());
      this.shipRoleList.set((res || []).map((api, idx) => toShipRole(api, idx + 1)));
    } catch {
      this.notify.error("Failed to load ship roles.");
    } finally {
      this.shipRoleLoading.set(false);
    }
  }

  async loadLoginImages(): Promise<void> {
    this.loginImageLoading.set(true);
    try {
      const res = await firstValueFrom(this.call.getLoginPageImages());
      this.loginImageList.set((res || []).map((api) => toLoginPageImage(api)));
    } catch {
      this.notify.error("Failed to load login page image.");
    } finally {
      this.loginImageLoading.set(false);
    }
  }

  openAddLoginImageModal(): void {
    this.formLoginImage.set(null);
    this.loginImageFormError.set("");
    this.showLoginImageModal.set(true);
  }

  closeLoginImageModal(): void {
    this.showLoginImageModal.set(false);
  }

  onLoginImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.formLoginImage.set(input.files?.[0] ?? null);
  }

  async saveLoginImage(): Promise<void> {
    const file = this.formLoginImage();
    if (!file) {
      this.loginImageFormError.set("Please select an image.");
      return;
    }

    const payload = new FormData();
    payload.append("image", file);
    // DRF's BooleanField treats a missing key as `false` for multipart/HTML
    // form input (mimicking an unticked checkbox) instead of falling back to
    // the model's `default=True` — so this must be sent explicitly.
    payload.append("is_active", "true");

    this.savingLoginImage.set(true);
    try {
      let created = await firstValueFrom(this.call.createLoginPageImage(payload));
      if (!created.is_active) {
        const activatePayload = new FormData();
        activatePayload.append("is_active", "true");
        created = await firstValueFrom(this.call.updateLoginPageImage(created.id, activatePayload));
      }
      this.loginImageList.set([toLoginPageImage(created), ...this.loginImageList()]);
      this.notify.success("Login page image updated.");
      this.closeLoginImageModal();
      await this.loadLoginImages();
    } catch (err) {
      this.notify.error(this.extractErrorMessage(err, "Failed to upload login page image."));
    } finally {
      this.savingLoginImage.set(false);
    }
  }

  private extractErrorMessage(err: unknown, fallback: string): string {
    const httpError = err as { error?: { detail?: string; message?: string } };
    return httpError?.error?.detail ?? httpError?.error?.message ?? fallback;
  }

  async loadCommandMessages(): Promise<void> {
    this.commandMessageLoading.set(true);
    try {
      const res = await firstValueFrom(this.call.getCoMessages());
      this.commandMessageList.set((res || []).map((api, idx) => toCommandMessage(api, idx + 1)));
    } catch {
      this.notify.error("Failed to load command messages.");
    } finally {
      this.commandMessageLoading.set(false);
    }
  }

  async loadEvents(): Promise<void> {
    this.eventLoading.set(true);
    try {
      const res = await firstValueFrom(this.call.getEvents());
      this.eventList.set((res || []).map((api, idx) => toUpcomingEvent(api, idx + 1)));
    } catch {
      this.notify.error("Failed to load upcoming event updates.");
    } finally {
      this.eventLoading.set(false);
    }
  }

  selectNav(key: string): void {
    this.activeKey.set(key);
  }

  openAddModal(): void {
    this.editingCrew.set(null);
    this.formFullName.set("");
    this.formDesignation.set("");
    this.formRank.set("");
    this.formCrewImage.set(null);
    this.formError.set("");
    this.showFormModal.set(true);
  }

  openEditModal(crew: CrewDetail): void {
    this.editingCrew.set(crew);
    this.formFullName.set(crew.fullName);
    this.formDesignation.set(crew.designation);
    this.formRank.set(crew.rank);
    this.formCrewImage.set(null);
    this.formError.set("");
    this.showFormModal.set(true);
  }

  closeFormModal(): void {
    this.showFormModal.set(false);
  }

  onCrewImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.formCrewImage.set(input.files?.[0] ?? null);
  }

  async saveCrew(): Promise<void> {
    if (!this.formFullName().trim()) {
      this.formError.set("Full name is required.");
      return;
    }
    if (!this.formDesignation().trim()) {
      this.formError.set("Designation is required.");
      return;
    }
    if (!this.formRank().trim()) {
      this.formError.set("Rank is required.");
      return;
    }

    const payload = new FormData();
    payload.append("name", this.formFullName().trim());
    payload.append("designation", this.formDesignation().trim());
    payload.append("rank", this.formRank().trim());
    if (this.formCrewImage()) {
      payload.append("image", this.formCrewImage() as File);
    }

    this.savingCrew.set(true);
    try {
      const editing = this.editingCrew();
      if (editing) {
        await firstValueFrom(this.call.updateMemberDetail(editing.id, payload));
      } else {
        await firstValueFrom(this.call.createMemberDetail(payload));
      }
      // this.notify.success("Saved successfully.");
      this.closeFormModal();
      await this.loadCrewList();
    } catch {
      this.notify.error("Failed to save crew details.");
    } finally {
      this.savingCrew.set(false);
    }
  }

  async deleteCrew(crew: CrewDetail): Promise<void> {
    if (!confirm(`Delete crew member "${crew.fullName}"?`)) return;
    try {
      await firstValueFrom(this.call.deleteMemberDetail(crew.id));
      this.notify.success("Crew member deleted.");
      await this.loadCrewList();
    } catch {
      this.notify.error("Failed to delete crew member.");
    }
  }

  openAddQuoteModal(): void {
    this.editingQuote.set(null);
    this.formQuote.set("");
    this.quoteFormError.set("");
    this.showQuoteModal.set(true);
  }

  openEditQuoteModal(quote: QuoteOfTheDay): void {
    this.editingQuote.set(quote);
    this.formQuote.set(quote.quote);
    this.quoteFormError.set("");
    this.showQuoteModal.set(true);
  }

  closeQuoteModal(): void {
    this.showQuoteModal.set(false);
  }

  async saveQuote(): Promise<void> {
    if (!this.formQuote().trim()) {
      this.quoteFormError.set("Quote is required.");
      return;
    }

    const payload = { quoteText: this.formQuote().trim() };

    this.savingQuote.set(true);
    try {
      const editing = this.editingQuote();
      if (editing) {
        await firstValueFrom(this.call.updateQuote(editing.id, payload));
      } else {
        await firstValueFrom(this.call.createQuote(payload));
      }
      // this.notify.success("Saved successfully.");
      this.closeQuoteModal();
      await this.loadQuotes();
    } catch {
      this.notify.error("Failed to save quote.");
    } finally {
      this.savingQuote.set(false);
    }
  }

  async deleteQuote(quote: QuoteOfTheDay): Promise<void> {
    if (!confirm("Delete this quote?")) return;
    try {
      await firstValueFrom(this.call.deleteQuote(quote.id));
      this.notify.success("Quote deleted.");
      await this.loadQuotes();
    } catch {
      this.notify.error("Failed to delete quote.");
    }
  }

  async activateQuote(quote: QuoteOfTheDay): Promise<void> {
    try {
      await firstValueFrom(this.call.activateQuote(quote.id));
      await this.loadQuotes();
    } catch {
      this.notify.error("Failed to activate quote.");
    }
  }

  openAddCommandMessageModal(): void {
    this.editingCommandMessage.set(null);
    this.formCommandMessage.set("");
    this.formCommandMessageValidTill.set("");
    this.commandMessageFormError.set("");
    this.showCommandMessageModal.set(true);
  }

  openEditCommandMessageModal(message: CommandMessage): void {
    this.editingCommandMessage.set(message);
    this.formCommandMessage.set(message.message);
    this.formCommandMessageValidTill.set(message.validTillDate);
    this.commandMessageFormError.set("");
    this.showCommandMessageModal.set(true);
  }

  closeCommandMessageModal(): void {
    this.showCommandMessageModal.set(false);
  }

  async saveCommandMessage(): Promise<void> {
    if (!this.formCommandMessage().trim()) {
      this.commandMessageFormError.set("Command message is required.");
      return;
    }
    if (!this.formCommandMessageValidTill()) {
      this.commandMessageFormError.set("Valid till date is required.");
      return;
    }

    const payload = {
      message: this.formCommandMessage().trim(),
      valid_till_date: this.formCommandMessageValidTill(),
    };

    this.savingCommandMessage.set(true);
    try {
      const editing = this.editingCommandMessage();
      if (editing) {
        await firstValueFrom(this.call.updateCoMessage(editing.id, payload));
      } else {
        await firstValueFrom(this.call.createCoMessage(payload));
      }
      // this.notify.success("Saved successfully.");
      this.closeCommandMessageModal();
      await this.loadCommandMessages();
    } catch {
      this.notify.error("Failed to save command message.");
    } finally {
      this.savingCommandMessage.set(false);
    }
  }

  async deleteCommandMessage(message: CommandMessage): Promise<void> {
    if (!confirm("Delete this command message?")) return;
    try {
      await firstValueFrom(this.call.deleteCoMessage(message.id));
      this.notify.success("Command message deleted.");
      await this.loadCommandMessages();
    } catch {
      this.notify.error("Failed to delete command message.");
    }
  }

  openAddEventModal(): void {
    this.editingEvent.set(null);
    this.eventDayType.set("single");
    this.formEventDate.set("");
    this.formEventStartDate.set("");
    this.formEventEndDate.set("");
    this.formEventName.set("");
    this.formEventDocument.set(null);
    this.eventFormError.set("");
    this.showEventModal.set(true);
  }

  openEditEventModal(event: UpcomingEvent): void {
    this.editingEvent.set(event);
    const isMultiple = !!event.endDate && event.endDate !== event.startDate;
    this.eventDayType.set(isMultiple ? "multiple" : "single");
    this.formEventDate.set(event.startDate);
    this.formEventStartDate.set(event.startDate);
    this.formEventEndDate.set(event.endDate ?? "");
    this.formEventName.set(event.eventName);
    this.formEventDocument.set(null);
    this.eventFormError.set("");
    this.showEventModal.set(true);
  }

  closeEventModal(): void {
    this.showEventModal.set(false);
  }

  setEventDayType(type: "single" | "multiple"): void {
    this.eventDayType.set(type);
    this.eventFormError.set("");
  }

  onEventDocumentSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.formEventDocument.set(input.files?.[0] ?? null);
  }

  async saveEvent(): Promise<void> {
    const isMultiple = this.eventDayType() === "multiple";

    if (!this.formEventName().trim()) {
      this.eventFormError.set("Event name is required.");
      return;
    }
    if (isMultiple && (!this.formEventStartDate() || !this.formEventEndDate())) {
      this.eventFormError.set("Date range is required.");
      return;
    }
    if (isMultiple && this.formEventEndDate() < this.formEventStartDate()) {
      this.eventFormError.set("End date cannot be less than start date.");
      return;
    }
    if (!isMultiple && !this.formEventDate()) {
      this.eventFormError.set("Date is required.");
      return;
    }

    const payload = new FormData();
    payload.append("title", this.formEventName().trim());
    payload.append("start_date", isMultiple ? this.formEventStartDate() : this.formEventDate());
    if (isMultiple) {
      payload.append("end_date", this.formEventEndDate());
    }
    payload.append("start_time", "00:00:00");
    payload.append("category", "others");
    if (this.formEventDocument()) {
      payload.append("document", this.formEventDocument() as File);
    }

    this.savingEvent.set(true);
    try {
      const editing = this.editingEvent();
      if (editing) {
        await firstValueFrom(this.call.updateEvent(editing.id, payload));
      } else {
        await firstValueFrom(this.call.createEvent(payload));
      }
      this.notify.success("Saved successfully.");
      this.closeEventModal();
      await this.loadEvents();
    } catch {
      this.notify.error("Failed to save event.");
    } finally {
      this.savingEvent.set(false);
    }
  }

  async deleteEvent(event: UpcomingEvent): Promise<void> {
    if (!confirm(`Delete event "${event.eventName}"?`)) return;
    try {
      await firstValueFrom(this.call.deleteEvent(event.id));
      this.notify.success("Event deleted.");
      await this.loadEvents();
    } catch {
      this.notify.error("Failed to delete event.");
    }
  }

  isImageDocument(url: string | null): boolean {
    if (!url) return false;
    return /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(url.split("?")[0]);
  }

  openEventPreview(event: UpcomingEvent): void {
    this.previewEvent.set(event);
    this.showEventPreviewModal.set(true);
  }

  closeEventPreview(): void {
    this.showEventPreviewModal.set(false);
  }

  openImagePreview(role: ShipRole): void {
    this.previewShipRole.set(role);
    this.showImagePreviewModal.set(true);
  }

  closeImagePreview(): void {
    this.showImagePreviewModal.set(false);
  }

  openAddShipRoleModal(): void {
    this.editingShipRole.set(null);
    this.formShipRoleTitle.set("");
    this.formShipRoleDescription.set("");
    this.formShipRoleImages.set([]);
    this.shipRoleFormError.set("");
    this.showShipRoleModal.set(true);
  }

  openEditShipRoleModal(role: ShipRole): void {
    this.editingShipRole.set(role);
    this.formShipRoleTitle.set(role.title);
    this.formShipRoleDescription.set(role.description);
    this.formShipRoleImages.set([]);
    this.shipRoleFormError.set("");
    this.showShipRoleModal.set(true);
  }

  closeShipRoleModal(): void {
    this.showShipRoleModal.set(false);
  }

  onShipRoleImagesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (files.length > this.MAX_SHIP_ROLE_IMAGES) {
      this.shipRoleFormError.set(`You can upload a maximum of ${this.MAX_SHIP_ROLE_IMAGES} images.`);
      input.value = "";
      return;
    }
    this.shipRoleFormError.set("");
    this.formShipRoleImages.set(files);
  }

  async saveShipRole(): Promise<void> {
    if (!this.formShipRoleTitle().trim()) {
      this.shipRoleFormError.set("Ship Role Title is required.");
      return;
    }
    if (!this.formShipRoleDescription().trim()) {
      this.shipRoleFormError.set("Description is required.");
      return;
    }

    const payload = new FormData();
    payload.append("role_title", this.formShipRoleTitle().trim());
    payload.append("current_text", this.formShipRoleDescription().trim());
    this.formShipRoleImages().forEach((file) => payload.append("images", file));

    this.savingShipRole.set(true);
    try {
      const editing = this.editingShipRole();
      if (editing) {
        await firstValueFrom(this.call.updateShipRole(editing.id, payload));
      } else {
        await firstValueFrom(this.call.createShipRole(payload));
      }
      // this.notify.success("Saved successfully.");
      this.closeShipRoleModal();
      await this.loadShipRoles();
    } catch {
      this.notify.error("Failed to save ship role.");
    } finally {
      this.savingShipRole.set(false);
    }
  }

  async deleteShipRole(role: ShipRole): Promise<void> {
    if (!confirm(`Delete ship role "${role.title}"?`)) return;
    try {
      await firstValueFrom(this.call.deleteShipRole(role.id));
      // this.notify.success("Ship role deleted.");
      await this.loadShipRoles();
    } catch {
      this.notify.error("Failed to delete ship role.");
    }
  }
}
