import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  EventEmitter,
  forwardRef,
  HostListener,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  inject,
} from '@angular/core';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR } from '@angular/forms';

export interface CheckboxMultiSelectOption {
  label: string;
  value: number | string;
  disabled?: boolean;
}

@Component({
  selector: 'app-checkbox-multiselect',
  standalone: true,
  imports: [CommonModule, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CheckboxMultiselectComponent),
      multi: true,
    },
  ],
  template: `
    <div class="w-full">
      <div class="relative" [class.opacity-60]="disabled">
        <button
          type="button"
          class="relative flex min-h-[45px] w-full items-center rounded-[10px] pl-4 pr-10 text-left transition"
          [ngClass]="triggerStateClasses"
          [disabled]="disabled"
          (click)="togglePanel($event)"
        >
          <label *ngIf="label" class="pointer-events-none absolute left-4 right-10 truncate transition-all duration-200" [ngClass]="labelStateClasses">
            {{ label }}
            <span *ngIf="required" class="text-red-500">*</span>
          </label>

           <span class="truncate pt-3 text-sm text-white/50" *ngIf="!selectedValues.length">
            {{ placeholder || '--Select--' }}
          </span>
           <span class="truncate pt-3 text-sm text-white" *ngIf="selectedValues.length">
            {{ selectedSummary }}
          </span>
          <i
             class="fa-solid absolute right-4 top-1/2 -translate-y-1/2 text-xs text-white/50"
            [ngClass]="panelOpen ? 'fa-chevron-up' : 'fa-chevron-down'"
          ></i>
        </button>

        <div
          *ngIf="panelOpen"
           class="absolute left-0 right-0 top-[calc(100%+4px)] z-[200] overflow-hidden rounded-md border border-white/20 bg-[#0d2438] text-white shadow-xl"
          (click)="$event.stopPropagation()"
        >
           <div class="border-b border-white/15 bg-black/10 p-2">
            <input
              type="text"
              [(ngModel)]="searchTerm"
              placeholder="Search..."
               class="w-full rounded border border-white/20 bg-white/10 px-3 py-2 text-sm text-white outline-none placeholder:text-white/50 focus:border-[#61C2FF] focus:ring-1 focus:ring-[#61C2FF]"
              (click)="$event.stopPropagation()"
            />
          </div>

          <div
            *ngIf="selectAllEnabled"
             class="flex items-center justify-between border-b border-white/15 px-3 py-2 text-xs"
          >
             <button type="button" class="font-semibold text-white/80 hover:text-[#61C2FF]" (click)="selectAll($event)">
              Select all
            </button>
             <button type="button" class="font-semibold text-white/60 hover:text-red-400" (click)="clearAll($event)">
              Clear
            </button>
          </div>

          <div class="max-h-52 overflow-y-auto py-1">
            <label
              *ngFor="let option of filteredOptions"
               class="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm text-white/90 hover:bg-white/10"
              [class.opacity-50]="option.disabled"
              [class.cursor-not-allowed]="option.disabled"
            >
              <input
                type="checkbox"
                 class="h-4 w-4 shrink-0 accent-[#61C2FF]"
                [checked]="isSelected(option.value)"
                [disabled]="disabled || option.disabled"
                (change)="onCheckboxChange(option, $event)"
              />
               <span class="text-white/80">{{ option.label }}</span>
            </label>
             <p *ngIf="filteredOptions.length === 0" class="px-3 py-4 text-center text-sm text-white/50
">
              No options found
            </p>
          </div>
        </div>
      </div>

      <div *ngIf="selectedValues.length" class="mt-2 flex flex-wrap gap-2">
        <span
          *ngFor="let item of selectedLabels"
           class="inline-flex max-w-full items-center gap-1.5 rounded-full border border-[#4f8fd5] bg-[#1069AB] py-1 pl-2.5 pr-1 text-xs font-semibold leading-tight text-white"
        >
          <span class="truncate">{{ item.label }}</span>
          <button
            type="button"
             class="inline-flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border border-white/30 bg-white/10 text-[10px] leading-none text-white/70 transition hover:border-[#61C2FF] hover:bg-[#1069AB] hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            [disabled]="disabled"
            aria-label="Remove"
            (click)="removeValue(item.value, $event)"
          >
            <i class="fa-solid fa-times"></i>
          </button>
        </span>
      </div>
    </div>
  `,
})
export class CheckboxMultiselectComponent implements ControlValueAccessor, OnChanges {
  @Input() label = '';
  @Input() placeholder = '';
  @Input() required = false;
  @Input() selectAllEnabled = true;
  @Input() disabled = false;
  @Input() options: CheckboxMultiSelectOption[] = [];

