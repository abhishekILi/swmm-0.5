import { ChangeDetectionStrategy, Component } from '@angular/core';
import { DynamicFormHostComponent } from '../../angulerFromconverting/dynamic-form-host.component';

/**
 * Compatibility entry point for the legacy HITU route set.
 * HITU schemas are rendered by the same Trial-INT host as E-POL/trial forms,
 * which keeps prefill, equipment switching, drafts, and submit behavior on the
 * current API/services instead of importing the legacy HITU module.
 */
@Component({
  selector: 'app-hitu-form',
  standalone: true,
  imports: [DynamicFormHostComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<app-dynamic-form-host></app-dynamic-form-host>',
})
export class HituForm {}
