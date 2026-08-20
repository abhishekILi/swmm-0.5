import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ColDef } from 'ag-grid-community';
import { Subject, debounceTime } from 'rxjs';

import { DataGrid } from '../../../../../shared/components/data-grid/data-grid';
import { Call } from '../../../../../services/network/call';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
export type SlipTab = 'gt' | 'gtg';

/* ---------- GT row shape ---------- */

interface GtSlipRow {
  date: string;
  gt_name: string;
  HPC: number;
  LPC: number;
  AirPr: number;
  ExtTemp: number;
  lpc_slip: number;
  air_slip: number;
  ext_slip: number;
}

interface GtgSlipRow {
  date: string;
  gt_name: string;
  el_load: number;
  ext_temp: number;
  amb_temp: number;
  gtg_slip: number;
}

export interface SlipHistoryResponse {
  activate: string;
  history_slip: GtSlipRow[];
  history_slip_gtg: GtgSlipRow[];
  gt_names?: string[];
}

@Component({
  selector: 'app-slip-history',
  standalone: true,
  imports: [CommonModule, FormsModule, DataGrid, IconComponent],
  templateUrl: './slip-history.html',
  styleUrl: './slip-history.scss',
})
export class SlipHistory implements OnInit {
  private callService = inject(Call);


  /* ------------------------------------------------------------------ */
  /*  Tab state                                                            */
  /* ------------------------------------------------------------------ */
  activeTab: SlipTab = 'gt';
  showDatePicker = false;
  presets = [
  'Today',
  'Yesterday',
  'Last 7 Days',
  'Last 30 Days',
  'This Month',
  // 'Last Month',
  'Custom'
];
  activePreset = 'Last 30 Days';

  selectedRangeLabel = 'May 17, 2026 - June 15, 2026';

  startDate = '';
  endDate = '';

  private readonly filtersChanged = new Subject<void>();

  setTab(tab: SlipTab): void {
    this.activeTab = tab;
    this.searchText = '';
    this.loadSlipHistory(this.startDate, this.endDate);
  }

  /* ------------------------------------------------------------------ */
  /*  Search                                                               */
  /* ------------------------------------------------------------------ */
  searchText = '';

  onSearchChange(): void {
    this.filtersChanged.next();
  }

  /* ------------------------------------------------------------------ */
  /*  GT Column definitions                                                */
  /* ------------------------------------------------------------------ */
 gtColumnDefs: ColDef[] = [
  {
    headerName: 'Date',
    field: 'date',
    flex: 1,
    minWidth: 140,
  },
  {
    headerName: 'GT Name',
    field: 'gt_name',
    flex: 1.5,
    minWidth: 220,
  },
  {
    headerName: 'HPC',
    field: 'HPC',
    flex: 1,
  },
  {
    headerName: 'LPC',
    field: 'LPC',
    flex: 1,
  },
  {
    headerName: 'Air Pressure',
    field: 'AirPr',
    flex: 1,
  },
  {
    headerName: 'Ext Temp',
    field: 'ExtTemp',
    flex: 1,
  },
  {
    headerName: 'LPC Slip',
    field: 'lpc_slip',
    flex: 1,
  },
  {
    headerName: 'Air Slip',
    field: 'air_slip',
    flex: 1,
  }
];

  /* ------------------------------------------------------------------ */
  /*  GTG Column definitions                                               */
  /* ------------------------------------------------------------------ */
 gtgColumnDefs: ColDef[] = [
  {
    headerName: 'Date',
    field: 'date',
    flex: 1,
  },
  {
    headerName: 'GT Name',
    field: 'gt_name',
    flex: 1.5,
  },
  {
    headerName: 'Electrical Load',
    field: 'el_load',
    flex: 1,
  },
  {
    headerName: 'Ext Temp',
    field: 'ext_temp',
    flex: 1,
  },
  {
    headerName: 'Ambient Temp',
    field: 'amb_temp',
    flex: 1,
  },
  {
    headerName: 'GTG Slip',
    field: 'gtg_slip',
    flex: 1,
  }
];

  filteredGtRows = signal<GtSlipRow[]>([]);
  filteredGtgRows = signal<GtgSlipRow[]>([]);

  /* ------------------------------------------------------------------ */
  /*  Lifecycle                                                            */
  /* ------------------------------------------------------------------ */
  ngOnInit(): void {

    this.activePreset = 'Last 30 Days';

    this.applyPreset('Last 30 Days');

    // Backend does the filtering — debounce so typing doesn't fire a
    // request per keystroke.
    this.filtersChanged
      .pipe(debounceTime(300))
      .subscribe(() => this.loadSlipHistory(this.startDate, this.endDate));
  }

  loadSlipHistory(start?: string, end?: string) {

    this.callService.getSlipHistory(start, end, this.searchText.trim()).subscribe({
    next: (response: SlipHistoryResponse) => {

        this.filteredGtRows.set(response.history_slip ?? []);
        this.filteredGtgRows.set(response.history_slip_gtg ?? []);
      },
    error: (err: HttpErrorResponse) => {
      console.error('Slip History API Error', err);
      this.filteredGtRows.set([]);
      this.filteredGtgRows.set([]);
    }
  });
  }

  clearFilters() {
    this.searchText = '';
    this.loadSlipHistory(this.startDate, this.endDate);
  }

  selectPreset(value: string) {

    this.activePreset = value;

    if (value !== 'Custom') {
      this.applyPreset(value);
      this.showDatePicker = false;
    }

    // computed signals automatically refresh
  }

 applyPreset(value: string) {
  const today = new Date();

  switch (value) {

    case 'Today':
      this.startDate = this.endDate =
        today.toISOString().split('T')[0];
      break;

    case 'Yesterday': {
      const y = new Date();
      y.setDate(today.getDate() - 1);

      this.startDate =
      this.endDate =
      y.toISOString().split('T')[0];
      break;
    }

    case 'Last 7 Days': {
      const d7 = new Date();
      d7.setDate(today.getDate() - 6);

      this.startDate = d7.toISOString().split('T')[0];
      this.endDate = today.toISOString().split('T')[0];
      break;
    }

    case 'Last 30 Days': {
      const d30 = new Date();
      d30.setDate(today.getDate() - 29);

      this.startDate = d30.toISOString().split('T')[0];
      this.endDate = today.toISOString().split('T')[0];
      break;
    }

    case 'This Month': {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);

      this.startDate = firstDay.toISOString().split('T')[0];
      this.endDate = today.toISOString().split('T')[0];
      break;
    }
  }

  this.updateLabel();

  // IMPORTANT
  this.loadSlipHistory(this.startDate, this.endDate);
}

  applyRange() {

    this.updateLabel();

    this.loadSlipHistory(
      this.startDate,
      this.endDate
    );

    this.showDatePicker = false;
  }

 updateLabel() {

    if (!this.startDate || !this.endDate) {
      this.selectedRangeLabel = 'Select Date Range';
      return;
    }

    const start = new Date(this.startDate);
    const end = new Date(this.endDate);

    this.selectedRangeLabel =
      `${start.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      })} - ${end.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      })}`;

  }


}
