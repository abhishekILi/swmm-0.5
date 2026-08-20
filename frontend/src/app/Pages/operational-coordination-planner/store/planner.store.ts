import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import {
  Activity,
  Category,
  InboxMessage,
  LaneId,
  MS_PER_DAY,
  Notification,
  ThemeMode,
  ViewMode,
  addDays,
  getWeekStart,
  startOfDay,
} from '../constants/data';
import { PlannerApiService } from '../services/planner-api.service';
import {
  PlannerActivityDto,
  PlannerActivityPayload,
  PlannerActivityQuery,
  PlannerChoicesDto,
  PlannerDashboardDto,
  PlannerInboxMessageDto,
  PlannerNotificationDto,
  PlannerOverdueDartRowDto,
} from '../models/planner-api.models';

type ChipFilter = 'active' | 'delayed' | 'conflict' | 'others' | 'trial' | 'today' | null;

const DEPT_TO_LANE: Record<string, LaneId> = {
  Engineering: 'eng',
  Electrical: 'elec',
  Weapon: 'wpn',
  Operations: 'ops',
  'FMU / Support': 'fmu',
  'Trials & Inspection': 'tri',
  Admin: 'adm',
};

@Injectable({ providedIn: 'root' })
export class PlannerStore {
  private readonly api = inject(PlannerApiService);
  private loadSeq = 0;
  private readonly today = startOfDay(new Date());
  readonly currentWeekDayIndex = (new Date().getDay() + 6) % 7;

  readonly activities = signal<Activity[]>([]);
  /** Whole-year activities for the Year view (not clamped to a single week like `activities`). */
  readonly yearActivities = signal<Activity[]>([]);
  readonly yearRef = signal(this.today.getFullYear());
  readonly yearLoading = signal(false);
  private loadedYear: number | null = null;
  readonly notifications = signal<Notification[]>([]);
  readonly inbox = signal<InboxMessage[]>([]);
  readonly dashboard = signal<PlannerDashboardDto | null>(null);
  readonly choices = signal<PlannerChoicesDto | null>(null);
  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly lastSyncedAt = signal<Date | null>(null);

  readonly selectedId = signal<string | null>(null);
  readonly selectedDate = signal<string | null>(null);
  /** When true, the expanded read-only side panel shows instead of the compact details popup. */
  readonly detailFullView = signal(false);
  readonly view = signal<ViewMode>('Week');
  readonly rangeStart = signal(this.today);
  readonly currentRangeDayIndex = computed(() =>
    Math.floor((this.today.getTime() - startOfDay(this.rangeStart()).getTime()) / MS_PER_DAY),
  );
  readonly navActive = signal('planner');
  readonly sidebarCollapsed = signal(false);

  readonly chipFilter = signal<ChipFilter>(null);
  readonly deptFilter = signal('All Departments');
  readonly catFilter = signal<Category[]>([
    'defect',
    'routine',
    'planned_routine',
    'trial',
    'audit',
    'others',
  ]);

  readonly newModalOpen = signal(false);
  readonly editorMode = signal<'create' | 'edit'>('create');
  readonly notifFlyoutOpen = signal(false);
  readonly mailFlyoutOpen = signal(false);

  readonly overdueDartsModalOpen = signal(false);
  readonly overdueDartsLoading = signal(false);
  readonly overdueDarts = signal<PlannerOverdueDartRowDto[]>([]);

  readonly theme = signal<ThemeMode>('dark');
  readonly toasts = signal<{ id: string; text: string }[]>([]);

  readonly filteredActivities = computed<Activity[]>(() => {
    const cats = this.catFilter();
    const dept = this.deptFilter();
    const chip = this.chipFilter();

    return this.activities().filter((a) => {
      if (!cats.includes(a.cat)) return false;
      if (dept !== 'All Departments' && a.lane !== DEPT_TO_LANE[dept]) return false;
      if (chip === 'active') return a.status.toLowerCase() === 'active' || !!a.prog || !!a.selected;
      if (chip === 'delayed') return !!a.delayed;
      if (chip === 'conflict') return !!a.conflict;
      if (chip === 'others') return a.cat === 'others';
      if (chip === 'trial') return a.cat === 'trial';
      if (chip === 'today') return a.day === this.currentRangeDayIndex();
      return true;
    });
  });

