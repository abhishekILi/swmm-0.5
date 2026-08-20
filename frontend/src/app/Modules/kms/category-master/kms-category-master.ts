import { Component, ChangeDetectionStrategy, OnInit, signal, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { ColDef } from "ag-grid-community";

import { InputField } from "../../../shared/components/input-field/input-field";
import { ModalComponent } from "../../../shared/components/modal/modal.component";
import { IconComponent } from "../../../shared/components/icon/icon.component";
import { PageHeaderBar } from "../../../shared/components/page-header-bar/page-header-bar";
import { DataGrid } from "../../../shared/components/data-grid/data-grid";
import { ActionRendererComponent, GridAction } from "../../../shared/components/data-grid/grid-action-icons";
import { GridStatusChipRenderer } from "../../../shared/components/data-grid/grid-status-chip-renderer";
import { NotificationService } from "../../../Core/services/notification/notification.service";
import { CertificateCategory } from "../models/kms.model";
import { KmsStateService } from "../state/kms-state.service";

@Component({
  selector: "app-kms-category-master",
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, InputField, ModalComponent, IconComponent, PageHeaderBar, DataGrid],
  templateUrl: "./kms-category-master.html",
  styleUrl: "./kms-category-master.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KmsCategoryMaster implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly notify = inject(NotificationService);
  private readonly store = inject(KmsStateService);

  readonly categories = this.store.categories;

  ngOnInit(): void {
    void this.store.loadCategories();
  }

  readonly columnDefs: ColDef[] = [
    { field: "categoryName", headerName: "Category Name", flex: 1.5 },
    {
      headerName: "Type",
      width: 130,
      sortable: false,
      valueGetter: (params) => (params.data && (params.data as CertificateCategory).isSystem ? "System" : "Custom"),
      cellRenderer: GridStatusChipRenderer,
      cellRendererParams: { toneMap: { System: "neutral", Custom: "info" } },
    },
    {
      headerName: "Actions",
      width: 110,
      sortable: false,
      cellRenderer: ActionRendererComponent,
      cellRendererParams: {
        actions: (row: CertificateCategory): GridAction[] =>
          row.isSystem
            ? []
            : [
                { icon: "edit", label: "Edit", action: () => this.openEditModal(row) },
                { icon: "delete", label: "Delete", action: () => this.remove(row) },
              ],
      },
    },
  ];

  readonly showModal = signal(false);
  readonly editingId = signal<number | null>(null);

  readonly form = this.formBuilder.group({
    categoryName: ["", Validators.required],
  });

  get modalTitle(): string {
    return this.editingId() !== null ? "Edit Category" : "Add Category";
  }

  openAddModal(): void {
    this.editingId.set(null);
    this.form.reset({ categoryName: "" });
    this.showModal.set(true);
  }

  openEditModal(category: CertificateCategory): void {
    if (category.isSystem) {
      this.notify.error("System categories cannot be edited.");
      return;
    }
    this.editingId.set(category.id);
    this.form.reset({ categoryName: category.categoryName });
    this.showModal.set(true);
  }

  closeModal(): void {
    this.showModal.set(false);
  }

  async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.notify.error("Category name is required");
      return;
    }
    const name = this.form.getRawValue().categoryName ?? "";
    const editId = this.editingId();

    const ok = editId !== null ? await this.store.updateCategory(editId, name) : await this.store.createCategory(name);
    if (ok) {
      this.closeModal();
    }
  }

  async remove(category: CertificateCategory): Promise<void> {
    if (category.isSystem) {
      this.notify.error("Default categories cannot be deleted.");
      return;
    }
    await this.store.deleteCategory(category.id);
  }
}
