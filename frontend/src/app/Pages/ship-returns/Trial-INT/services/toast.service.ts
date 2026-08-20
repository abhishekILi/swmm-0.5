import { Injectable } from '@angular/core';
import { ReplaySubject } from 'rxjs';

type ToastType = 'success' | 'error' | 'warning';

@Injectable({ providedIn: 'root' })
export class ToastService {
  private readonly toastSubject = new ReplaySubject<{ message: string; type: ToastType }>(1);
  readonly toastState$ = this.toastSubject.asObservable();

  showSuccess(message: string): void {
    this.toastSubject.next({ message: message?.trim() || 'Success', type: 'success' });
  }

  showError(message: string): void {
    this.toastSubject.next({ message: message?.trim() || 'Something went wrong.', type: 'error' });
  }

  showWarning(message: string): void {
    this.toastSubject.next({ message: message?.trim() || 'Warning', type: 'warning' });
  }
}
