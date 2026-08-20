import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { MasterCard } from '../../refit-maintenance/master-card/master-card';
import { NotificationService } from '../../../Core/services/notification/notification.service';
import { Call } from '../../../services/network/call';
import { OpenDefect, OpenDefectsResponse } from '../open-defects/open-defects.model';
import { OpenDefectRow } from '../ra-signal/ra-signal.model';

// No yard/dockyard master-data endpoint exists anywhere in this backend yet
// (checked call.ts) — kept as a static list, same as create-ra/create-dliii/ra-signal.
const YARD_NAMES = ['ND (Mbi)', 'ND (V)', 'NSRY (Koc)', 'NSRY (Kar)', 'NSRY (Pbr)'];
const EXPORT_FORMATS = ['ACCDB', 'XLSX', 'CSV'];

// Mirrors Django's dart/ra_defect_list.html — the RA-initiated defect working queue.
@Component({
  selector: 'app-ra-defect-list',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard],
  templateUrl: './ra-defect-list.html',
  styleUrl: './ra-defect-list.css',
})
export class RaDefectList implements OnInit {
  private readonly toastr = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly call = inject(Call);

  readonly yardNames = YARD_NAMES;
  readonly exportFormats = EXPORT_FORMATS;

  yardName = '';
  exportFormat = EXPORT_FORMATS[0];
  loading = true;

  rows: OpenDefectRow[] = [];
  selectedIds = new Set<number>();

  async ngOnInit(): Promise<void> {
    try {
      const res: OpenDefectsResponse = await firstValueFrom(this.call.getOpenDartsAndABER());
      this.rows = (res.open_defects ?? []).map((d: OpenDefect) => ({
        id: d.id,
        dart_number: d.dart_number ?? '',
        defect_date: d.dart_date ?? '',
        equipment_name: d.eq_name ?? '',
        equipment_nomenclature: d.nomenclature ?? '',
        description: d.defective_discriptions ?? '',
        status: d.status === 'Closed' ? ('Closed' as const) : ('Open' as const),
        remarks: d.remarks ?? '',
        ss_remark: '' as const,
      }));
    } catch (err) {
      console.error('Failed to load open defects', err);
    } finally {
      this.loading = false;
    }
  }

  toggleSelect(id: number): void {
    if (this.selectedIds.has(id)) {
      this.selectedIds.delete(id);
    } else {
      this.selectedIds.add(id);
    }
  }

  isSelected(id: number): boolean {
    return this.selectedIds.has(id);
  }

  createRaDl(): void {
    if (!this.selectedIds.size) {
      this.toastr.warning('Select at least one defect to create RA / DL.');
      return;
    }
    const selected = this.rows
      .filter((r) => this.selectedIds.has(r.id))
      .map((r) => ({ id: r.id }));
    this.router.navigateByUrl('/afterAuth/op-maintenance/create-ra', {
      state: { selectedDefects: selected },
    });
  }

  sendToNavYojana(): void {
    this.toastr.info('Export to NavYojana/SDRS is not wired up yet — this is a placeholder action.');
  }
}
