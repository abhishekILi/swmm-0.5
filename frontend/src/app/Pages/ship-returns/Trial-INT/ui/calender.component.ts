import {
  ChangeDetectorRef,
  Component,
  Input,
  forwardRef,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
} from '@angular/forms';

@Component({
  selector: 'app-calendar',
  standalone: true,
  imports: [CommonModule],
template: `
<div class="w-full group flex flex-col">
  <div class="relative flex h-[45px] w-full items-center rounded-[10px] px-4 transition focus-within:border-white/70" [ngClass]="fieldStateClasses">
    <label *ngIf="label" class="pointer-events-none absolute left-4 top-[3px] text-[11px] text-white/65">
      {{ label }}
      <span *ngIf="required" class="text-red-500">*</span>
    </label>

    <input
      type="date"
      class="w-full border-none bg-transparent pt-3 text-sm text-white outline-none disabled:cursor-not-allowed"
      [value]="value"
      [disabled]="disabled"
      [attr.min]="min"
      [attr.max]="max"
      [readonly]="readonly"
      (input)="onInput($event)"
      (blur)="markTouched()"
    />
  </div>
</div>
`,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CalenderComponent),
      multi: true,
    },
  ],
})
export class CalenderComponent implements ControlValueAccessor {
  private readonly cdr = inject(ChangeDetectorRef);
  @Input() label = '';
  @Input() placeholder = '';
  @Input() disabled = false;
  @Input() min?: string;
  @Input() max?: string;
  @Input() required = false;
  @Input() readonly = false;
  value = '';

  /** Field surface: border/background per readonly state. */
  get fieldStateClasses(): string {
    return this.readonly || this.disabled
      ? 'border border-white/70 bg-white/[0.12] opacity-90'
      : 'border border-white/40 bg-white/[0.08]';
  }

  private onChange = (value: string) => {};
  private onTouched = () => {};

  writeValue(value: any): void {
    if (!value) {
      this.value = '';
      this.cdr.markForCheck();
      return;
    }

    // Accept Date object or string
    if (value instanceof Date) {
      this.value = value.toISOString().split('T')[0];
    } else {
      this.value = value;
    }
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
    const value = (event.target as HTMLInputElement).value;
    this.value = value;
    this.onChange(value);
  }

  markTouched() {
    this.onTouched();
  }
}
