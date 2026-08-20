import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
@Component({
  selector: 'app-pill-toggle',
  standalone: true,
  imports: [],
  templateUrl: './pill-toggle.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './pill-toggle.css',
})
export class PillToggle {
  @Input() options: string[] = [];
  @Input() value = '';
  @Output() valueChange = new EventEmitter<string>();

  select(option: string): void {
    if (option !== this.value) {
      this.value = option;
      this.valueChange.emit(option);
    }
  }
}
