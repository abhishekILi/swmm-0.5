import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { AbstractControl, FormBuilder, FormGroup, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';

import { Activity, LANES, addDays } from '../../constants/data';
import { PlannerStore } from '../../store/planner.store';
import { IconComponent } from '../planner-icon/planner-icon.component';
import { InputField } from '../../../../shared/components/input-field/input-field';
import { SelectInput } from '../../../../shared/components/select-input/select-input';
import { TextareaInput } from '../../../../shared/components/textarea-input/textarea-input';
import { DatePickerComponent } from '../../../../shared/components/date-picker/picker';

function validTimeValidator(control: AbstractControl): ValidationErrors | null {
  const val = control.value;
  if (!val) {
    return null;
  }

  const trimmed = String(val).trim();

  // 1. Check 12-hour AM/PM format (e.g., "08:00 AM", "8:00 PM", "12:30 am")
  const matchAmPm = /^(\d{1,2}):(\d{2})\s*(AM|PM)$/i.exec(trimmed);
  if (matchAmPm) {
    const hours = parseInt(matchAmPm[1], 10);
    const minutes = parseInt(matchAmPm[2], 10);
    if (hours < 1 || hours > 12 || minutes < 0 || minutes > 59) {
      return { invalidTimeFormat: true };
    }
    return null;
  }

  // 2. Check 24-hour format (e.g., "08:00", "14:30", "00:00", "23:59")
  const match24 = /^(\d{1,2}):(\d{2})$/.exec(trimmed);
  if (match24) {
    const hours = parseInt(match24[1], 10);
    const minutes = parseInt(match24[2], 10);
    if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
      return { invalidTimeFormat: true };
    }
    return null;
  }

  return { invalidTimeFormat: true };
}

