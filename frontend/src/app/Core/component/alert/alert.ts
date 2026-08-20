import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { AppService } from '../../services/app/app.service';

@Component({
  selector: 'app-alert',
  imports: [],
  templateUrl: './alert.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './alert.css',
})
export class Alert {
  appService = inject(AppService);


}
