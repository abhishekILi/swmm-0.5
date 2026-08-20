import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MasterCard } from '../../refit-maintenance/master-card/master-card';
import { IconComponent } from '../../../shared/components/icon/icon.component';
import { NotificationService } from '../../../Core/services/notification/notification.service';
import { OperationMaintenance } from '../../../services/operation-maintenance';

interface MaintenancePeriodViewRow {
  period: string;
  occasion: string;
  start_date: string;
  stop_date: string;
  current: boolean;
}

@Component({
  selector: 'app-maintenance-periods',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard, IconComponent],
  templateUrl: './maintenance-periods.html',
  styleUrl: './maintenance-periods.css',
})
export class MaintenancePeriods implements OnInit {
  private readonly toastr = inject(NotificationService);
  private readonly opMaintenance = inject(OperationMaintenance);
  private readonly cdr = inject(ChangeDetectorRef);

  rows: MaintenancePeriodViewRow[] = [];
  loading = true;

  get occasions(): string[] {
    return [...new Set(this.rows.map((r) => r.occasion))];
  }

  periodFilter = 'All';
  occasionFilter = 'All';
  fromDate = '';
  toDate = '';
  pageSize = 10;
  search = '';

  columnSearch = { period: '', occasion: '', start_date: '', stop_date: '' };

  ngOnInit(): void {
    this.loadMaintenancePeriods();
  }

  async loadMaintenancePeriods(): Promise<void> {
    this.loading = true;
    try {
      const data = await this.opMaintenance.getMaintenancePeriodsList();
      this.rows = data.map((row) => ({
        period: row.maintenance_period,
        occasion: row.occasion,
        start_date: row.start_date,
        stop_date: row.end_date,
        current: row.is_current,
      }));
    } finally {
      this.loading = false;
      this.cdr.detectChanges();
    }
  }

  get filteredRows() {
    return this.rows.filter((row) => {
      const matchesPeriod =
        this.periodFilter === 'All' || row.period.toLowerCase() === this.periodFilter.toLowerCase();
      const matchesOccasion = this.occasionFilter === 'All' || row.occasion === this.occasionFilter;
      const matchesFrom = !this.fromDate || row.start_date >= this.fromDate;
      const matchesTo = !this.toDate || (row.stop_date ? row.stop_date <= this.toDate : true);

      const matchesColumnSearch =
        row.period.toLowerCase().includes(this.columnSearch.period.toLowerCase()) &&
        row.occasion.toLowerCase().includes(this.columnSearch.occasion.toLowerCase()) &&
        row.start_date.toLowerCase().includes(this.columnSearch.start_date.toLowerCase()) &&
        (row.stop_date || '').toLowerCase().includes(this.columnSearch.stop_date.toLowerCase());

      const globalText = `${row.period} ${row.occasion} ${row.start_date} ${row.stop_date}`.toLowerCase();
      const matchesGlobalSearch = !this.search || globalText.includes(this.search.toLowerCase());

      return matchesPeriod && matchesOccasion && matchesFrom && matchesTo && matchesColumnSearch && matchesGlobalSearch;
    });
  }

  clearFilters(): void {
    this.periodFilter = 'All';
    this.occasionFilter = 'All';
    this.fromDate = '';
    this.toDate = '';
    this.search = '';
    this.columnSearch = { period: '', occasion: '', start_date: '', stop_date: '' };
  }

  print(): void {
    window.print();
  }

  exportPlaceholder(format: string): void {
    this.toastr.info(`Export to ${format} is not wired up yet — this is a placeholder action.`);
  }
}
