import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { CommandMessagePayload } from '../home.model';

@Component({
  selector: 'app-command-message-modal',
  standalone: true,
  imports: [ReactiveFormsModule, IconComponent],
  templateUrl: './command-message-modal.html',
  styleUrl: './command-message-modal.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CommandMessageModalComponent {
  private readonly formBuilder = inject(FormBuilder);

  @Input() saving = false;
  @Input() errorMessage = '';

  @Output() closeModal = new EventEmitter<void>();
  @Output() saveMessage = new EventEmitter<CommandMessagePayload>();

  readonly commandMessageForm = this.formBuilder.nonNullable.group({
    message: ['', [Validators.required]],
    validTillDate: ['', [Validators.required]],
  });

  submit(): void {
    this.commandMessageForm.markAllAsTouched();
    if (this.commandMessageForm.invalid) {
      return;
    }

    const formValue = this.commandMessageForm.getRawValue();
    const message = formValue.message.trim();
    const validTillDate = formValue.validTillDate.trim();

    if (!message) {
      this.commandMessageForm.controls.message.setErrors({ required: true });
      return;
    }

    if (!validTillDate) {
      this.commandMessageForm.controls.validTillDate.setErrors({ required: true });
      return;
    }

    this.saveMessage.emit({
      message,
      validTillDate,
    });
  }
}
