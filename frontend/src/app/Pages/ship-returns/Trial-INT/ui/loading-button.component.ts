import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-loading-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button
      type="button"
      [disabled]="disabled || loading"
      [attr.aria-busy]="loading"
      class="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
      [class.bg-blue-600]="color === 'blue'"
      [class.bg-green-600]="color === 'green'"
      [class.bg-slate-600]="color !== 'blue' && color !== 'green'"
      (click)="clicked.emit()"
    >
      <span *ngIf="loading" class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"></span>
      <span>{{ label }}</span>
    </button>
  `,
})
export class LoadingButtonComponent {
  @Input() label = '';
  @Input() color = '';
  @Input() icon = '';
  @Input() loading = false;
  @Input() disabled = false;
  @Output() clicked = new EventEmitter<void>();
}