@Component({
  selector: 'app-new-activity-modal',
  standalone: true,
  imports: [IconComponent, CommonModule, ReactiveFormsModule, InputField, SelectInput, TextareaInput, DatePickerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './planner-new-activity-modal.component.scss',
  templateUrl: './planner-new-activity-modal.component.html',
})
export class NewActivityModalComponent implements OnInit {
  private fb = inject(FormBuilder);

  private readonly store = inject(PlannerStore);

  activityForm!: FormGroup;
  protected readonly editorMode = this.store.editorMode;
  protected readonly selectedActivity = this.store.selectedActivity;

  readonly departmentOptions = LANES.map((lane) => ({
    label: lane.label,
    value: lane.id,
  }));

  readonly categoryOptions = computed(() => {
    const rawCategories = this.store.choices()?.categories;
    const fallbackCategories = [
      { value: 'defect', label: 'Defect' },
      { value: 'routine', label: 'Routine' },
      { value: 'planned_routine', label: 'Planned Routine' },
      { value: 'trial', label: 'Trial' },
      { value: 'audit', label: 'Audit' },
      { value: 'others', label: 'Others' },
    ];

    const list: unknown[] = Array.isArray(rawCategories) && rawCategories.length > 0
      ? rawCategories
      : fallbackCategories;

    return list.map((item: unknown) => {
      if (Array.isArray(item)) {
        const val = String(item[0] ?? '');
        const lbl = String(item[1] ?? item[0] ?? val);
        return { label: lbl, value: val };
      }
      if (item && typeof item === 'object') {
        const obj = item as Record<string, unknown>;
        const val = String(obj['value'] ?? obj['id'] ?? obj['key'] ?? obj['code'] ?? '');
        const lbl = String(obj['label'] ?? obj['name'] ?? obj['display_name'] ?? obj['title'] ?? val);
        return { label: lbl, value: val };
      }
      if (typeof item === 'string') {
        return { label: item, value: item };
      }
      return { label: String(item ?? ''), value: String(item ?? '') };
    });
  });

  ngOnInit() {
    this.activityForm = this.fb.group({
      title: ['', Validators.required],
      department: [null, Validators.required],
      category: [null, Validators.required],
      date: ['', Validators.required],
      fromTime: ['', [Validators.required, validTimeValidator]],
      toTime: ['', [Validators.required, validTimeValidator]],
      description: [''],
    });

    this.setupTimeFieldFormatting('fromTime');
    this.setupTimeFieldFormatting('toTime');

    const activity = this.selectedActivity();
    if (this.editorMode() === 'edit' && activity) {
      this.activityForm.patchValue(this.toFormValues(activity));
    }
  }

  private setupTimeFieldFormatting(fieldName: string): void {
    const control = this.activityForm.get(fieldName);
    if (!control) return;

    let previousVal = '';

    control.valueChanges.subscribe((val: string | null) => {
      const raw = val ?? '';
      if (raw === previousVal) return;

      const isDeleting = raw.length < previousVal.length;

      // Extract only numeric digits, max 4 digits strictly
      const digitsOnly = raw.replace(/\D/g, '').slice(0, 4);

      let formatted = raw;

      if (raw.includes(':')) {
        const parts = raw.split(':');
        const h = parts[0].replace(/\D/g, '').slice(0, 2);
        const m = parts.slice(1).join('').replace(/\D/g, '').slice(0, 2);
        formatted = m ? `${h}:${m}` : `${h}:`;
      } else if (!isDeleting && digitsOnly.length === 4) {
        formatted = `${digitsOnly.slice(0, 2)}:${digitsOnly.slice(2)}`;
      } else {
        formatted = digitsOnly;
      }

      // Cap at 5 characters max (HH:MM)
      if (formatted.length > 5) {
        formatted = formatted.slice(0, 5);
      }

      previousVal = formatted;

      if (formatted !== raw) {
        setTimeout(() => {
          control.setValue(formatted, { emitEvent: false });
        });
      }
    });
  }

  readonly timeErrorMessage = signal<string>('');

  close() {
    this.store.closeEditor();
  }

  closeAllDropdowns(): void {
    document.dispatchEvent(new CustomEvent('close-all-select-dropdowns'));
  }

  async create() {
    this.timeErrorMessage.set('');

    const fromControl = this.activityForm.get('fromTime');
    const toControl = this.activityForm.get('toTime');

    if (fromControl?.hasError('invalidTimeFormat') || toControl?.hasError('invalidTimeFormat')) {
      this.timeErrorMessage.set('Please enter a valid time in HH:MM format (00:00 to 23:59).');
      this.activityForm.markAllAsTouched();
      return;
    }

    if (this.activityForm.invalid) {
      this.activityForm.markAllAsTouched();
      return;
    }

    const payload = this.activityForm.value;
    const startTimeNorm = this.normalizeTime(payload.fromTime);
    const endTimeNorm = this.normalizeTime(payload.toTime);

    if (startTimeNorm >= endTimeNorm) {
      this.timeErrorMessage.set('End time must be after start time.');
      this.activityForm.get('toTime')?.setErrors({ invalidTimeRange: true });
      this.activityForm.markAllAsTouched();
      return;
    }

    const selected = this.selectedActivity();

    try {
      if (this.editorMode() === 'edit' && selected) {
        await this.store.updateActivity(selected.id, {
          title: payload.title,
          category: payload.category,
          date: payload.date,
          start_time: startTimeNorm,
          end_time: endTimeNorm,
          lane: payload.department,
          progress: selected.prog ?? 0,
          status: this.normalizeStatus(selected.status),
          description: payload.description,
          subtitle: payload.description,
        });
      } else {
        await this.store.createActivity({
          title: payload.title,
          lane: payload.department,
          cat: payload.category,
          t1: payload.fromTime,
          t2: payload.toTime,
          date: payload.date,
          description: payload.description,
        });
      }
      this.close();
    } catch (err) {
      console.error('Activity save failed', err);
    }
  }

  private toFormValues(activity: Activity) {
    const [fromTime, toTime] = this.parseTimeRange(activity.t);
    return {
      title: activity.title,
      department: activity.lane,
      category: activity.cat,
      date: this.dayToDate(activity.day),
      fromTime,
      toTime,
      description: activity.description || activity.sub || '',
    };
  }

  private dayToDate(day: number): string {
    const d = addDays(this.store.rangeStart(), day);
    return this.toIsoDate(d);
  }

  private toIsoDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private parseTimeRange(label: string): [string, string] {
    const normalized = (label || '').replace(/[–—]/g, '-');
    const parts = normalized.split('-').map((p) => p.trim());
    if (parts.length >= 2) {
      return [this.toClock(parts[0]), this.toClock(parts[1])];
    }
    if (parts.length === 1 && parts[0]) {
      return [this.toClock(parts[0]), '10:00 AM'];
    }
    return ['08:00 AM', '10:00 AM'];
  }

  private toClock(value: string): string {
    const trimmed = value.trim();
    if (!trimmed) {
      return '08:00 AM';
    }
    const match = /^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i.exec(trimmed);
    if (match) {
      return trimmed;
    }
    const match4 = /^(\d{4})$/.exec(trimmed);
    if (match4) {
      return `${match4[1].slice(0, 2)}:${match4[1].slice(2)}`;
    }
    return trimmed;
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

  private normalizeStatus(status: string): 'scheduled' | 'active' | 'delayed' | 'conflict' | 'completed' | 'cancelled' {
    const normalized = (status || '').toLowerCase();
    if (normalized.includes('delayed')) return 'delayed';
    if (normalized.includes('conflict')) return 'conflict';
    if (normalized.includes('active')) return 'active';
    if (normalized.includes('completed')) return 'completed';
    if (normalized.includes('cancel')) return 'cancelled';
    return 'scheduled';
  }
}
