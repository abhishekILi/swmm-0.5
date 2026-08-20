import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MasterCard } from '../../../../refit-maintenance/master-card/master-card';
import { NotificationService } from '../../../../../Core/services/notification/notification.service';

type MasterTab = 'pol-types' | 'pol-names' | 'tank-category' | 'tank-location';

interface PolTypeRow { id: number; ser: number; polType: string }
interface PolNameRow { id: number; ser: number; polName: string; polType: string; unit: string }
interface TankCategoryRow { id: number; ser: number; categoryName: string; manualName: string; pol: string }
interface TankLocationRow { id: number; ser: number; locationName: string }

// Mirrors Django's tank/tank_masters.html — sidebar-nav'd reference-data CRUD for the
// Onboard POL Status module (Fluid/POL Types, Fluid/POL Names, Tank Category, Tank Location).
@Component({
  selector: 'app-tank-masters',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard],
  templateUrl: './tank-masters.html',
  styleUrl: './tank-masters.css',
})
export class TankMasters {
  private readonly toastr = inject(NotificationService);

  activeTab: MasterTab = 'pol-types';

  polTypes: PolTypeRow[] = [];
  polNames: PolNameRow[] = [];
  tankCategories: TankCategoryRow[] = [];
  tankLocations: TankLocationRow[] = [];

  newPolType = '';
  newPolName = '';
  newPolNameType = '';
  newPolNameUnit = 'Litres';
  newCategoryName = '';
  newCategoryManualName = '';
  newCategoryPol = '';
  newLocationName = '';

  setTab(tab: MasterTab): void {
    this.activeTab = tab;
  }

  private nextSer(rows: { ser: number }[]): number {
    return rows.length ? Math.max(...rows.map((r) => r.ser)) + 1 : 1;
  }

  addPolType(): void {
    if (!this.newPolType.trim()) {
      this.toastr.warning('Enter a Fluid/POL Type name.');
      return;
    }
    const ser = this.nextSer(this.polTypes);
    this.polTypes = [...this.polTypes, { id: ser, ser, polType: this.newPolType.trim() }];
    this.newPolType = '';
  }

  removePolType(row: PolTypeRow): void {
    this.polTypes = this.polTypes.filter((r) => r.id !== row.id);
  }

  addPolName(): void {
    if (!this.newPolName.trim() || !this.newPolNameType) {
      this.toastr.warning('Enter a Fluid/POL Name and select its Type.');
      return;
    }
    const ser = this.nextSer(this.polNames);
    this.polNames = [...this.polNames, { id: ser, ser, polName: this.newPolName.trim(), polType: this.newPolNameType, unit: this.newPolNameUnit }];
    this.newPolName = '';
    this.newPolNameType = '';
  }

  removePolName(row: PolNameRow): void {
    this.polNames = this.polNames.filter((r) => r.id !== row.id);
  }

  addTankCategory(): void {
    if (!this.newCategoryName.trim() || !this.newCategoryManualName.trim()) {
      this.toastr.warning('Enter both Category Name and Manual Name.');
      return;
    }
    const ser = this.nextSer(this.tankCategories);
    this.tankCategories = [
      ...this.tankCategories,
      { id: ser, ser, categoryName: this.newCategoryName.trim(), manualName: this.newCategoryManualName.trim(), pol: this.newCategoryPol },
    ];
    this.newCategoryName = '';
    this.newCategoryManualName = '';
    this.newCategoryPol = '';
  }

  removeTankCategory(row: TankCategoryRow): void {
    this.tankCategories = this.tankCategories.filter((r) => r.id !== row.id);
  }

  addTankLocation(): void {
    if (!this.newLocationName.trim()) {
      this.toastr.warning('Enter a Location Name.');
      return;
    }
    const ser = this.nextSer(this.tankLocations);
    this.tankLocations = [...this.tankLocations, { id: ser, ser, locationName: this.newLocationName.trim() }];
    this.newLocationName = '';
  }

  removeTankLocation(row: TankLocationRow): void {
    this.tankLocations = this.tankLocations.filter((r) => r.id !== row.id);
  }
}
