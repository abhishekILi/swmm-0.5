import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject, signal } from '@angular/core';
import { MasterCard } from '../../../../refit-maintenance/master-card/master-card';
import { NotificationService } from '../../../../../Core/services/notification/notification.service';
import { ModalComponent } from '../../../../../shared/components/modal/modal.component';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';
import { Call } from '../../../../../services/network/call';
import { GeneratedDl1ReportInnerRow, GeneratedDl1ReportRow } from './exported-files-dl1.model';

// No dockyard-master endpoint exists yet — kept as a static list, same
// convention used elsewhere in this app (create-ra/create-dliii/etc).
const DOCKYARDS = ['ND (Mbi)', 'ND (V)', 'NSRY (Koc)', 'NSRY (Kar)', 'NSRY (Pbr)'];

// Mirrors Django's ems_generated_reports_list.html — previously generated DL 1 exports,
// each row exportable per-dockyard as an .accdb file.
@Component({
  selector: 'app-exported-files-dl1',
  standalone: true,
  imports: [CommonModule, MasterCard, ModalComponent, IconComponent],
  templateUrl: './exported-files-dl1.html',
})
export class ExportedFilesDl1 implements OnInit {
  private readonly toastr = inject(NotificationService);
  private readonly call = inject(Call);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly dockyards = DOCKYARDS;
  rows: GeneratedDl1ReportRow[] = [];
  selectedRow = signal<GeneratedDl1ReportRow | null>(null);
  selectedRowDetails = signal<GeneratedDl1ReportInnerRow[]>([]);

  ngOnInit(): void {
    this.call.getGeneratedDl1Reports().subscribe({
      next: (res) => {
        this.rows = res.report_rows ?? [];
        this.cdr.detectChanges();
      },
      error: (err: unknown) => console.error('Failed to load generated DL1 reports', err),
    });
  }

  viewDetails(row: GeneratedDl1ReportRow): void {
    this.selectedRow.set(row);
    this.selectedRowDetails.set([]);
    this.call.getGeneratedDl1ReportInnerRows(row.id).subscribe({
      next: (res) => {
        this.selectedRowDetails.set(res.data ?? []);
        this.cdr.detectChanges();
      },
      error: (err: unknown) => console.error('Failed to load report detail rows', err),
    });
  }

  closeDetails(): void {
    this.selectedRow.set(null);
    this.selectedRowDetails.set([]);
  }

  exportToDockyard(row: GeneratedDl1ReportRow, dockyard: string): void {
    this.toastr.info(`Exporting ${row.ra_dl_name} for ${dockyard} (.accdb) — placeholder, no backend wired yet.`);
  }
}
