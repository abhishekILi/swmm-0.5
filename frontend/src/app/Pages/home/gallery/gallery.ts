import { ChangeDetectionStrategy, Component, OnInit, inject, signal, computed } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { firstValueFrom } from "rxjs";
import { Call } from "../../../services/network/call";
import { NotificationService } from "../../../Core/services/notification/notification.service";
import { ModalComponent } from "../../../shared/components/modal/modal.component";
import { GalleryImage } from "./gallery.model";
import { DepartmentMaster } from "../department-master/department-master.model";
import { IconComponent } from "../../../shared/components";

@Component({
  selector: "app-gallery",
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent, IconComponent],
  templateUrl: "./gallery.html",
  styleUrl: "./gallery.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Gallery implements OnInit {
  private readonly call = inject(Call);
  private readonly notify = inject(NotificationService);

  readonly loading = signal(true);
  readonly isEditMode = signal(false);
  readonly images = signal<GalleryImage[]>([]);
  readonly departments = signal<DepartmentMaster[]>([]);
  readonly selectedDepartment = signal<number | null>(null);

  readonly filteredImages = computed(() => {
    const dept = this.selectedDepartment();
    if (dept === null) return this.images();
    return this.images().filter(img => img.department === dept);
  });

  readonly showViewer = signal(false);
  readonly activeIndex = signal(0);

  readonly showUploadModal = signal(false);
  readonly uploadTitle = signal("");
  readonly uploadCaption = signal("");
  readonly uploadDepartment = signal<number | null>(null);
  readonly uploadFile = signal<File | null>(null);
  readonly uploadPreview = signal<string | null>(null);
  readonly uploadError = signal("");
  readonly saving = signal(false);

  ngOnInit(): void {
    this.loadDepartments();
    this.loadImages();
  }

  async loadDepartments(): Promise<void> {
    try {
      const res = await firstValueFrom(this.call.getDepartments());
      this.departments.set(res || []);
    } catch {
      this.departments.set([]);
    }
  }

  async loadImages(): Promise<void> {
    this.loading.set(true);
    try {
      const res = await firstValueFrom(this.call.getGalleryData());
      this.images.set(res || []);
    } catch {
      this.notify.error("Failed to load gallery images.");
    } finally {
      this.loading.set(false);
    }
  }

  selectDepartment(deptId: number | null): void {
    this.selectedDepartment.set(deptId);
  }

  setUploadDepartment(value: string): void {
    this.uploadDepartment.set(value ? Number(value) : null);
  }

  toggleMode(): void {
    this.isEditMode.set(!this.isEditMode());
  }

  openViewer(index: number): void {
    this.activeIndex.set(index);
    this.showViewer.set(true);
  }

  resetActiveIndex(): void {
    const count = this.filteredImages().length;
    if (count > 0) {
      this.activeIndex.set(0);
    }
  }

  closeViewer(): void {
    this.showViewer.set(false);
  }

  prevImage(): void {
    const count = this.filteredImages().length;
    if (count === 0) return;
    this.activeIndex.set((this.activeIndex() - 1 + count) % count);
  }

  nextImage(): void {
    const count = this.filteredImages().length;
    if (count === 0) return;
    this.activeIndex.set((this.activeIndex() + 1) % count);
  }

  activeImage(): GalleryImage | null {
    return this.filteredImages()[this.activeIndex()] ?? null;
  }

  openUploadModal(): void {
    this.uploadTitle.set("");
    this.uploadCaption.set("");
    this.uploadDepartment.set(null);
    this.uploadFile.set(null);
    this.uploadPreview.set(null);
    this.uploadError.set("");
    this.showUploadModal.set(true);
  }

  closeUploadModal(): void {
    this.showUploadModal.set(false);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.uploadFile.set(file);
    if (file) {
      const reader = new FileReader();
      reader.onload = () => this.uploadPreview.set(reader.result as string);
      reader.readAsDataURL(file);
    }
  }

  async uploadImage(): Promise<void> {
    if (!this.uploadTitle().trim()) {
      this.uploadError.set("Title is required.");
      return;
    }
    if (!this.uploadFile()) {
      this.uploadError.set("Please choose an image.");
      return;
    }

    const formData = new FormData();
    formData.set("title", this.uploadTitle().trim());
    formData.set("caption", this.uploadCaption().trim());
    if (this.uploadDepartment()) {
      formData.set("department", this.uploadDepartment()!.toString());
    }
    formData.append("image", this.uploadFile()!);

    this.saving.set(true);
    try {
      await firstValueFrom(this.call.createGalleryImage(formData));
      this.closeUploadModal();
      await this.loadImages();
      this.resetActiveIndex();
    } catch {
      this.notify.error("Failed to upload image.");
    } finally {
      this.saving.set(false);
    }
  }

  async deleteImage(image: GalleryImage, event: Event): Promise<void> {
    event.stopPropagation();
    if (!confirm(`Delete "${image.title}"?`)) return;

    try {
      await firstValueFrom(this.call.deleteGalleryImage(image.id));
      this.notify.success("Image deleted.");
      await this.loadImages();
      this.resetActiveIndex();
    } catch {
      this.notify.error("Failed to delete image.");
    }
  }
}
