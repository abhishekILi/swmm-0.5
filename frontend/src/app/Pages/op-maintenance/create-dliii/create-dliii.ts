import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { MasterCard } from '../../refit-maintenance/master-card/master-card';
import { NotificationService } from '../../../Core/services/notification/notification.service';
import { Call } from '../../../services/network/call';
import { YARD_OPTIONS, DL_EXPORT_FORMATS, YardOption } from '../ra-signal/ra-signal.model';
import { CreateDLDraftItem, CreateDLRefitItem, ShipRemarkOption } from './create-dliii.model';

interface DraftDlRow {
  ser: number;
  /** The InitiateRADL draft row's own id — used for save_dl_rows/delete_dl_row. */
  draftId: number;
  /** The originating defect's id — used as `dart_id` in the export payload. */
  defectId: number;
  dl_no: string;
  dart_no: string;
  date: string;
  status: string;
  equipment: string;
  description: string;
  remarks: string;
  ss_remark: string;
}

@Component({
  selector: 'app-create-dliii',
  standalone: true,
  imports: [CommonModule, FormsModule, MasterCard],
  templateUrl: './create-dliii.html',
  styleUrl: './create-dliii.css',
})
export class CreateDLIII implements OnInit {
  private readonly toastr = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly call = inject(Call);

  readonly yardOptions: YardOption[] = YARD_OPTIONS;
  readonly exportFormats = DL_EXPORT_FORMATS;
  refitTypes: CreateDLRefitItem[] = [];
  shipRemarkOptions: ShipRemarkOption[] = [];

  refitType = '';
  yardName = '';
  exportFormat = '';
  manualDlNo = '';
  /** Gates only the Export button — matches the source app exactly (Refit
   * Type/Yard/Export Format stay visible from the start). */
  dlNoSet = false;
  saving = false;
  exporting = false;

  rows: DraftDlRow[] = [];

  async ngOnInit(): Promise<void> {
    // Defects are already drafted via /createdlfun/ before we get here (see
    // OpenDefects.goToCreateDLII) — this page only ever shows that draft set,
    // there's no separate "all pending defects" list or selection UI, matching
    // the source app's create_dl.html.
    const draftData = (history.state?.draftData as CreateDLDraftItem[]) ?? [];

    if (draftData.length) {
      this.refitTypes = (history.state?.refitList as CreateDLRefitItem[]) ?? [];
      this.shipRemarkOptions = (history.state?.shipRemarksList as ShipRemarkOption[]) ?? [];
      this.applyDraftData(draftData);
      return;
    }

    // Router navigation state doesn't survive a page reload — refetch the
    // current draft list instead of showing an empty table. createdlfun/
    // always returns every existing DRAFT DL-II row regardless of the ids
    // passed in, so an empty-id call here just re-reads current state
    // (including any remarks already saved via save_dl_rows/).
    try {
      const res = await firstValueFrom(this.call.createDL([]));
      this.refitTypes = res.data?.refit_list ?? [];
      this.shipRemarkOptions = res.data?.ship_remarks_list ?? [];
      this.applyDraftData(res.data?.draft_data ?? []);
    } catch (err) {
      const error = err as { error?: { message?: string } };
      this.toastr.error(error?.error?.message ?? 'Failed to load DL-II drafts.');
    }
  }

  private applyDraftData(draftData: CreateDLDraftItem[]): void {
    if (!draftData.length) {
      this.toastr.warning('No drafted DL-II rows found — select defects on Open Defects and click Create DL-II first.');
    }

    this.rows = draftData.map((d, i) => ({
      ser: i + 1,
      draftId: d.id,
      defectId: d.dart_id,
      dl_no: d.dl_no ?? '',
      dart_no: d.dart_number ?? '',
      date: d.dart_date ?? '',
      status: 'DRAFT DL-II',
      equipment: d.equipment ?? '',
      description: d.defective_discriptions ?? '',
      remarks: d.additional_remarks ?? '',
      ss_remark: d.remarks ?? '',
    }));
  }

  /** One starting number, auto-incremented sequentially across every row —
   * matches the source app's #setDLBtn behavior exactly. Reveals Export. */
  setDlNo(): void {
    const start = parseInt(this.manualDlNo, 10);
    if (!start || start <= 0) {
      this.toastr.warning('Enter a valid DL No.');
      return;
    }
    this.rows = this.rows.map((r, i) => ({ ...r, dl_no: String(start + i) }));
    this.dlNoSet = true;
  }

  async removeRow(ser: number): Promise<void> {
    const row = this.rows.find((r) => r.ser === ser);
    if (!row) return;

    try {
      await firstValueFrom(this.call.deleteDLRow(row.draftId));
      this.rows = this.rows.filter((r) => r.ser !== ser);
      this.toastr.success('DL row deleted.');
    } catch (err) {
      const error = err as { error?: { message?: string } };
      this.toastr.error(error?.error?.message ?? 'Failed to delete DL row.');
    }
  }

  /** Bulk-saves every row's Additional Remarks / SS Remarks in one call —
   * matches the source app's #saveDLBtn, which saves the whole table at once. */
  async save(): Promise<void> {
    if (!this.rows.length) {
      this.toastr.warning('No rows to save.');
      return;
    }

    this.saving = true;
    try {
      await firstValueFrom(
        this.call.saveDLRows(this.rows.map((r) => ({ dart_id: r.draftId, additional_remarks: r.remarks, remarks: r.ss_remark }))),
      );
      this.toastr.success('Saved successfully.');
    } catch (err) {
      const error = err as { error?: { message?: string } };
      this.toastr.error(error?.error?.message ?? 'Save failed.');
    } finally {
      this.saving = false;
    }
  }

  async exportToNavyojana(): Promise<void> {
    if (!this.yardName) {
      this.toastr.warning('Select a yard first.');
      return;
    }
    const yardOption = this.yardOptions.find((y) => y.code === this.yardName);
    if (!yardOption) {
      this.toastr.error('Unknown yard selected.');
      return;
    }
    if (!this.exportFormat) {
      this.toastr.warning('Select an export format first.');
      return;
    }
    if (!this.rows.length) {
      this.toastr.warning('No rows to export.');
      return;
    }

    const rowData = this.rows.map((r) => ({
      dart_id: r.defectId,
      dl_id: r.draftId,
      dl_number: r.dl_no,
      additional_remark: r.remarks,
      ss_remark: r.ss_remark,
    }));

    this.exporting = true;
    try {
      const res = await firstValueFrom(
        this.call.exportDLII(yardOption.exportPath, {
          yard: yardOption.code,
          export_format: this.exportFormat,
          refit_Type: this.refitType ? Number(this.refitType) : undefined,
          row_data: rowData,
        }),
      );

      this.toastr.success(res.message ?? 'DL-II exported successfully.');

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
      this.toastr.error(error?.error?.message ?? 'Failed to export DL-II.');
    } finally {
      this.exporting = false;
    }
  }

  cancel(): void {
    this.router.navigate(['/afterAuth/op-maintenance/open-darts']);
  }
}
