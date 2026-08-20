import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { ShipDashboard } from '../ship-dashboard/ship-dashboard';
import { RasMonitor } from '../ras-monitor/ras-monitor';
import { RasHistory } from '../ras-history/ras-history';
import { TankMasters } from '../tank-masters/tank-masters';

type PolTab = 'dashboard' | 'ras-monitor' | 'history' | 'tank-masters';

// Mirrors Django's tank/tank_main_page.html — page-level tabs (Dashboard / RAS Monitor /
// History / Tank Masters) inside the "Onboard POL Status" header tab.
@Component({
  selector: 'app-onboard-pol-status',
  standalone: true,
  imports: [CommonModule, IconComponent, ShipDashboard, RasMonitor, RasHistory, TankMasters],
  templateUrl: './onboard-pol-status.html',
})
export class OnboardPolStatus {
  activeTab: PolTab = 'dashboard';

  setTab(tab: PolTab): void {
    this.activeTab = tab;
  }
}
