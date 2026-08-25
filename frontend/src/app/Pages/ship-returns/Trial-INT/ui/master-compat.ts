import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ICellRendererAngularComp } from 'ag-grid-angular';

@Component({
  selector: 'app-form-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="glass-card max-h-[90vh] overflow-hidden text-white shadow-[0_30px_80px_rgba(0,0,0,0.4)]">
      <header *ngIf="title" class="border-b border-white/10 px-5 py-3.5">
        <h2 class="text-[1.05rem] font-semibold leading-snug tracking-tight text-white">{{ title }}</h2>
      </header>
      <div class="max-h-[calc(90vh-58px)] overflow-y-auto p-5 custom-scrollbar">
        <ng-content></ng-content>
      </div>
    </section>
  `,
})
export class FormCardComponent { @Input() title = ''; }

@Component({
  selector: 'app-reusable-delete-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="open" class="fixed inset-0 z-[999999] flex items-center justify-center bg-black/60 p-4 backdrop-blur-md">
      <div class="glass-card w-full max-w-sm text-white shadow-[0_30px_80px_rgba(0,0,0,0.4)]">
        <div class="flex flex-col items-center gap-3 px-6 pb-2 pt-7 text-center">
          <div class="grid h-12 w-12 shrink-0 place-items-center rounded-full border border-rose-400/30 bg-rose-500/15 text-rose-300">
            <i class="fa-solid fa-triangle-exclamation text-lg" aria-hidden="true"></i>
          </div>
          <h2 class="text-base font-semibold text-white">Delete {{ entityType || 'Item' }}?</h2>
          <p class="text-sm leading-relaxed text-white/60">
            {{ message || ('Are you sure you want to delete' + (name ? ' “' + name + '”' : ' this ' + (entityType || 'item').toLowerCase()) + '? This action cannot be undone.') }}
          </p>
        </div>

        <div class="flex items-center justify-end gap-3 border-t border-white/10 px-5 py-4">
          <button type="button" [disabled]="loading" (click)="cancel.emit()"
            class="rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.98]">
            Cancel
          </button>
          <button type="button" [disabled]="loading" (click)="confirm.emit()"
            class="inline-flex items-center gap-2 rounded-lg border border-rose-400/40 bg-rose-500/80 px-4 py-2 text-sm font-semibold text-white shadow-lg transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60 active:scale-[0.98]">
            <i *ngIf="loading" class="fa-solid fa-circle-notch animate-spin text-sm" aria-hidden="true"></i>
            <span>{{ loading ? 'Deleting...' : 'Delete' }}</span>
          </button>
        </div>
      </div>
    </div>
  `,
})
export class ReusableDeleteDialogComponent {
  @Input() open = false; @Input() message = ''; @Input() loading = false; @Input() name = ''; @Input() entityType = '';
  @Output() confirm = new EventEmitter<void>(); @Output() cancel = new EventEmitter<void>();
}

