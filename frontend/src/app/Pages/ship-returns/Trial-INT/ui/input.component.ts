import { ChangeDetectorRef, Component, Input, forwardRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

@Component({
  selector: 'app-input',
  standalone: true,
  imports: [CommonModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputComponent),
      multi: true,
    },
  ],
  template: `
  <div class="group flex w-full flex-col gap-1.5">
   <div class="relative flex h-[45px] w-full items-center rounded-[10px] px-4 transition" [ngClass]="fieldStateClasses">
    <label *ngIf="label" class="pointer-events-none absolute left-4 transition-all duration-200" [ngClass]="labelStateClasses">
      <span *ngIf="isHtmlContent(label)" [innerHTML]="label"></span>
      <span *ngIf="!isHtmlContent(label)">{{ label }}</span>
      <span *ngIf="required" class="text-red-500">*</span>
    </label>

    <!-- 🔥 DROPDOWN
    <select
      *ngIf="options?.length"
       class="h-11 w-full rounded-md border border-white/20 bg-white/10 px-3 text-sm text-white outline-none transition placeholder:text-white/50 focus:border-[#61C2FF] focus:ring-1 focus:ring-[#61C2FF] disabled:cursor-not-allowed disabled:opacity-60"
      [disabled]="disabled"
      [value]="value"
      (change)="onSelect($event)"
      (blur)="markTouched()"
    >
      <option value="">Select {{ label }}</option>

      <option *ngFor="let opt of options" [value]="opt.value">
        {{ opt.label }}
      </option>
    </select> -->

    <!-- 🔥 INPUT -->
    <input
      *ngIf="!options?.length"
      [type]="type"
      [placeholder]="focused ? placeholder : ''"
      [disabled]="disabled"
      [readOnly]="readonly"
      [value]="value"
      [attr.min]="numberMinAttr"
      [attr.max]="numberMaxAttr"
      [attr.step]="numberStepAttr"
      (input)="onInput($event)"
      (focus)="focused = true"
      (blur)="focused = false; markTouched()"
      class="w-full bg-transparent border-none outline-none pt-3 text-sm text-white placeholder:text-white/50 disabled:cursor-not-allowed"
    />
   </div>
  </div>
  `,
})
export class InputComponent implements ControlValueAccessor {

  private readonly cdr = inject(ChangeDetectorRef);

  @Input() placeholder = '';
  // `alphanumeric` is kept as a compatibility alias used by legacy forms.
  @Input() type: 'text' | 'number' | 'email' | 'password' | 'date' | 'alphanumeric' = 'text';
  @Input() label = '';
  @Input() disabled = false;
  @Input() readonly: boolean | '' = false;
  @Input() required: boolean | '' = false;
  /** For `type="number"`: HTML min / max / step + live clamp vs min/max */
  @Input() min: number | string | null = null;
  @Input() max: number | string | null = null;
  @Input() step: number | string | null = null;

  // 🔥 NEW (for dropdown)
  @Input() options: { label: string; value: any }[] = [];

  value: any = '';
  focused = false;

  /** Floating-label field surface: border/background per focus + readonly state. */
  get fieldStateClasses(): string {
    if (this.readonly || this.disabled) {
      return 'border border-white/70 bg-white/[0.12] opacity-90';
    }
    return this.focused
      ? 'border border-white/70 bg-white/[0.08]'
      : 'border border-white/40 bg-white/[0.08]';
  }

  get hasValue(): boolean {
    return this.value !== '' && this.value !== null && this.value !== undefined;
  }

  /** Floating-label position: raised when focused or already has a value. */
  get labelStateClasses(): string {
    return this.focused || this.hasValue
      ? 'top-[3px] text-[11px] text-white/65'
      : 'top-1/2 -translate-y-1/2 text-sm text-white/75';
  }

  get numberMinAttr(): string | null {
    return this.type === 'number' && this.min !== null && this.min !== undefined && this.min !== ''
      ? String(this.min)
      : null;
  }

  get numberMaxAttr(): string | null {
    return this.type === 'number' && this.max !== null && this.max !== undefined && this.max !== ''
      ? String(this.max)
      : null;
  }

  get numberStepAttr(): string | null {
    return this.type === 'number' && this.step !== null && this.step !== undefined && this.step !== ''
      ? String(this.step)
      : null;
  }

  private parseBound(v: number | string | null | undefined): number | null {
    if (v === null || v === undefined || v === '') return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  private onChange = (value: any) => { };
  private onTouched = () => { };

  writeValue(value: any): void {
    this.value = value ?? '';
    this.cdr.markForCheck();
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
    this.cdr.markForCheck();
  }

  onInput(event: Event) {
    const target = event.target as HTMLInputElement;
    let val = target.value;

    if (this.type === 'number') {
      if (this.step && val.includes('.')) {
      const stepStr = String(this.step);

      if (stepStr.includes('.')) {
        const allowedDecimals = stepStr.split('.')[1].length;

        const [integer, decimal] = val.split('.');

        if (decimal.length > allowedDecimals) {
          val = `${integer}.${decimal.substring(0, allowedDecimals)}`;
          target.value = val;
        }
      }
    }

      const minN = this.parseBound(this.min);
      const maxN = this.parseBound(this.max);
      if (val !== '' && val !== '-') {
        const n = Number(val);
        if (!Number.isNaN(n)) {
          let next = n;
          if (minN !== null && next < minN) next = minN;
          if (maxN !== null && next > maxN) next = maxN;
          if (next !== n) {
            val = String(next);
            target.value = val;
          }
        }
      }
    }

    this.value = val;
    this.onChange(this.value);
  }

  // 🔥 NEW
  onSelect(event: Event) {
    const target = event.target as HTMLSelectElement;
    this.value = target.value;
    this.onChange(this.value);
  }

  markTouched() {
    this.onTouched();
  }
  isHtmlContent(value: unknown): boolean {
    if (typeof value !== 'string') return false;

    return /<\/?[a-z][\s\S]*>/i.test(value);
  }
}