  readonly yearFilteredActivities = computed<Activity[]>(() => {
    const cats = this.catFilter();
    const dept = this.deptFilter();

    return this.yearActivities().filter((a) => {
      if (!cats.includes(a.cat)) return false;
      if (dept !== 'All Departments' && a.lane !== DEPT_TO_LANE[dept]) return false;
      return true;
    });
  });

  readonly selectedActivity = computed<Activity | null>(() => {
    const id = this.selectedId();
    if (id) {
      const matched = this.filteredActivities().find((a) => a.id === id);
      if (matched) {
        return matched;
      }
    }

    return this.selectedDateActivities()[0] ?? null;
  });

  readonly selectedDateActivities = computed<Activity[]>(() => {
    const selectedDate = this.selectedDate();
    if (!selectedDate) {
      return [];
    }

    return this.filteredActivities().filter(
      (activity) => this.getActivityDateKey(activity) === selectedDate,
    );
  });

  readonly unreadMailCount = computed(() => this.inbox().filter((m) => m.unread).length);

  selectActivity(id: string | null) {
    if (id === null) {
      this.clearSelection();
      return;
    }

    this.selectedId.set(id);
    this.detailFullView.set(false);
  }

  selectActivityWithDate(id: string | null, date: string | null = null) {
    this.selectedId.set(id);
    this.selectedDate.set(date);
    this.detailFullView.set(false);
  }

  selectDate(date: string, activityId: string | null = null) {
    this.selectedDate.set(date);
    this.selectedId.set(activityId);
    this.detailFullView.set(false);
  }

  clearSelection() {
    this.selectedId.set(null);
    this.selectedDate.set(null);
    this.detailFullView.set(false);
  }

  openFullDetail() {
    this.detailFullView.set(true);
  }

  openCreateActivity() {
    this.editorMode.set('create');
    this.newModalOpen.set(true);
  }

  openEditActivity() {
    if (!this.selectedActivity()) {
      return;
    }

    this.editorMode.set('edit');
    this.newModalOpen.set(true);
  }

  closeEditor() {
    this.newModalOpen.set(false);
    this.editorMode.set('create');
  }

  async init() {
    await this.reloadCurrentWeek();
  }

  toggleChip(id: Exclude<ChipFilter, null>) {
    this.chipFilter.update((cur) => (cur === id ? null : id));
  }

  setDept(d: string) {
    this.deptFilter.set(d);
  }

  toggleCategory(c: Category) {
    this.catFilter.update((cats) =>
      cats.includes(c) ? cats.filter((x) => x !== c) : [...cats, c],
    );
  }

  toggleSidebar() {
    this.sidebarCollapsed.update((v) => !v);
  }

  toggleTheme() {
    this.theme.update((t) => (t === 'dark' ? 'light' : 'dark'));
  }

  openNotifFlyout() {
    this.notifFlyoutOpen.set(true);
    this.mailFlyoutOpen.set(false);
  }

  openMailFlyout() {
    this.mailFlyoutOpen.set(true);
    this.notifFlyoutOpen.set(false);
  }

  closeFlyouts() {
    this.notifFlyoutOpen.set(false);
    this.mailFlyoutOpen.set(false);
  }

  openOverdueDartsModal() {
    this.overdueDartsModalOpen.set(true);
    void this.loadOverdueDarts();
  }

  closeOverdueDartsModal() {
    this.overdueDartsModalOpen.set(false);
  }

  private async loadOverdueDarts() {
    this.overdueDartsLoading.set(true);
    try {
      const response = await firstValueFrom(this.api.getOverdueDarts());
      this.overdueDarts.set(response.results);
    } catch (error) {
      console.error('Overdue DARTs load failed', error);
      this.pushToast('Unable to load overdue DARTs');
    } finally {
      this.overdueDartsLoading.set(false);
    }
  }

  stepWeek(delta: number) {
    this.rangeStart.update((start) => addDays(start, delta * 7));
    this.clearSelection();
    void this.reloadCurrentRange();
  }

  stepYear(delta: number) {
    const next = this.yearRef() + delta;
    this.yearRef.set(next);
    void this.loadYear(next);
  }