@Component({
  selector: 'app-reusable-input-table',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="overflow-x-auto rounded-xl border border-white/15 bg-white/[0.04]">
      <table class="w-full min-w-[900px] border-collapse text-sm">
        <thead class="bg-white/[0.08]">
          <tr>
            <th *ngFor="let column of columns" class="border-r border-white/10 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wide text-white/70 last:border-r-0">
              {{ column.header || column.headerName }}
            </th>
            <th *ngIf="enableRowActions" class="w-40 border-white/10 px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wide text-white/70">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let row of data; let rowIndex = index" class="border-t border-white/10">
            <td *ngFor="let column of columns" class="border-r border-white/10 px-4 py-2 last:border-r-0">
              <span *ngIf="column.fieldType !== 'text' && column.fieldType !== 'select'" class="text-white/85">
                {{ row[column.field || column.key] }}
              </span>
              <input *ngIf="column.fieldType === 'text'" [(ngModel)]="row[column.field || column.key]"
                class="h-[42px] w-full rounded-[10px] border border-white/20 bg-white/[0.08] px-3 text-sm text-white outline-none placeholder:text-white/40 focus:border-[#61C2FF] focus:shadow-[0_0_8px_rgba(97,194,255,.4)]" />
              <select *ngIf="column.fieldType === 'select'" [(ngModel)]="row[column.field || column.key]"
                class="h-[42px] w-full rounded-[10px] border border-white/20 bg-white/[0.08] px-3 text-sm text-white outline-none focus:border-[#61C2FF] focus:shadow-[0_0_8px_rgba(97,194,255,.4)]">
                <option value="">Select</option>
                <option *ngFor="let option of column.options || []" [ngValue]="option.value">{{ option.label }}</option>
              </select>
            </td>
            <td *ngIf="enableRowActions" class="px-4 py-2">
              <div class="flex items-center justify-center gap-2">
                <button type="button" (click)="addRow()" class="grid h-8 w-8 place-items-center rounded-full border border-emerald-400/30 bg-emerald-500/10 text-emerald-300 transition hover:bg-emerald-500/20" title="Add row">
                  <i class="fa-solid fa-plus text-xs" aria-hidden="true"></i>
                </button>
                <button type="button" (click)="removeRow(rowIndex)" [disabled]="data.length === 1"
                  class="grid h-8 w-8 place-items-center rounded-full border border-rose-400/30 bg-rose-500/10 text-rose-300 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-35" title="Remove row">
                  <i class="fa-solid fa-minus text-xs" aria-hidden="true"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
})
export class ReusableInputTableComponent {
  @Input() data: any[] = [];
  @Input() columns: any[] = [];
  @Input() enableRowActions = false;
  @Input() isReadonly = false;

  addRow(): void {
    const row = this.columns.reduce((result, column) => {
      result[column.field || column.key] = column.field === 'sr_no' ? this.data.length + 1 : '';
      return result;
    }, {} as Record<string, unknown>);
    this.data.push(row);
  }

  removeRow(index: number): void {
    if (this.data.length <= 1) return;
    this.data.splice(index, 1);
    this.data.forEach((row, rowIndex) => {
      if ('sr_no' in row) row.sr_no = rowIndex + 1;
    });
  }
}
export type ReusableTableColumn = Record<string, any>;

interface AgActionCellAction {
  key: string;
  label?: string;
  iconClass?: string;
  hidden?: (row: any) => boolean;
}

interface AgActionCellParams {
  data: any;
  actions?: AgActionCellAction[];
  onAction?: (key: string, row: any) => void;
  onMainAction?: (row: any) => void;
}

const ACTION_TONE: Record<string, string> = {
  edit: 'border-sky-400/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20',
  view: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20',
  status: 'border-amber-400/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20',
  add: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20',
  delete: 'border-rose-400/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20',
};
const DEFAULT_TONE = 'border-white/20 bg-white/10 text-white/80 hover:bg-white/15';

