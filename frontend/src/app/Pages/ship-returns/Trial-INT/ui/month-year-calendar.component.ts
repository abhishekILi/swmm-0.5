import {
  Component,
  Input,
  forwardRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
} from '@angular/forms';

@Component({
  selector: 'app-month-year-calendar, app-year-picker',
  standalone: true,
  imports: [CommonModule],
  template: `

<div class="w-full group flex flex-col gap-1.5">
  <div class="relative flex h-[45px] w-full items-center rounded-[10px] border border-white/40 bg-white/[0.08] px-4 transition focus-within:border-white/70">
    <label *ngIf="label" class="pointer-events-none absolute left-4 top-[3px] text-[11px] text-white/65">
      {{ label }}
      <span *ngIf="required" class="text-red-500">*</span>
    </label>

    <input
      type="month"
      class="w-full border-none bg-transparent pt-3 text-sm text-white outline-none disabled:cursor-not-allowed disabled:opacity-60"
      [value]="value"
      [disabled]="disabled"
      [attr.min]="min"
      [attr.max]="max"
      (input)="onInput($event)"
      (blur)="markTouched()" />
  </div>
</div>

  `,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MonthYearCalendarComponent),
      multi: true,
    },
  ],
})
export class MonthYearCalendarComponent implements ControlValueAccessor {

  @Input() label = '';
  @Input() placeholder = '';
  @Input() disabled = false;
  @Input() min?: string | number; // format: YYYY-MM or YYYY
  @Input() max?: string | number; // format: YYYY-MM or YYYY
  @Input() required = false;
  value = '';        // internal value (YYYY-MM)
  displayValue = ''; // formatted value (MM/YYYY)

  private onChange = (value: string) => {};
  private onTouched = () => {};

  writeValue(value: any): void {
    if (!value) {
      this.value = '';
      this.displayValue = '';
      return;
    }

    // Accept MM/YYYY format
    if (value.includes('/')) {
      const [month, year] = value.split('/');
      this.value = `${year}-${month}`;
      this.displayValue = value;
    } else {
      this.value = value;
      const [year, month] = value.split('-');
      this.displayValue = `${month}/${year}`;
    }
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  onInput(event: Event) {
    const rawValue = (event.target as HTMLInputElement).value; // YYYY-MM
    this.value = rawValue;

    if (!rawValue) {
      this.displayValue = '';
      this.onChange('');
      return;
    }

    const [year, month] = rawValue.split('-');
    this.displayValue = `${month}/${year}`;

    // Emit in MM/YYYY format
    this.onChange(this.displayValue);
  }

  markTouched() {
    this.onTouched();
  }
}