  /** Loads the year for `yearRef()` only if it hasn't been loaded yet. */
  ensureYearLoaded() {
    if (this.loadedYear !== this.yearRef()) {
      void this.loadYear(this.yearRef());
    }
  }

  private extractArray<T>(response: unknown): T[] {
    if (Array.isArray(response)) {
      return response;
    }
    if (response && typeof response === 'object') {
      const obj = response as Record<string, unknown>;
      if (Array.isArray(obj['results'])) return obj['results'] as T[];
      if (Array.isArray(obj['data'])) return obj['data'] as T[];
      if (Array.isArray(obj['activities'])) return obj['activities'] as T[];
    }
    return [];
  }

  private async loadYear(year: number) {
    const start = new Date(year, 0, 1);
    const end = new Date(year, 11, 31);
    const query = this.buildQuery(start, end);

    this.yearLoading.set(true);
    try {
      const rawActivities = await firstValueFrom(this.api.getActivities(query));
      const activities = this.extractArray<PlannerActivityDto>(rawActivities);
      this.yearActivities.set(
        activities
          .map((activity) => this.mapActivityForYear(activity))
          .filter((activity): activity is Activity => activity !== null),
      );
      this.loadedYear = year;
    } catch (error) {
      console.error('Year activities load failed', error);
      this.pushToast('Unable to load the year view');
    } finally {
      this.yearLoading.set(false);
    }
  }

  setWeek(offset: number) {
    this.rangeStart.set(addDays(getWeekStart(offset), 0));
    this.clearSelection();
    void this.reloadCurrentRange();
  }

  goToday() {
    this.rangeStart.set(this.today);
    this.clearSelection();
    void this.reloadCurrentRange();
  }

  setRangeStart(date: Date) {
    this.rangeStart.set(startOfDay(date));
    this.clearSelection();
    void this.reloadCurrentRange();
  }

  pushToast(text: string) {
    const id = crypto.getRandomValues(new Uint32Array(1))[0].toString(36).slice(0, 5);
    this.toasts.update((t) => [...t, { id, text }]);
    setTimeout(() => this.toasts.update((t) => t.filter((x) => x.id !== id)), 2400);
  }

  createActivity(input: {
    title: string;
    lane: LaneId;
    cat: Category;
    t1: string;
    t2: string;
    date?: string;
    description?: string;
  }): Promise<void> {
    const payload: PlannerActivityPayload = {
      title: input.title || 'Untitled Event',
      category: input.cat,
      date: input.date || this.formatDate(this.getAnchorDate()),
      start_time: this.normalizeTime(input.t1),
      end_time: this.normalizeTime(input.t2),
      lane: input.lane || 'eng',
      progress: 0,
      status: 'scheduled',
      description: input.description || '',
    };

    return this.createActivityOnServer(payload);
  }

  async updateActivity(id: string | number, payload: PlannerActivityPayload) {
    try {
      await firstValueFrom(this.api.updateActivity(id, payload));
      await this.reloadCurrentWeek();
      this.pushToast('Event updated');
    } catch (error) {
      console.error('Activity update failed', error);
      this.pushToast('Unable to update event');
      throw error;
    }
  }

  async deleteActivity(id: string | number) {
    try {
      await firstValueFrom(this.api.deleteActivity(id));
      await this.reloadCurrentWeek();
      this.selectActivity(null);
      this.pushToast('Event deleted');
    } catch (error) {
      console.error('Activity delete failed', error);
      this.pushToast('Unable to delete event');
    }
  }

  reloadCurrentRange() {
    return this.reloadCurrentWeek();
  }