@Component({
  selector: 'app-grid-action-cell',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex h-full items-center justify-center gap-2">
      <button *ngFor="let action of visibleActions" type="button" (click)="run(action)"
        [class]="'grid h-8 w-8 place-items-center rounded-full border transition ' + (tone(action.key))"
        [title]="action.label || action.key">
        <ng-container [ngSwitch]="action.key.toLowerCase()">
          <svg *ngSwitchCase="'edit'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4" aria-hidden="true">
            <path d="M13.8 3.3l2.9 2.9-9.4 9.4-3.9 1 1-3.9 9.4-9.4z"></path>
          </svg>
          <svg *ngSwitchCase="'delete'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4" aria-hidden="true">
            <path d="M3.5 5.5h13M7.5 5.5V4.4A1.4 1.4 0 0 1 8.9 3h2.2a1.4 1.4 0 0 1 1.4 1.4v1.1M6.5 6.5l.7 9.1A1.5 1.5 0 0 0 8.7 17h2.6a1.5 1.5 0 0 0 1.5-1.4l.7-9.1"></path>
          </svg>
          <svg *ngSwitchCase="'add'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4" aria-hidden="true">
            <path d="M10 4v12M4 10h12"></path>
          </svg>
          <svg *ngSwitchCase="'view'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4" aria-hidden="true">
            <path d="M1.7 10s3.2-5 8.3-5 8.3 5 8.3 5-3.2 5-8.3 5-8.3-5-8.3-5z"></path>
            <circle cx="10" cy="10" r="2.2"></circle>
          </svg>
          <svg *ngSwitchCase="'status'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4" aria-hidden="true">
            <circle cx="10" cy="10" r="7"></circle>
            <path d="M10 9v4M10 6.5h.01"></path>
          </svg>
          <i *ngSwitchDefault [class]="(action.iconClass || 'fa-solid fa-circle') + ' text-xs'" aria-hidden="true"></i>
        </ng-container>
      </button>
    </div>
  `,
})
export class AgActionCellComponent implements ICellRendererAngularComp {
  params!: AgActionCellParams;

  agInit(params: AgActionCellParams): void { this.params = params; }
  refresh(): boolean { return false; }

  get visibleActions(): AgActionCellAction[] {
    return (this.params?.actions || []).filter(action => !action.hidden?.(this.params.data));
  }

  tone(key: string): string { return ACTION_TONE[key] || DEFAULT_TONE; }

  run(action: AgActionCellAction): void {
    this.params.onAction?.(action.key, this.params.data);
  }
}

@Component({
  selector: 'app-transaction-table-tabs',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="mb-4 flex border-b border-gray-200 gap-1">
      <button *ngFor="let tab of tabs" type="button" (click)="selectTab(tab.value)"
        [class]="'px-4 py-2.5 text-sm font-semibold transition-all border-b-2 rounded-t-lg ' + (activeTab === tab.value ? 'border-sky-500 text-sky-600 bg-sky-50/70 font-bold' : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-100/60')">
        {{ tab.label }}
      </button>
    </div>
  `,
})
export class TransactionTableTabs {
  @Input() activeTab = 'draft';
  @Input() tabs: { label: string; value: string }[] = [];
  @Output() activeTabChange = new EventEmitter<string>();
  @Output() tabChange = new EventEmitter<string>();

  selectTab(val: string): void {
    this.activeTabChange.emit(val);
    this.tabChange.emit(val);
  }
}

@Component({
  selector: 'app-reusable-delete-dialog-dynamic-content',
  standalone: true,
  imports: [CommonModule, ReusableDeleteDialogComponent],
  template: `<app-reusable-delete-dialog [open]="open" [message]="message" (confirm)="confirm.emit()" (cancel)="cancel.emit()"></app-reusable-delete-dialog>`,
})
export class ReusableDeleteDialogDynamicContentComponent {
  @Input() open = false; @Input() message = '';
  @Output() confirm = new EventEmitter<void>(); @Output() cancel = new EventEmitter<void>();
}

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  template: ``,
})
export class ToastComponent {}

@Component({
  selector: 'app-shell-expension-ga-dialog-view',
  standalone: true,
  imports: [CommonModule],
  template: ``,
})
export class ShellExpensionGaDrawingDialogViewer {
  @Input() open = false;
  @Input() data: any;
  @Output() close = new EventEmitter<void>();
}

@Component({
  selector: 'app-reusable-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button [type]="type" [disabled]="loading || disabled" (click)="clicked.emit($event)"
      [class]="'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ' + customClass">
      <i *ngIf="loading" class="fa-solid fa-circle-notch animate-spin text-sm" aria-hidden="true"></i>
      <span>{{ label }}</span>
    </button>
  `,
})
export class ReusableButtonComponent {
  @Input() label = '';
  @Input() variant = 'primary';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() loading = false;
  @Input() disabled = false;
  @Input() icon: any;
  @Input() customClass = 'border border-white/20 bg-white/10 text-white hover:bg-white/15';
  @Output() clicked = new EventEmitter<Event>();
}

