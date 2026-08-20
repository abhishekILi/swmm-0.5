import { Component, ChangeDetectionStrategy, OnInit, signal, computed, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { ColDef } from "ag-grid-community";

import { InputField } from "../../../shared/components/input-field/input-field";
import { SelectInput, DropdownOption } from "../../../shared/components/select-input/select-input";
import { FileInput } from "../../../shared/components/file-input/file-input";
import { ModalComponent } from "../../../shared/components/modal/modal.component";
import { DataGrid } from "../../../shared/components/data-grid/data-grid";
import { ActionRendererComponent } from "../../../shared/components/data-grid/grid-action-icons";
import { ExportToolbar, ExportKind } from "../../../shared/components/export-toolbar/export-toolbar";
import { IconComponent } from "../../../shared/components/icon/icon.component";
import { PageHeaderBar } from "../../../shared/components/page-header-bar/page-header-bar";
import { NotificationService } from "../../../Core/services/notification/notification.service";
import { EquipmentDocument } from "../models/kms.model";
import { getFileIcon } from "../shared/kms-file-icon.util";
import { KmsStateService } from "../state/kms-state.service";
import { toFormData } from "../state/kms-mapper.util";

const DOCUMENT_TYPE_OPTIONS: DropdownOption[] = [
  { label: "TDOI", value: "TDOI" },
  { label: "TD", value: "TD" },
  { label: "OI", value: "OI" },
  { label: "Other", value: "Other" },
];

@Component({
  selector: "app-kms-technical",
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, InputField, SelectInput, FileInput, ModalComponent, DataGrid, ExportToolbar, IconComponent, PageHeaderBar],
  templateUrl: "./kms-technical.html",
  styleUrl: "./kms-technical.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KmsTechnical implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly notify = inject(NotificationService);
  private readonly store = inject(KmsStateService);

  readonly equipmentCategories = this.store.equipmentCategories;
  readonly documents = this.store.documents;
  readonly equipmentSearch = signal("");
  readonly documentSearch = signal("");
  readonly exportBusy = signal<ExportKind | null>(null);

  ngOnInit(): void {
    void this.store.loadTechnical();
  }

  readonly filteredEquipment = computed(() => {
    const search = this.equipmentSearch().toLowerCase();
    return this.equipmentCategories().filter((eq) => eq.equipmentName.toLowerCase().includes(search));
  });

  readonly filteredDocuments = computed(() => {
    const search = this.documentSearch().toLowerCase();
    if (!search) return this.documents();
    return this.documents().filter((doc) =>
      [doc.documentName, doc.documentType, doc.uploadedDate, doc.equipmentName].some((field) => field.toLowerCase().includes(search)),
    );
  });

  readonly documentTypeOptions = DOCUMENT_TYPE_OPTIONS;
  readonly equipmentOptions = computed<DropdownOption[]>(() =>
    this.equipmentCategories().map((eq) => ({ label: eq.equipmentName, value: eq.id })),
  );

  readonly showAddEquipmentModal = signal(false);
  readonly showAddDocumentModal = signal(false);
  readonly showDetailModal = signal(false);
  readonly activeDocument = signal<EquipmentDocument | null>(null);

  readonly manualEquipmentName = signal("");

  readonly documentForm = this.formBuilder.group({
    equipmentId: [null as number | null, Validators.required],
    documentType: ["", Validators.required],
    customDocType: [""],
    documentName: ["", Validators.required],
    attachment: [null as File | null],
  });

  readonly showCustomDocType = computed(() => this.documentForm.get("documentType")?.value === "Other");

  readonly columnDefs: ColDef[] = [
    { field: "documentName", headerName: "Document Name", flex: 1.4 },
    { field: "documentType", headerName: "Document Type", width: 150 },
    { field: "uploadedDate", headerName: "Uploaded Date", width: 150 },
    { field: "equipmentName", headerName: "Equipment Name", flex: 1 },
    {
      headerName: "Actions",
      width: 110,
      sortable: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: EquipmentDocument) => [
          { icon: "view", label: "View", action: () => this.viewDocument(row) },
          { icon: "delete", label: "Delete", action: () => this.deleteDocument(row) },
        ],
      },
    },
  ];

  getFileIcon = getFileIcon;

  /** No export endpoint exists yet — the delay + busy state just simulate one so the button isn't dead. */
  onExport(kind: ExportKind): void {
    this.exportBusy.set(kind);
    setTimeout(() => {
      this.exportBusy.set(null);
      this.notify.info(`${kind.toUpperCase()} export will be available once the backend integration is wired up.`);
    }, 400);
  }

  openAddEquipmentModal(): void {
    this.manualEquipmentName.set("");
    this.showAddEquipmentModal.set(true);
  }

  closeAddEquipmentModal(): void {
    this.showAddEquipmentModal.set(false);
  }

  async saveEquipmentCategory(): Promise<void> {
    const name = this.manualEquipmentName().trim();
    if (!name) {
      this.notify.error("Enter an equipment name");
      return;
    }
    if (this.equipmentCategories().some((eq) => eq.equipmentName.toLowerCase() === name.toLowerCase())) {
      this.notify.error("Equipment category already exists");
      return;
    }
    if (await this.store.addEquipmentCategory(name)) {
      this.closeAddEquipmentModal();
    }
  }

  openAddDocumentModal(equipmentId?: number): void {
    this.documentForm.reset({ equipmentId: equipmentId ?? null, documentType: "", customDocType: "", documentName: "", attachment: null });
    this.showAddDocumentModal.set(true);
  }

  closeAddDocumentModal(): void {
    this.showAddDocumentModal.set(false);
  }

  async saveDocument(): Promise<void> {
    if (this.documentForm.invalid) {
      this.documentForm.markAllAsTouched();
      this.notify.error("Fill all required fields");
      return;
    }
    const value = this.documentForm.getRawValue();
    const equipment = this.equipmentCategories().find((eq) => eq.id === value.equipmentId);
    if (!equipment) return;

    const docType = value.documentType === "Other" && value.customDocType ? value.customDocType : value.documentType;
    const formData = toFormData({ equipment: equipment.id, document_name: value.documentName, document_type: docType }, value.attachment);
    if (await this.store.addEquipmentDocument(formData)) {
      this.closeAddDocumentModal();
    }
  }

  viewDocument(doc: EquipmentDocument): void {
    this.activeDocument.set(doc);
    this.showDetailModal.set(true);
  }

  closeDetailModal(): void {
    this.showDetailModal.set(false);
  }

  async deleteDocument(doc: EquipmentDocument): Promise<void> {
    await this.store.deleteEquipmentDocument(doc.id);
  }
}
