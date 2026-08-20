import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { IconComponent } from '../../../shared/components/icon/icon.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PanelCard } from '../../../shared/components/panel-card/panel-card';
import { AddDailyOrderModal } from '../../../Modules/landing/add-daily-order-modal/add-daily-order-modal';
import { Call } from '../../../services/network/call';
import { CommandMessageModalComponent } from './command-message-modal/command-message-modal';
import { AnniversaryModalComponent } from './anniversary-modal/anniversary-modal';
import { UpcomingEventModalComponent } from './upcoming-event-modal/upcoming-event-modal';
import {
  AnniversaryModalPayload,
  CoMessage,
  CommandMessagePayload,
  DailyOrder,
  OfficerSpotlight,
  PersonnelEvent,
  Quote,
  ShipRole,
  UpcomingEvent,
  UpcomingEventUpdatePayload,
} from './home.model';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [DatePipe, IconComponent, PanelCard, ModalComponent, AddDailyOrderModal, UpcomingEventModalComponent, CommandMessageModalComponent, AnniversaryModalComponent],
  templateUrl: './home.html',
  styleUrl: './home.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Home implements OnInit {
  private readonly call = inject(Call);
  private readonly router = inject(Router);

  readonly images = [
    '/assests/images/dashboard_img_1.jpg',
    '/assests/images/dashboard_img_2.jpg',
    '/assests/images/dashboard_img_3.jpg',
  ];

  readonly officerSpotlights = signal<OfficerSpotlight[]>([]);

  readonly scrollingOfficerSpotlights = computed(() => [
    ...this.officerSpotlights(),
    ...this.officerSpotlights(),
  ]);

  currentImageIndex = 0;
  uploadModalOpen = false;
  anniversaryModalOpen = false;
  eventModalOpen = false;
  eventMessageModalOpen=false;
  readonly activeHeroTab = signal<'role' | 'message'>('role');
  readonly quotePaused = signal(false);
  readonly commandMessages = signal<CoMessage[]>([]);
  readonly dailyOrders = signal<DailyOrder[]>([]);
  readonly upcomingEvents = signal<UpcomingEvent[]>([]);
  readonly personnelEvents = signal<PersonnelEvent[]>([]);
  readonly shipRoles = signal<ShipRole[]>([]);
  readonly activeShipRole = computed(() => this.shipRoles()[0] ?? null);
  readonly commandFormError = signal('');
  readonly commandFormSaving = signal(false);
  readonly quoteOfTheDay = signal<string>("शं नो वरुणः | Sham No Varunah | 'हर काम देश के नाम' !! Jai Hind !!");
  readonly activeDailyOrderTooltip = signal<DailyOrder | null>(null);
  readonly dailyOrderTooltipX = signal<number>(0);
  readonly dailyOrderTooltipY = signal<number>(0);
  readonly dailyOrderTooltipPlacement = signal<'top' | 'bottom'>('top');

  ngOnInit(): void {
    this.loadQuoteOfTheDay();
    this.loadCommandMessages();
    this.loadDailyOrders();
    this.loadUpcomingEvents();
    this.loadPersonnelEvents();
    this.loadShipRoles();
    this.loadOfficerSpotlights();
  }

  get currentImage(): string {
    return this.images[this.currentImageIndex];
  }

  moveLeft(): void {
    this.currentImageIndex =
      (this.currentImageIndex - 1 + this.images.length) % this.images.length;
  }

  moveRight(): void {
    this.currentImageIndex =
      (this.currentImageIndex + 1) % this.images.length;
  }

  openDailyOrderModal(): void {
    this.uploadModalOpen = true;
  }

  closeDailyOrderModal(): void {
    this.uploadModalOpen = false;
  }

  async onDailyOrderSaved(): Promise<void> {
    await this.loadDailyOrders();
  }

  goToDailyOrdersHistory(): void {
    this.router.navigate(['/afterAuth/home/daily-orders-history']);
  }

  openPdf(pdfPath: string): void {
    window.open(pdfPath, '_blank', 'noopener,noreferrer');
  }

  orderTooltip(order: DailyOrder): string {
    const lines = [
      order.description ? `Description : ${order.description}` : null,
      order.officer_details ? `Officer of the day : ${order.officer_details}` : null,
      order.routine_details ? `Routine of the day : ${order.routine_details}` : null,
    ].filter((line): line is string => !!line);

    return lines.length ? lines.join('\n') : 'No additional details';
  }

  openAnniversaryModal(): void {
    this.anniversaryModalOpen = true;
  }

  closeAnniversaryModal(): void {
    this.anniversaryModalOpen = false;
  }

  async onAnniversarySave(_payload: AnniversaryModalPayload): Promise<void> {
    await this.loadPersonnelEvents();
    this.closeAnniversaryModal();
  }

  private async loadDailyOrders(): Promise<void> {
    try {
      const response = await firstValueFrom(this.call.getDailyOrders());
      this.dailyOrders.set(this.normalizeDailyOrders(response));
    } catch {
      this.dailyOrders.set([]);
    }
  }

  openEventModal(): void {
    this.eventModalOpen = true;
  }

  closeEventModal(): void {
    this.eventModalOpen = false;
  }

  async onUpcomingEventSave(payload: UpcomingEventUpdatePayload): Promise<void> {
    const formData = new FormData();
    formData.append('title', payload.title);
    formData.append('start_date', payload.start_date);
    formData.append('end_date', payload.end_date ?? '');
    formData.append('start_time', payload.start_time);
    formData.append('end_time', payload.end_time ?? '');
    formData.append('category', payload.category ?? 'defect');

    if (payload.description !== null) {
      formData.append('description', payload.description);
    }

    if (payload.document) {
      formData.append('document', payload.document, payload.document.name);
    }

    try {
      await firstValueFrom(this.call.createEvent(formData));
      await this.loadUpcomingEvents();
      this.closeEventModal();
    } catch {
      // error toast already raised by feedbackInterceptor; nothing else to do here
    }
  }

  openEventMessageModal(): void {
    this.commandFormError.set('');
    this.eventMessageModalOpen = true;
  }

  closeEventMessageModal(): void {
    this.commandFormError.set('');
    this.eventMessageModalOpen = false;
  }

  selectHeroTab(tab: 'role' | 'message'): void {
    this.activeHeroTab.set(tab);
  }

  async submitCommandMessage(payload: CommandMessagePayload): Promise<void> {
    const message = payload.message;
    const validTillDate = payload.validTillDate;

    this.commandFormSaving.set(true);
    this.commandFormError.set('');

    try {
      await firstValueFrom(
        this.call.createCoMessage({
          message,
          valid_till_date: validTillDate,
        }),
      );
      await this.loadCommandMessages();
      this.closeEventMessageModal();
      this.activeHeroTab.set('message');
    } catch {
      this.commandFormError.set('Failed to save command message. Please try again.');
    } finally {
      this.commandFormSaving.set(false);
    }
  }

  private async loadCommandMessages(): Promise<void> {
    try {
      const response = await firstValueFrom(this.call.getCoMessages());
      this.commandMessages.set(this.normalizeCoMessages(response));
    } catch {
      this.commandMessages.set([]);
    }
  }

  private async loadUpcomingEvents(): Promise<void> {
    try {
      const response = await firstValueFrom(this.call.getEvents());
      this.upcomingEvents.set(this.normalizeUpcomingEvents(response));
    } catch {
      this.upcomingEvents.set([]);
    }
  }

  private async loadShipRoles(): Promise<void> {
    try {
      const response = await firstValueFrom(this.call.getShipRoles());
      this.shipRoles.set(this.normalizeShipRoles(response));
    } catch {
      this.shipRoles.set([]);
    }
  }

  private async loadOfficerSpotlights(): Promise<void> {
    try {
      const response = await firstValueFrom(this.call.getMemberDetails());
      const members = Array.isArray(response) ? response : [];
      const spotlights = members
        .filter((member) => member?.name)
        .map((member, index) => ({
          name: member.name,
          rank: member.rank ?? '',
          role: member.designation ?? '',
          image: member.image_path || '',
        }));
      this.officerSpotlights.set(spotlights);
    } catch {
      this.officerSpotlights.set([]);
    }
  }

  private normalizeShipRoles(response: unknown): ShipRole[] {
    if (!Array.isArray(response)) {
      return [];
    }

    const roles = response
      .map((item) => {
        const raw = item as {
          id?: number;
          role_title?: string | null;
          current_text?: string;
          uploaded_date?: string;
        };

        return {
          id: Number(raw.id ?? 0),
          title: typeof raw.role_title === 'string' ? raw.role_title.trim() : '',
          description: typeof raw.current_text === 'string' ? raw.current_text.trim() : '',
          uploadedDate: typeof raw.uploaded_date === 'string' ? raw.uploaded_date : '',
        };
      })
      .filter((item) => item.title.length > 0 || item.description.length > 0);

    return roles.sort((a, b) => {
      const dateA = Date.parse(a.uploadedDate || '');
      const dateB = Date.parse(b.uploadedDate || '');
      if (dateA !== dateB) {
        return dateB - dateA;
      }
      return b.id - a.id;
    });
  }

  private async loadPersonnelEvents(): Promise<void> {
    try {
      const response = await firstValueFrom(this.call.getPersonnelEvents());
      this.personnelEvents.set(this.normalizePersonnelEvents(response));
    } catch {
      this.personnelEvents.set([]);
    }
  }

  private normalizeCoMessages(response: unknown): CoMessage[] {
    if (!Array.isArray(response)) {
      return [];
    }

    const messages: CoMessage[] = response
      .map((item) => {
        const raw = item as Partial<CoMessage>;
        return {
          id: Number(raw.id ?? 0),
          message: typeof raw.message === 'string' ? raw.message.trim() : '',
          valid_till_date:
            typeof raw.valid_till_date === 'string' ? raw.valid_till_date : '',
          uploaded_date:
            typeof raw.uploaded_date === 'string' ? raw.uploaded_date : '',
        };
      })
      .filter((item) => item.message.length > 0);

    return messages.sort((a, b) => {
      const dateA = Date.parse(a.uploaded_date || '');
      const dateB = Date.parse(b.uploaded_date || '');
      if (dateA !== dateB) {
        return dateB - dateA;
      }
      return b.id - a.id;
    });
  }

  private normalizeUpcomingEvents(response: unknown): UpcomingEvent[] {
    const source = Array.isArray(response)
      ? response
      : (response as { results?: unknown[] })?.results ?? [];

    const events = source
      .map((item) => {
        const raw = item as {
          id?: number;
          title?: string;
          start_date?: string;
          document?: string;
          created_at?: string;
        };

        return {
          id: Number(raw.id ?? 0),
          title: typeof raw.title === 'string' ? raw.title.trim() : '',
          date: typeof raw.start_date === 'string' ? raw.start_date : '',
          document: typeof raw.document === 'string' ? raw.document : '',
          created_at: typeof raw.created_at === 'string' ? raw.created_at : '',
        };
      })
      .filter((item) => item.title.length > 0 && item.date.length > 0);

    events.sort((a, b) => {
      const dateA = Date.parse(a.date || a.created_at || '');
      const dateB = Date.parse(b.date || b.created_at || '');
      if (dateA !== dateB) {
        return dateA - dateB;
      }
      return b.id - a.id;
    });

    return events.map(({ id, title, date, document }) => ({ id, title, date, document }));
  }

  private normalizePersonnelEvents(response: unknown): PersonnelEvent[] {
    const source = (response as { results?: unknown[] })?.results ?? [];

    if (!Array.isArray(source)) {
      return [];
    }

    return source
      .map((item) => {
        const raw = item as Partial<PersonnelEvent>;

        return {
          type: typeof raw.type === 'string' ? raw.type : '',
          name: typeof raw.name === 'string' ? raw.name.trim() : '',
          personal_number:
            typeof raw.personal_number === 'string' && raw.personal_number.trim()
              ? raw.personal_number.trim()
              : null,
          designation:
            typeof raw.designation === 'string' && raw.designation.trim()
              ? raw.designation.trim()
              : null,
          event_date:
            typeof raw.event_date === 'string' ? raw.event_date : '',
          age: typeof raw.age === 'number' ? raw.age : null,
          years: typeof raw.years === 'number' ? raw.years : null,
          event_label:
            typeof raw.event_label === 'string' ? raw.event_label.trim() : '',
        };
      })
      .filter((item) => item.name.length > 0 && item.event_date.length > 0);
  }

  private normalizeDailyOrders(response: unknown): DailyOrder[] {
    const source = Array.isArray(response)
      ? response
      : (response as { results?: unknown[]; daily_orders?: unknown[] })?.results ??
        (response as { results?: unknown[]; daily_orders?: unknown[] })?.daily_orders ??
        [];

    if (!Array.isArray(source)) {
      return [];
    }

    return source
      .map((item) => {
        const raw = item as Partial<DailyOrder>;

        return {
          id: Number(raw.id ?? 0),
          date: typeof raw.date === 'string' ? raw.date : '',
          description: typeof raw.description === 'string' ? raw.description.trim() : '',
          officer_details:
            typeof raw.officer_details === 'string' ? raw.officer_details.trim() : '',
          routine_details:
            typeof raw.routine_details === 'string' ? raw.routine_details.trim() : '',
          pdf_path: typeof raw.pdf_path === 'string' ? raw.pdf_path : '',
        };
      })
      .filter((item) => item.date.length > 0 || item.description.length > 0);
  }

  private async loadQuoteOfTheDay(): Promise<void> {
    try {
      const response = await firstValueFrom(this.call.getQuotes());
      const quotes = Array.isArray(response) ? (response as Quote[]) : [];
      const activeQuote = quotes.find((q) => q.is_active === true);
      if (activeQuote && activeQuote.quoteText) {
        this.quoteOfTheDay.set(activeQuote.quoteText);
      }
    } catch {
      console.error('Failed to load quote of the day:');
    }
  }

  showTooltip(event: MouseEvent, order: DailyOrder): void {
    this.activeDailyOrderTooltip.set(order);
    const target = event.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();

    const margin = 12;
    const tooltipWidth = Math.min(330, window.innerWidth - margin * 2);
    const halfWidth = tooltipWidth / 2;
    const rawX = rect.left + rect.width / 2;

    this.dailyOrderTooltipX.set(Math.min(
      Math.max(rawX, halfWidth + margin),
      window.innerWidth - halfWidth - margin,
    ));

    const estimatedTooltipHeight = 160;
    const spaceAbove = rect.top;
    const spaceBelow = window.innerHeight - rect.bottom;
    
    const placement = spaceAbove < estimatedTooltipHeight && spaceBelow > spaceAbove ? 'bottom' : 'top';
    this.dailyOrderTooltipPlacement.set(placement);

    const y = placement === 'top'
      ? Math.max(rect.top - 10, margin)
      : Math.min(rect.bottom + 10, window.innerHeight - margin);
    this.dailyOrderTooltipY.set(y);
  }

  hideTooltip(): void {
    this.activeDailyOrderTooltip.set(null);
  }

}
