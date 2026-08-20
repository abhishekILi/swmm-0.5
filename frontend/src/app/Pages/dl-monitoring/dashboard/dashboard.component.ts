import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DlApiService } from '../dl-api.service';
import { BarChart, BarDatum, KpiCard } from '../../../shared/components';
import { PanelCard } from '../../../shared/components/panel-card/panel-card';

@Component({
  selector: 'app-dl-dashboard',
  standalone: true,
  imports: [KpiCard, PanelCard, BarChart],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(DlApiService);

  // Signal state
  readonly countsSignal = signal({ dl1: 0, dl2: 0, dl3: 0 });

  // Computed signals for KPI card counts
  readonly totalRefit = computed(() => {
    const c = this.countsSignal();
    return c.dl1 + c.dl2 + c.dl3;
  });

  readonly dl1Count = computed(() => this.countsSignal().dl1);
  readonly dl2Count = computed(() => this.countsSignal().dl2);
  readonly dl3Count = computed(() => this.countsSignal().dl3);

  // Computed bar chart breakdown
  readonly breakdownData = computed<BarDatum[]>(() => {
    const c = this.countsSignal();
    return [
      { label: 'DL-1', value: c.dl1, color: '#2674b8' },
      { label: 'DL-2', value: c.dl2, color: '#83bdd8' },
      { label: 'DL-3', value: c.dl3, color: '#d9e8ef' }
    ];
  });

  readonly pendingData: BarDatum[] = [
    { label: 'DL-1', value: 29, color: '#a98216' },
    { label: 'DL-2', value: 30, color: '#e3bd31' },
    { label: 'DL-3', value: 19, color: '#f9e7ac' }
  ];

  ngOnInit(): void {
    this.api.counts().subscribe({
      next: v => {
        if (v) {
          this.countsSignal.set(v);
        }
      },
      error: err => {
        console.error('Failed to fetch DL counts:', err);
      }
    });
  }
}
