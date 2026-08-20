import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MasterCard } from '../../../../refit-maintenance/master-card/master-card';
import { ModalComponent } from '../../../../../shared/components/modal/modal.component';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { NotificationService } from '../../../../../Core/services/notification/notification.service';

type FuellingLocation = 'AT_SEA' | 'AT_HARBOUR';

interface RasMonitorRow {
  id: number;
  ser: number;
  fuellingStart: string;
  fuellingStop: string;
  location: FuellingLocation;
  receivedFromAt: string;
  receivedFuel: number;
  fuellingRateTph: number;
  status: 'Completed' | 'In Progress';
}

// No backend master-data or RAS-monitor endpoint exists yet in this codebase
// (checked ems/urls.py, dart/urls.py, services/network/call.ts) for harbour
// stations, sea sources, tank categories, fluids, or fuelling-log rows — these
// stay empty until those endpoints are added, rather than showing fabricated
// entity lists / rows.
const HARBOUR_STATIONS: string[] = [];
const SEA_SOURCES: string[] = [];
const RECEIVED_THROUGH: string[] = [];
const TANK_CATEGORIES: string[] = [];
const FLUIDS: string[] = [];

// Mirrors Django's tank/create_ras_monitor.html — logging RAS/harbour fuelling evolutions.
@Component({
  selector: 'app-ras-monitor',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard, ModalComponent, IconComponent],
  templateUrl: './ras-monitor.html',
  styleUrl: './ras-monitor.css',
})
export class RasMonitor {
  private readonly toastr = inject(NotificationService);

  readonly harbourStations = HARBOUR_STATIONS;
  readonly seaSources = SEA_SOURCES;
  readonly receivedThroughOptions = RECEIVED_THROUGH;
  readonly tankCategories = TANK_CATEGORIES;
  readonly fluids = FLUIDS;

  rows: RasMonitorRow[] = [];

  locationFilter: FuellingLocation | '' = '';
  startDateFrom = '';
  startDateTo = '';

  showCreateModal = false;

  fuellingLocation: FuellingLocation | '' = '';
  startDate = '';
  startTime = '';
  stopDate = '';
  stopTime = '';
  tankCategory = '';
  fluidInTank = '';
  receivedAtStation = '';
  receivedFromSource = '';
  receivedThrough = '';
  rasShipName = '';
  remarks = '';

  get durationDisplay(): string {
    if (!this.startDate || !this.startTime || !this.stopDate || !this.stopTime) return '';
    const start = new Date(`${this.startDate}T${this.startTime}`);
    const stop = new Date(`${this.stopDate}T${this.stopTime}`);
    const diffMs = stop.getTime() - start.getTime();
    if (diffMs <= 0) return '';
    const hrs = Math.floor(diffMs / 3_600_000);
    const mins = Math.round((diffMs % 3_600_000) / 60_000);
    return `${hrs}h ${mins}m`;
  }

  filteredRows(): RasMonitorRow[] {
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
    this.locationFilter = '';
    this.startDateFrom = '';
    this.startDateTo = '';
  }

  openCreateModal(): void {
    this.showCreateModal = true;
    this.fuellingLocation = '';
    this.startDate = '';
    this.startTime = '';
    this.stopDate = '';
    this.stopTime = '';
    this.tankCategory = '';
    this.fluidInTank = '';
    this.receivedAtStation = '';
    this.receivedFromSource = '';
    this.receivedThrough = '';
    this.rasShipName = '';
    this.remarks = '';
  }

  closeCreateModal(): void {
    this.showCreateModal = false;
  }

  createRasMonitor(): void {
    if (!this.fuellingLocation || !this.startDate || !this.startTime || !this.tankCategory || !this.fluidInTank) {
      this.toastr.warning('Fuelling Location, Fuelling Start Date/Time, Tank Category and Fluid in Tank are required.');
      return;
    }
    const nextSer = this.rows.length ? Math.max(...this.rows.map((r) => r.ser)) + 1 : 1;
    this.rows = [
      ...this.rows,
      {
        id: nextSer,
        ser: nextSer,
        fuellingStart: `${this.startDate} ${this.startTime}`,
        fuellingStop: this.stopDate && this.stopTime ? `${this.stopDate} ${this.stopTime}` : '',
        location: this.fuellingLocation,
        receivedFromAt: this.fuellingLocation === 'AT_HARBOUR' ? this.receivedAtStation : this.receivedFromSource,
        receivedFuel: 0,
        fuellingRateTph: 0,
        status: 'In Progress',
      },
    ];
    this.toastr.success('RAS Monitor created.');
    this.closeCreateModal();
  }
}
