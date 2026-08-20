import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../../services/toast.service';
import { Subscription } from 'rxjs';

type ToastItem = {
  message: string;
  type: 'success' | 'error' | 'warning';
};

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './toast.component.html',
  styleUrls: ['./toast.component.css'],
})
export class ToastComponent implements OnInit, OnDestroy {
  message = '';
  type: 'success' | 'error' | 'warning' = 'success';
  show = false;
  private readonly displayDuration = 3000;
  private readonly maxQueueSize = 5;
  private toastQueue: ToastItem[] = [];
  private isProcessingQueue = false;
  private hideTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private hideTimerStartedAt = 0;
  private remainingDuration = this.displayDuration;
  private toastSubscription: Subscription | null = null;

  constructor(
    private toastService: ToastService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.toastSubscription = this.toastService.toastState$.subscribe(
      ({ message, type }) => {
        const normalizedMessage = message.trim();
        const isSameAsVisible =
          this.show &&
          this.message === normalizedMessage &&
          this.type === type;
        const isAlreadyQueued = this.toastQueue.some(
          (toast) => toast.message === normalizedMessage && toast.type === type
        );

        // Avoid infinite-looking loop when the same API error is emitted repeatedly.
        if (isSameAsVisible || isAlreadyQueued) {
          return;
        }

        this.toastQueue.push({ message: normalizedMessage, type });
        if (this.toastQueue.length > this.maxQueueSize) {
          this.toastQueue.shift();
        }
        this.processQueue();
        this.cdr.detectChanges();
      }
    );
  }

  ngOnDestroy(): void {
    this.toastSubscription?.unsubscribe();
    if (this.hideTimeoutId) {
      clearTimeout(this.hideTimeoutId);
      this.hideTimeoutId = null;
    }
  }

  private processQueue(): void {
    if (this.isProcessingQueue || this.toastQueue.length === 0) {
      return;
    }

    this.isProcessingQueue = true;
    const nextToast = this.toastQueue.shift();
    if (!nextToast) {
      this.isProcessingQueue = false;
      return;
    }

    this.message = nextToast.message;
    this.type = nextToast.type;
    this.show = true;
    this.remainingDuration = this.displayDuration;
    this.cdr.detectChanges();

    this.startHideTimer();
  }

  pauseAutoDismiss(): void {
    if (!this.show || !this.hideTimeoutId) return;

    const elapsed = Date.now() - this.hideTimerStartedAt;
    this.remainingDuration = Math.max(this.remainingDuration - elapsed, 0);
    clearTimeout(this.hideTimeoutId);
    this.hideTimeoutId = null;
  }

  resumeAutoDismiss(): void {
    if (!this.show || this.hideTimeoutId) return;
    this.startHideTimer();
  }

  private startHideTimer(): void {
    if (!this.show) return;

    if (this.hideTimeoutId) {
      clearTimeout(this.hideTimeoutId);
    }

    this.hideTimerStartedAt = Date.now();
    this.hideTimeoutId = setTimeout(() => {
      this.show = false;
      this.message = '';
      this.isProcessingQueue = false;
      this.hideTimeoutId = null;
      this.remainingDuration = this.displayDuration;
      this.processQueue();
      this.cdr.detectChanges();
    }, this.remainingDuration);
  }
}
