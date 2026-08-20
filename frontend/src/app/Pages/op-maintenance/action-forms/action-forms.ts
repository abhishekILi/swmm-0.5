import { Component, signal, ViewChild } from "@angular/core";
import { DefactForm } from "./defact-form/defact-form";
import { AaAberForm } from "./aa-aber-form/aa-aber-form";
import { SpareSelectionModal } from "../../../shared/components/spare-selection-modal/spare-selection-modal"; // path adjust karo
import { GuaranteeDefectForm } from "./guarantee-defect-form/guarantee-defect-form";
import { FormModal } from "../../../shared/components/form-modal/form-modal";
import { ImagePreview } from "../../../shared/components/image-preview/image-preview";
import { SpareItem, ConfirmModalData } from "./action-forms.model";

type SpareSource = 'defect' | 'aber' | 'guarantee';

@Component({
  selector: "app-action-forms",
  imports: [DefactForm, AaAberForm, SpareSelectionModal, GuaranteeDefectForm, FormModal, ImagePreview],
  templateUrl: "./action-forms.html",
  styleUrl: "./action-forms.css",
})
export class ActionForms {
  activeTab: "defect" | "guarantee-defect" | "A&A/ABES" = "defect";
  currentFormType: 'defect' | 'guarantee' | 'aber' | null = null;
  currentSpareSource = signal<SpareSource>('defect');
  showSpareModal = signal(false);
  selectedSpares = signal<SpareItem[]>([]);
  showFormConfirmModal = signal(false);
  @ViewChild(AaAberForm)
  aberForm!: AaAberForm;
  @ViewChild(DefactForm)
  defectForm!: DefactForm;
  @ViewChild(GuaranteeDefectForm)
  guaranteeForm!: GuaranteeDefectForm;

  showPreview = signal(false);
  previewImages = signal<string[]>([]);
  openFormConfirmModal(type: 'defect' | 'guarantee' | 'aber') {
    this.currentFormType = type;
    this.showFormConfirmModal.set(true);
  }

  openPreview(images: string[]) {
    this.previewImages.set(images);
    this.showPreview.set(true);
  }

  closePreview() {
    this.showPreview.set(false);
    this.previewImages.set([]);
  }

  // on tab chagne
  changeTab(tab: "defect" | "guarantee-defect" | "A&A/ABES") {
    if (this.activeTab !== tab) {
      this.selectedSpares.set([]);
      this.showSpareModal.set(false);
    }

    this.activeTab = tab;
  }

  async onModalSave(data: ConfirmModalData) {

    this.closeFormConfirmModal();

    if (this.currentFormType === 'defect') {
      await this.defectForm.submit(data);
    }

    if (this.currentFormType === 'guarantee') {
      await this.guaranteeForm.submit(data);
    }

    if (this.currentFormType === 'aber') {
      await this.aberForm.submit(data);
    }
  }


  closeFormConfirmModal() {
    this.showFormConfirmModal.set(false);
  }
  openSpareModal(source: SpareSource) {
    this.currentSpareSource.set(source);
    this.showSpareModal.set(true);
  }

  closeSpareModal() {
    this.showSpareModal.set(false);
  }



  onSparesSelected(rows: SpareItem[]) {
    this.selectedSpares.update((existing) => {
      const merged = [...existing];

      rows.forEach((newRow) => {
        const exists = merged.some((x) => x.pk === newRow.pk);

        if (!exists) {
          merged.push(newRow);
        }
      });

      return merged;
    });

    this.showSpareModal.set(false);
  }

  removeSpare(pk: string) {
    this.selectedSpares.update((rows) =>
      rows.filter((x: SpareItem) => String(x.pk ?? '') !== pk),
    );
  }
}
