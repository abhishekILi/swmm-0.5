import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { FormBuilder, ReactiveFormsModule } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { FileInput } from "../../../../../shared/components/file-input/file-input";
import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { HelpGuidance } from "../../../shared/components/help-guidance/help-guidance";
import { NotificationService } from "../../../../../Core/services/notification/notification.service";
import { ObsApiService } from "../../services/obs-api.service";

type MastersTab = "import" | "spare-data-map" | "vendor-pil";

const HELP_HTML = `
  <h6 class="fw-bold mb-1">What this page is for</h6>
  <p class="mb-0">This is where you initialise your Ship Inventory in SWMM. Work through the three
     tabs — the main one is Import Data, where you import all onboard spares from a template Excel
     sheet. Each tab has its own <em>i</em> Help & Guidance — open it inside the tab.</p>
`;

@Component({
  selector: "app-obs-masters-page",
  standalone: true,
  imports: [ReactiveFormsModule, FileInput, SelectInput, HelpGuidance],
  templateUrl: "./masters-page.html",
  styleUrl: "./masters-page.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MastersPage {
  private readonly fb = inject(FormBuilder);
  private readonly notifications = inject(NotificationService);
  private readonly api = inject(ObsApiService);

  readonly helpHtml = HELP_HTML;
  readonly activeTab = signal<MastersTab>("import");
  readonly importBusy = signal(false);
  readonly pilBusy = signal(false);

  readonly importForm = this.fb.nonNullable.group({ importType: "", file: this.fb.control<File | null>(null) });
  readonly mapForm = this.fb.nonNullable.group({ equipmentName: "", equipmentClass: "" });
  readonly pilForm = this.fb.nonNullable.group({ file: this.fb.control<File | null>(null) });

  readonly importTypeOptions = [
    { label: "D787J", value: "D787J" },
    { label: "B & D", value: "B & D" },
    { label: "WED Item", value: "WED_ITEM" },
    { label: "Others", value: "OTHERS" },
  ];

  selectTab(tab: MastersTab): void {
    this.activeTab.set(tab);
  }

  /** `POST import-excel-file/` (`SparesViewSet.import_excel`) — headers in the sheet must match
   * the Spares model's writable field names; `importType` has no server-side effect (the endpoint
   * reads columns from the file only), so it's not sent. */
  async submitImport(): Promise<void> {
    const file = this.importForm.value.file;
    if (!file) {
      this.notifications.error("Select an Excel (*.xlsx) file to import.");
      return;
    }
    this.importBusy.set(true);
    try {
      const result = await firstValueFrom(this.api.importSparesExcel(file));
      this.notifications.success(`Imported ${result.imported} spare(s) successfully.`);
      this.importForm.reset({ importType: "", file: null });
    } catch (error) {
      this.notifications.error(error instanceof Error ? error.message : "Import failed.");
    } finally {
      this.importBusy.set(false);
    }
  }

  submitMap(): void {
    this.notifications.success("Equipment mapping saved.");
  }

  /** `POST api/v1/ilms/vendor-pils/import-excel/` (`VendorPilViewSet.import_excel`) — bulk-creates
   * `VendorPil` rows from the sheet; the endpoint has no per-vendor scoping, so `vendor` is not
   * sent (it isn't a real filter — kept only as a UI hint of which vendor's PIL is being uploaded). */
  async submitPil(): Promise<void> {
    const file = this.pilForm.value.file;
    if (!file) {
      this.notifications.error("Select a PIL Excel (*.xlsx) file to upload.");
      return;
    }
    this.pilBusy.set(true);
    try {
      const result = await firstValueFrom(this.api.importVendorPil(file));
      this.notifications.success(`Uploaded ${result.imported} PIL row(s) successfully.`);
      this.pilForm.reset({ file: null });
    } catch (error) {
      this.notifications.error(error instanceof Error ? error.message : "PIL upload failed.");
    } finally {
      this.pilBusy.set(false);
    }
  }
}
