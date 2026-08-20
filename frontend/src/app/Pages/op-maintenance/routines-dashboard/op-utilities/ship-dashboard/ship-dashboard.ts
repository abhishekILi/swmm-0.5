import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MasterCard } from '../../../../refit-maintenance/master-card/master-card';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { ModalComponent } from '../../../../../shared/components/modal/modal.component';
import { NotificationService } from '../../../../../Core/services/notification/notification.service';
import { TANK_TYPE_FACTORS, TankType } from '../tank-management/tank-management.model';

interface TankGroupSummary {
  tank_type: TankType;
  subtext: string;
  count: number;
  held: number;
  capacity: number;
  fillPercent: number;
  tanks: { name: string; capacity100: number; capacity95: number; sounding: number; held: number; fillPercent: number; status: 'GOOD' | 'LOW' }[];
}

interface SoundingRow {
  tank_name: string;
  type: TankType;
  limit_mm: number;
  start_ras: number;
  sounding_mm: number | null;
  during_ras: number | null;
}

// No tank-master/sounding endpoint is wired up yet (closest candidate,
// `lookup_fuel_sounding/` in ems/urls.py, has no Call.ts wrapper) — these stay
// empty rather than showing fabricated tank names/soundings.
const GROUP_TANKS: Record<TankType, { name: string; sounding: number }[]> = {
  'HF/HSB Fuel': [],
  AVCAT: [],
  'Double Bottom': [],
  Overhead: [],
  'Dirty/Waste': [],
};

const GROUP_SUBTEXT: Record<TankType, string> = {
  'HF/HSB Fuel': 'Storage · Service tanks',
  AVCAT: 'Aviation fuel',
  'Double Bottom': 'DB Fwd · Aft · CTR',
  Overhead: 'GT1 · GT2 · GT3 · GT4',
  'Dirty/Waste': 'Dirty oil · Sludge',
};

function buildGroup(tank_type: TankType): TankGroupSummary {
  const factor = TANK_TYPE_FACTORS[tank_type];
  const tanks = GROUP_TANKS[tank_type].map((t) => {
    const held = Math.round(t.sounding * factor.volumePerMm * 100) / 100;
    const fillPercent = Math.round((held / factor.capacity100) * 1000) / 10;
    return {
      name: t.name,
      capacity100: factor.capacity100,
      capacity95: factor.capacity95,
      sounding: t.sounding,
      held,
      fillPercent,
      status: (fillPercent >= 90 ? 'GOOD' : 'LOW') as 'GOOD' | 'LOW',
    };
  });
  const held = Math.round(tanks.reduce((sum, t) => sum + t.held, 0) * 100) / 100;
  const capacity = tanks.length * factor.capacity100;
  return {
    tank_type,
    subtext: GROUP_SUBTEXT[tank_type],
    count: tanks.length,
    held,
    capacity,
    fillPercent: capacity ? Math.round((held / capacity) * 1000) / 10 : 0,
    tanks,
  };
}

const ALL_TANK_TYPES: TankType[] = ['HF/HSB Fuel', 'AVCAT', 'Double Bottom', 'Overhead', 'Dirty/Waste'];

@Component({
  selector: 'app-ship-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard, IconComponent, ModalComponent],
  templateUrl: './ship-dashboard.html',
  styleUrl: './ship-dashboard.css',
})
export class ShipDashboard {
  private readonly toastr = inject(NotificationService);

  readonly groups: TankGroupSummary[] = ALL_TANK_TYPES.map(buildGroup);
  readonly tankTypeOptions = ALL_TANK_TYPES;

  selectedGroup: TankGroupSummary | null = null;

  showSoundingModal = false;
  soundingDate = '';
  soundingTime = '';
  soundingTankType: TankType | '' = '';
  soundingRows: SoundingRow[] = [];

  /** The 4 groups charted below the summary cards (mirrors the source's 4 bar-chart panels — Dirty/Waste has no chart). */
  get chartGroups(): TankGroupSummary[] {
    return this.groups.filter((g) => g.tank_type !== 'Dirty/Waste');
  }

  get now(): Date {
    return new Date();
  }

  openDetails(group: TankGroupSummary): void {
    this.selectedGroup = group;
  }

  closeDetails(): void {
    this.selectedGroup = null;
  }

  openSoundingModal(): void {
    this.showSoundingModal = true;
    this.soundingDate = '';
    this.soundingTime = '';
    this.soundingTankType = '';
    this.soundingRows = [];
  }

  closeSoundingModal(): void {
    this.showSoundingModal = false;
  }

  onTankTypeChange(): void {
    if (!this.soundingTankType) {
      this.soundingRows = [];
      return;
    }
    const factor = TANK_TYPE_FACTORS[this.soundingTankType];
    this.soundingRows = GROUP_TANKS[this.soundingTankType].map((t) => ({
      tank_name: t.name,
      type: this.soundingTankType as TankType,
      limit_mm: Math.round(factor.capacity95 / factor.volumePerMm),
      start_ras: Math.round(t.sounding * factor.volumePerMm * 100) / 100,
      sounding_mm: null,
      during_ras: null,
    }));
  }

  calculateDuringRas(row: SoundingRow): void {
    if (row.sounding_mm == null) {
      row.during_ras = null;
      return;
    }
    const factor = TANK_TYPE_FACTORS[row.type];
    if (factor) {
      row.during_ras = Math.round(row.sounding_mm * factor.volumePerMm * 100) / 100;
    }
  }

  submitSounding(): void {
    this.toastr.success('Sounding updated successfully.');
    this.closeSoundingModal();
  }

  saveSoundingData(): void {
    this.submitSounding();
  }
}
