import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MasterCard } from '../../../../refit-maintenance/master-card/master-card';

interface RasHistoryRow {
  id: number;
  ser: number;
  fuellingStart: string;
  fuellingStop: string;
  location: 'AT_SEA' | 'AT_HARBOUR';
  receivedFromAt: string;
  receivedFuel: number;
  fuellingRateTph: number;
}

// Mirrors Django's tank/ras_monitor_history.html — completed fuelling evolutions.
// No backend endpoint for RAS/fuelling history exists yet in this codebase
// (checked ems/urls.py, dart/urls.py, services/network/call.ts) — this stays
// empty until that endpoint is added, rather than showing fabricated rows.
@Component({
  selector: 'app-ras-history',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard],
  templateUrl: './ras-history.html',
})
export class RasHistory {
  rows: RasHistoryRow[] = [];

  startDateFrom = '';
  startDateTo = '';
  locationFilter: 'AT_SEA' | 'AT_HARBOUR' | '' = '';

  filteredRows(): RasHistoryRow[] {
    let rows = this.rows;
    if (this.locationFilter) {
      rows = rows.filter((r) => r.location === this.locationFilter);
    }
    if (this.startDateFrom) {
      rows = rows.filter((r) => r.fuellingStart.slice(0, 10) >= this.startDateFrom);
    }
    if (this.startDateTo) {
      rows = rows.filter((r) => r.fuellingStart.slice(0, 10) <= this.startDateTo);
    }
    return rows;
  }

  clearFilters(): void {
    this.startDateFrom = '';
    this.startDateTo = '';
    this.locationFilter = '';
  }
}