  private async reloadCurrentWeek() {
    const token = ++this.loadSeq;
    const rangeStart = this.startOfDay(this.rangeStart());
    const monthStart = new Date(rangeStart.getFullYear(), rangeStart.getMonth(), 1);
    const query = this.buildQuery(addDays(monthStart, -14), addDays(monthStart, 42));

    this.loading.set(true);
    this.loadError.set(null);

    try {
      const [rawActivities, dashboard, choices] = await Promise.all([
        firstValueFrom(this.api.getActivities(query)),
        firstValueFrom(this.api.getDashboard(query)),
        firstValueFrom(this.api.getChoices()),
      ]);

      if (token !== this.loadSeq) {
        return;
      }

      const activities = this.extractArray<PlannerActivityDto>(rawActivities);
      this.activities.set(
        activities
          .map((activity) => this.mapActivity(activity, rangeStart))
          .filter((activity): activity is Activity => activity !== null),
      );
      this.dashboard.set(dashboard);
      this.choices.set(choices);
      this.notifications.set((dashboard.notifications ?? []).map((item) => this.mapNotification(item)));
      this.inbox.set((dashboard.inbox ?? []).map((item) => this.mapInbox(item)));
      this.lastSyncedAt.set(new Date());
    } catch (error) {
      if (token === this.loadSeq) {
        this.loadError.set('Unable to load planner data.');
        console.error('Planner data load failed', error);
      }
    } finally {
      if (token === this.loadSeq) {
        this.loading.set(false);
      }
    }
  }

  private buildQuery(start: Date, end: Date): PlannerActivityQuery {
    return {
      start_date: this.formatDate(start),
      end_date: this.formatDate(end),
    };
  }

  private async createActivityOnServer(payload: PlannerActivityPayload) {
    try {
      const createdRaw = await firstValueFrom(this.api.createActivity(payload));
      const createdObj = (createdRaw as any)?.data ?? (createdRaw as any)?.result ?? createdRaw;

      if (createdObj && (createdObj.id || createdObj.id === 0)) {
        const rangeStart = this.startOfDay(this.rangeStart());
        const mapped = this.mapActivity(createdObj, rangeStart);
        if (mapped) {
          this.activities.update((cur) => [...cur.filter((a) => a.id !== mapped.id), mapped]);
        }
      }

      await this.reloadCurrentWeek();

      const createdId = String(createdObj?.id ?? '');
      if (createdId) {
        this.selectActivityWithDate(createdId, createdObj?.date ? this.formatDate(this.parseDate(createdObj.date)) : null);
      }
      this.pushToast('Event created');
    } catch (error) {
      console.error('Activity create failed', error);
      this.pushToast('Unable to create event');
      throw error;
    }
  }

  private mapActivity(dto: PlannerActivityDto, weekStart: Date): Activity | null {
    if (!dto) return null;

    const activityDate = this.parseDate(dto.date);
    const isoDate = this.formatDate(activityDate);
    const diffMs = this.startOfDay(activityDate).getTime() - this.startOfDay(weekStart).getTime();
    const calculatedDay = Math.round(diffMs / MS_PER_DAY);
    const day = isNaN(calculatedDay) ? 0 : calculatedDay;

    return {
      id: String(dto.id),
      lane: dto.lane,
      day,
      date: isoDate,
      cat: dto.category,
      title: dto.title || 'Untitled Event',
      sub: dto.subtitle?.trim() || dto.department || dto.lane_label || '',
      description: dto.description?.trim() || dto.subtitle?.trim() || '',
      t: dto.time_label || this.buildTimeLabel(dto.start_time, dto.end_time),
      prog: dto.progress ?? 0,
      status: dto.status_label || this.titleCase(dto.status || 'scheduled'),
      priority: (dto.priority_label as Activity['priority']) ?? undefined,
      conflict: !!dto.conflict,
      delayed: !!dto.delayed,
      selected: !!dto.selected,
      isolation: !!dto.isolation,
      equipment: dto.equipment ?? undefined,
      ref: dto.reference ?? undefined,
      loc: dto.location ?? undefined,
    };
  }

  /** Like `mapActivity`, but keyed by absolute date instead of a day-offset
   *  from a loaded week - for the Year view, which spans many weeks/months. */
  private mapActivityForYear(dto: PlannerActivityDto): Activity | null {
    if (!dto) return null;

    const activityDate = this.parseDate(dto.date);
    const isoDate = this.formatDate(activityDate);

    return {
      id: String(dto.id),
      lane: dto.lane,
      day: 0,
      date: isoDate,
      cat: dto.category,
      title: dto.title || 'Untitled Event',
      sub: dto.subtitle?.trim() || dto.department || dto.lane_label || '',
      description: dto.description?.trim() || dto.subtitle?.trim() || '',
      t: dto.time_label || this.buildTimeLabel(dto.start_time, dto.end_time),
      prog: dto.progress ?? 0,
      status: dto.status_label || this.titleCase(dto.status || 'scheduled'),
      priority: (dto.priority_label as Activity['priority']) ?? undefined,
      conflict: !!dto.conflict,
      delayed: !!dto.delayed,
      selected: !!dto.selected,
      isolation: !!dto.isolation,
      equipment: dto.equipment ?? undefined,
      ref: dto.reference ?? undefined,
      loc: dto.location ?? undefined,
    };
  }