  @Output() selectionChange = new EventEmitter<(number | string)[]>();

  panelOpen = false;
  searchTerm = '';
  selectedValues: (number | string)[] = [];

  /** Floating-label field surface: border/background per open state. */
  get triggerStateClasses(): string {
    return this.panelOpen
      ? 'border border-white/70 bg-white/[0.08]'
      : 'border border-white/40 bg-white/[0.08]';
  }

  /** Floating-label position: raised when open or at least one value is selected. */
  get labelStateClasses(): string {
    return this.panelOpen || this.selectedValues.length > 0
      ? 'top-[3px] text-[11px] text-white/65'
      : 'top-1/2 -translate-y-1/2 text-sm text-white/75';
  }

  private onChange: (value: (number | string)[]) => void = () => {};
  private onTouched: () => void = () => {};
  private readonly elementRef = inject(ElementRef<HTMLElement>);

  get filteredOptions(): CheckboxMultiSelectOption[] {
    const term = this.searchTerm.trim().toLowerCase();
    if (!term) return this.options;
    return this.options.filter((o) => String(o.label).toLowerCase().includes(term));
  }

  get selectedLabels(): CheckboxMultiSelectOption[] {
    return this.selectedValues.map((value) => {
      const found = this.options.find((o) => this.sameValue(o.value, value));
      if (found) return found;
      return { label: String(value), value };
    });
  }

  get selectedSummary(): string {
    const labels = this.selectedLabels.map((o) => o.label).filter(Boolean);
    if (!labels.length) return '';
    if (labels.length === 1) return labels[0];
    if (labels.length === 2) return `${labels[0]}, ${labels[1]}`;
    return `${labels[0]}, ${labels[1]} +${labels.length - 2} more`;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['options'] || changes['disabled']) {
      this.syncSelectedFromOptions();
    }
  }

  writeValue(value: (number | string)[] | null): void {
    this.selectedValues = Array.isArray(value)
      ? value.map((v) => Number(v)).filter((v) => !Number.isNaN(v))
      : [];
    this.syncSelectedFromOptions();
  }

  private syncSelectedFromOptions(): void {
    if (!this.selectedValues.length || !this.options.length) return;
    // Keep prefilled IDs until every selected value has a matching option (edit modal load).
    const hasUnknown = this.selectedValues.some(
      (v) => !this.options.some((o) => this.sameValue(o.value, v)),
    );
    if (hasUnknown) return;
    this.selectedValues = this.selectedValues.filter((v) =>
      this.options.some((o) => this.sameValue(o.value, v)),
    );
  }

  registerOnChange(fn: (value: (number | string)[]) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
    if (isDisabled) this.panelOpen = false;
  }

  togglePanel(event: MouseEvent): void {
    event.stopPropagation();
    if (this.disabled) return;
    this.panelOpen = !this.panelOpen;
    if (!this.panelOpen) this.searchTerm = '';
    this.onTouched();
  }

  isSelected(value: number | string): boolean {
    return this.selectedValues.some((v) => this.sameValue(v, value));
  }

  onCheckboxChange(option: CheckboxMultiSelectOption, event: Event): void {
    event.stopPropagation();
    if (option.disabled || this.disabled) return;

    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      if (!this.isSelected(option.value)) {
        this.selectedValues = [...this.selectedValues, option.value];
      }
    } else {
      this.selectedValues = this.selectedValues.filter((v) => !this.sameValue(v, option.value));
    }
    this.emitChange();
  }

  removeValue(value: number | string, event: MouseEvent): void {
    event.stopPropagation();
    this.selectedValues = this.selectedValues.filter((v) => !this.sameValue(v, value));
    this.emitChange();
  }

  selectAll(event: MouseEvent): void {
    event.stopPropagation();
    const enabled = this.filteredOptions.filter((o) => !o.disabled).map((o) => o.value);
    this.selectedValues = Array.from(
      new Set([...this.selectedValues, ...enabled]),
    );
    this.emitChange();
  }

  clearAll(event: MouseEvent): void {
    event.stopPropagation();
    this.selectedValues = [];
    this.emitChange();
  }

  private emitChange(): void {
    this.onChange(this.selectedValues);
    this.selectionChange.emit(this.selectedValues);
    this.onTouched();
  }

  private sameValue(a: number | string, b: number | string): boolean {
    return String(a) === String(b);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.panelOpen) return;
    const target = event.target as Node | null;
    if (target && this.elementRef.nativeElement.contains(target)) return;
    this.panelOpen = false;
    this.searchTerm = '';
  }
}
