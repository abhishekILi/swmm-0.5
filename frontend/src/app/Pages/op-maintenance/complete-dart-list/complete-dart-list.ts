import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { MasterCard } from '../../refit-maintenance/master-card/master-card';
import { Call } from '../../../services/network/call';
import { CompleteDartListItem } from './complete-dart-list.model';

interface CompleteDartRow {
  id: number;
  ser: number;
  dart_number: string;
  equipment_name: string;
  defective_discriptions: string;
  closed_date: string;
}

// Mirrors Django's dart/complete_dart_list.html — completed defects, used as a
// jump-off list to re-open the completion form for a given DART.
@Component({
  selector: 'app-complete-dart-list',
  standalone: true,
  imports: [CommonModule, MasterCard],
  templateUrl: './complete-dart-list.html',
})
export class CompleteDartList implements OnInit {
  private readonly router = inject(Router);
  private readonly call = inject(Call);

  rows: CompleteDartRow[] = [];
  loading = true;

  async ngOnInit(): Promise<void> {
    try {
      const items: CompleteDartListItem[] = await firstValueFrom(this.call.getCompleteDartList());
      this.rows = (items ?? []).map((item, i) => ({
        id: item.id,
        ser: i + 1,
        dart_number: item.dart_number ?? '',
        equipment_name: item.equipment_ship_name || item.equipment_ems_name || '',
        defective_discriptions: item.defective_discriptions ?? '',
        closed_date: item.complete_defect_dart_set?.[0]?.rectified_date ?? '',
      }));
    } catch (err) {
      console.error('Failed to load complete DART list', err);
    } finally {
      this.loading = false;
    }
  }

  reopen(row: CompleteDartRow): void {
    this.router.navigate(['/afterAuth/op-maintenance/close-defects', row.id]);
  }
}