  private mapNotification(dto: PlannerNotificationDto): Notification {
    return {
      id: dto.id,
      kind: dto.kind,
      icon: dto.icon,
      title: dto.title,
      body: dto.body,
      when: dto.when,
    };
  }

  private mapInbox(dto: PlannerInboxMessageDto): InboxMessage {
    return {
      id: dto.id,
      unread: dto.unread,
      from: dto.sender,
      subject: dto.subject,
      preview: dto.preview,
      when: dto.when,
    };
  }

  private parseDate(value: string | Date | null | undefined): Date {
    if (!value) {
      return new Date();
    }
    if (value instanceof Date) {
      return isNaN(value.getTime()) ? new Date() : value;
    }
    const cleanStr = String(value).split('T')[0].trim();
    const parts = cleanStr.split('-').map((p) => parseInt(p, 10));
    if (parts.length >= 3 && !parts.some(isNaN)) {
      return new Date(parts[0], parts[1] - 1, parts[2]);
    }
    const d = new Date(value);
    return isNaN(d.getTime()) ? new Date() : d;
  }

  private startOfDay(value: Date): Date {
    return new Date(value.getFullYear(), value.getMonth(), value.getDate());
  }

  private formatDate(value: Date): string {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private buildTimeLabel(start?: string | null, end?: string | null): string {
    const startLabel = this.formatClock(start);
    const endLabel = this.formatClock(end);
    if (!startLabel && !endLabel) {
      return '';
    }
    if (!endLabel) {
      return startLabel;
    }
    if (!startLabel) {
      return endLabel;
    }
    return `${startLabel} - ${endLabel}`;
  }

  private formatClock(value?: string | null): string {
    if (!value) {
      return '';
    }

    const trimmed = value.trim();
    if (/am|pm/i.test(trimmed)) {
      return trimmed;
    }

    const parts = trimmed.split(':');
    if (parts.length < 2) {
      return trimmed;
    }

    let hours = parseInt(parts[0], 10);
    const minutes = parts[1].padStart(2, '0');

    if (isNaN(hours)) {
      return value;
    }

    const period = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    if (hours === 0) {
      hours = 12;
    }

    const hoursStr = String(hours).padStart(2, '0');
    return `${hoursStr}:${minutes} ${period}`;
  }

  private titleCase(value: string): string {
    if (!value) return '';
    return value
      .split('_')
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  private normalizeTime(value: string): string {
    if (!value) {
      return '00:00:00';
    }

    const trimmed = value.trim();
    const matchAmPm = trimmed.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)$/i);
    if (matchAmPm) {
      let hours = parseInt(matchAmPm[1], 10);
      const minutes = matchAmPm[2];
      const seconds = matchAmPm[3] || '00';
      const period = matchAmPm[4].toUpperCase();

      if (period === 'PM' && hours < 12) {
        hours += 12;
      } else if (period === 'AM' && hours === 12) {
        hours = 0;
      }

      return `${String(hours).padStart(2, '0')}:${minutes}:${seconds}`;
    }

    if (/^\d{2}:\d{2}:\d{2}$/.test(trimmed)) {
      return trimmed;
    }

    if (/^\d{1,2}:\d{2}$/.test(trimmed)) {
      const [h, m] = trimmed.split(':');
      return `${h.padStart(2, '0')}:${m}:00`;
    }

    if (/^\d{4}$/.test(trimmed)) {
      return `${trimmed.slice(0, 2)}:${trimmed.slice(2)}:00`;
    }

    return '00:00:00';
  }

  private getAnchorDate(): Date {
    return this.startOfDay(this.rangeStart());
  }

  getActivityDateKey(activity: Activity): string {
    const rangeStart = this.startOfDay(this.rangeStart());
    const date = addDays(rangeStart, activity.day);
    return this.formatDate(date);
  }
}
