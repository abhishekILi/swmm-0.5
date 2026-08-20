import {
  Component,
  Input,
  ViewChild,
  ElementRef,
  HostListener,
  signal,
  computed,
  forwardRef,
  input,
  effect,
  inject, OnInit, OnDestroy,
  ChangeDetectionStrategy,
  output
} from "@angular/core";
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from "@angular/forms";
import { IconComponent } from "../icon/icon.component";

export interface DropdownOption {
  label: string;
  value: string | number | boolean;
}

@Component({
  selector: "app-select-input",
  standalone: true,
  imports: [IconComponent],
  templateUrl: "./select-input.html",
  styleUrls: ["./select-input.css"],
  host: {
    '[class.glass-popup]': 'glassPopup',
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => SelectInput),
      multi: true,
    },
  ],
})
export class SelectInput implements ControlValueAccessor, OnInit, OnDestroy {
  @Input() label = "";
  @Input() placeholder = "Search...";
  @Input() glassPopup = false;
  required = input(false);
  options = input<DropdownOption[]>([]);
  @ViewChild("searchBox")
  searchBox!: ElementRef<HTMLInputElement>;
  isOpen = signal(false);
  searchText = signal("");
  selectedLabel = signal("");
  serverSearch = input(false);
  searchChange = output<string>();
  public static readonly openedDropdown = signal<string | null>(null);
  // dropdownId = crypto.randomUUID();
  private static nextId = 0;
  error = input(false);
  /** Red placeholder text only (no border) — the live "this is required" hint shown before the
   * user has attempted to submit. `error` is the fuller post-submit treatment (border + placeholder). */
  placeholderError = input(false);
  dropdownId = `dropdown-${SelectInput.nextId++}`;
  // dropdownId = "124";
  value: unknown = null;
  readonly = input(false);

  readonly elementRef = inject(ElementRef);
  disabledState = signal(false);

  /** Lets a parent template disable this control directly, e.g. `[disabled]="!parentField"`
   * for cascading dropdowns — independent of the ControlValueAccessor disabled state. */
  @Input()
  set disabled(value: boolean | undefined | null) {
    this.disabledState.set(!!value);
  }

  formatLabel(label: string): string {
    if (!label) {
      return '';
    }

    const formatted = label
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .replace(/[_-]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();

    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
  }


  constructor() {

    // Updates selected label whenever options OR value changes
    effect(() => {
      const options = this.options();

      const selected = options.find(
        option => String(option.value) === String(this.value)
      );

      this.selectedLabel.set(selected?.label ?? '');
    });

    effect(() => {
      const active = SelectInput.openedDropdown();

      this.isOpen.set(active === this.dropdownId);

      if (this.isOpen()) {
        setTimeout(() => {
          this.searchBox?.nativeElement?.focus();
        });
      }
    });
  }

  ngOnInit(): void {
    document.addEventListener(
      'close-all-select-dropdowns',
      this.handleCloseDropdown
    );
  }
  ngOnDestroy(): void {
    document.removeEventListener(
      'close-all-select-dropdowns',
      this.handleCloseDropdown
    );
  }
  handleCloseDropdown = () => {
    SelectInput.openedDropdown.set(null);
  };



  filteredOptions = computed(() => {
    if (this.serverSearch()) {
      return this.options();
    }
    const search = this.searchText()?.toLowerCase() || '';

    return this.options().filter((option) =>
      (option?.label ?? '').toLowerCase().includes(search)
    );
  });


  private onChange: (value: unknown) => void = () => undefined;
  private onTouched: () => void = () => undefined;



  writeValue(value: unknown): void {
    this.value = value as DropdownOption['value'] | null;
    const selected = this.options().find(
      (option) => String(option.value) === String(this.value),
    );
    this.selectedLabel.set(selected?.label ?? '');
    this.searchText.set('');
  }

  registerOnChange(fn: (value: unknown) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }
  setDisabledState(isDisabled: boolean): void {
    this.disabledState.set(isDisabled);
  }
  toggleDropdown(): void {
    if (this.disabledState() || this.readonly()) {
      return;
    }
    if (SelectInput.openedDropdown() === this.dropdownId) {
      SelectInput.openedDropdown.set(null);
    } else {
      SelectInput.openedDropdown.set(this.dropdownId);
    }
  }

  updateSearch(event: Event): void {
    const value = (event.target as HTMLInputElement).value;

    this.searchText.set(value);

    if (this.serverSearch()) {
      this.searchChange.emit(value);
    }
  }

  selectOption(option: DropdownOption): void {
    if (this.disabledState() || this.readonly()) {
      return;
    }
    this.value = option.value;
    this.selectedLabel.set(option.label);
    this.onChange(option.value);
    this.onTouched();
    this.searchText.set("");
    // this.isOpen.set(false);
    SelectInput.openedDropdown.set(null);
  }

  clearSelection(event: MouseEvent): void {
    event.stopPropagation();

    if (this.disabledState() || this.readonly()) {
      return;
    }

    this.value = null;
    this.selectedLabel.set('');
    this.searchText.set('');

    this.onChange(null);
    this.onTouched();

    SelectInput.openedDropdown.set(null);
  }

  preventClose(event: Event): void {
    event.stopPropagation();
  }

  @HostListener("document:click", ["$event"])
  closeDropdown(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target as Node)) {
      if (SelectInput.openedDropdown() === this.dropdownId) {
        SelectInput.openedDropdown.set(null);
      }
    }
  }
}
