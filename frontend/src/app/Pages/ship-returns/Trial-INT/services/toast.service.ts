import { Injectable } from '@angular/core';
import { NotificationService } from '../../../../Core/services/notification/notification.service';

/** Injectable bridge for legacy forms; rendering is handled by ngx-sonner. */
@Injectable({ providedIn: 'root' })
export class ToastService extends NotificationService {}
