import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { MasterCard } from '../../refit-maintenance/master-card/master-card';
import { NotificationService } from '../../../Core/services/notification/notification.service';
import { Call } from '../../../services/network/call';
import { SS_REMARK_OPTIONS, SsRemark, RA_YARD_OPTIONS, DL_EXPORT_FORMATS } from '../ra-signal/ra-signal.model';
import { OpenDefect } from '../open-defects/open-defects.model';

interface OpraRow {
  ser: number;
  id: number;
  selected: boolean;
  opra_no: string;
  dart_no: string;
  defect_date: string;
  dart_closing_date: string;
  status: 'Open' | 'Closed';
  equipment: string;
  description: string;
  remarks: string;
  ss_remark: SsRemark | '';
}

@Component({
  selector: 'app-create-ra',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard],
  templateUrl: './create-ra.html',
  styleUrl: './create-ra.css',
})
export class CreateRA implements OnInit {
  private readonly toastr = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly call = inject(Call);

  readonly yardOptions: string[] = RA_YARD_OPTIONS;
  readonly exportFormats = DL_EXPORT_FORMATS;
  readonly ssRemarkOptions = SS_REMARK_OPTIONS;

  yardName = '';
  dtgDate = '';
  dtgHours = '';
  dtgMinutes = '';
  exportFormat = '';
  submitted = false;
  exporting = false;

  rows: OpraRow[] = [];

  get selectedCount(): number {
    return this.rows.filter((r) => r.selected).length;
  }

  get allSelected(): boolean {
    return this.rows.length > 0 && this.rows.every((r) => r.selected);
  }

  get yardMissing(): boolean {
    return this.submitted && !this.yardName;
  }

  get exportFormatMissing(): boolean {
    return this.submitted && !this.exportFormat;
  }

  ngOnInit(): void {
    // Only the defects the user explicitly checked on Open Defects come here —
    // this page never re-fetches the full pending-defects list.
    const selectedDefects = (history.state?.selectedDefects as OpenDefect[]) ?? [];

    if (!selectedDefects.length) {
      this.toastr.warning('No defects were selected — select at least one on Open Defects first.');
    }

    this.rows = selectedDefects.map((d, i) => ({
      ser: i + 1,
      id: d.id,
      selected: true,
      opra_no: d.opra_no ?? '',
      dart_no: d.dart_number ?? '',
      defect_date: d.dart_date ?? '',
      dart_closing_date: d.rectification_date ?? '',
      status: d.status === 'Closed' ? 'Closed' : 'Open',
      equipment: d.eq_name ?? '',
      description: d.defective_discriptions ?? '',
      remarks: d.remarks ?? '',
      ss_remark: '' as const,
    }));
  }

  toggleAll(checked: boolean): void {
    this.rows = this.rows.map((r) => ({ ...r, selected: checked }));
  }

  removeRow(ser: number): void {
    this.rows = this.rows.filter((r) => r.ser !== ser);
  }

  /** Converts an `<input type="date">` value (YYYY-MM-DD) to the DD-MM-YYYY
   * format the export API expects. */
  private formatDtgDate(value: string): string {
    const [year, month, day] = value.split('-');
    return year && month && day ? `${day}-${month}-${year}` : value;
  }

  async exportToNavYojana(): Promise<void> {
    this.submitted = true;

    const selected = this.rows.filter((r) => r.selected);
    if (!this.dtgDate) {
      this.toastr.warning('DTG is required.');
      return;
    }
    if (!selected.length) {
      this.toastr.warning('Select at least one defect to export.');
      return;
    }
    if (!this.yardName) {
      this.toastr.warning('Select a yard first.');
      return;
    }
    if (!this.exportFormat) {
      this.toastr.warning('Select an export format first.');
      return;
    }

    const remarksData: Record<number, string> = {};
    const ssRemarksData: Record<number, string> = {};
    selected.forEach((r) => {
      if (r.remarks) remarksData[r.id] = r.remarks;
      if (r.ss_remark) ssRemarksData[r.id] = r.ss_remark;
    });

    this.exporting = true;
    try {
      const res = await firstValueFrom(
        this.call.exportRA({
          yard: this.yardName,
          dtg_date: this.formatDtgDate(this.dtgDate),
          dtg_hour: this.dtgHours,
          dtg_minute: this.dtgMinutes,
          export_format: this.exportFormat,
          dart_ids: selected.map((r) => r.id),
          remarks_data: remarksData,
          ss_remarks_data: ssRemarksData,
          dl_type: 'RA',
        }),
      );

      const downloadUrl = res.data?.download_url;
      if (downloadUrl) {
        try {
          window.open(new URL(downloadUrl, this.call.baseUrl).toString(), '_blank');
        } catch (err) {
          console.error('Invalid download URL returned by export API', err);
        }
      }
    } catch (err) {
      const error = err as { error?: { message?: string } };
      this.toastr.error(error?.error?.message ?? 'Failed to export RA.');
    } finally {
      this.exporting = false;
    }
  }

  cancel(): void {
    this.router.navigate(['/afterAuth/op-maintenance/open-darts']);
  }
}
