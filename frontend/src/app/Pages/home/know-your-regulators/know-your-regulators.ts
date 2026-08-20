import { ChangeDetectionStrategy, Component, OnInit, AfterViewInit, inject, signal, ViewChildren, QueryList, ElementRef } from "@angular/core";
import { CommonModule } from "@angular/common";
import { firstValueFrom } from "rxjs";
import { Call } from "../../../services/network/call";
import { NotificationService } from "../../../Core/services/notification/notification.service";
import { ModalComponent } from "../../../shared/components/modal/modal.component";
import { MasterCard } from "../../refit-maintenance/master-card/master-card";
import {
  DepartmentRegulators,
  RegulatorSailor,
  RegulatorSummary,
} from "./know-your-regulators.model";

@Component({
  selector: "app-know-your-regulators",
  standalone: true,
  imports: [CommonModule, ModalComponent, MasterCard],
  templateUrl: "./know-your-regulators.html",
  styleUrl: "./know-your-regulators.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KnowYourRegulators implements OnInit, AfterViewInit {
  private readonly call = inject(Call);
  private readonly notify = inject(NotificationService);

  readonly loading = signal(true);
  readonly isEditMode = signal(false);
  readonly departments = signal<DepartmentRegulators[]>([]);
  readonly rootExpanded = signal(true);

  @ViewChildren('deptConnector') deptConnectors!: QueryList<ElementRef>;
  @ViewChildren('regConnector') regConnectors!: QueryList<ElementRef>;
  @ViewChildren('deptCard') deptCards!: QueryList<ElementRef>;
  @ViewChildren('regCard') regCards!: QueryList<ElementRef>;

  readonly showSailorModal = signal(false);
  readonly activeRegulator = signal<RegulatorSummary | null>(null);
  readonly assignedSailors = signal<RegulatorSailor[]>([]);
  readonly unassignedSailors = signal<RegulatorSailor[]>([]);
  readonly selectedSailorIds = signal<Set<number>>(new Set());
  readonly modalLoading = signal(false);
  readonly saving = signal(false);

  ngOnInit(): void {
    this.loadTree();
  }

  ngAfterViewInit(): void {
    this.positionConnectors();
  }

  async loadTree(): Promise<void> {
    this.loading.set(true);
    try {
      const res = await firstValueFrom(this.call.getRegulatorsTree());
      const depts = res.departments || [];
      depts.forEach((d) => (d.expanded = true));
      this.departments.set(depts);
    } catch {
      this.notify.error("Failed to load regulators.");
    } finally {
      this.loading.set(false);
    }
  }

  getDepartmentName(department: DepartmentRegulators): string {
    return department.dep_name || department.name || "Department";
  }

  toggleDepartment(department: DepartmentRegulators): void {
    department.expanded = !department.expanded;
    this.departments.set([...this.departments()]);
    setTimeout(() => this.positionConnectors(), 0);
  }

  toggleRootDepartments(): void {
    this.rootExpanded.set(!this.rootExpanded());
    setTimeout(() => this.positionConnectors(), 0);
  }

  private positionConnectors(): void {
    const allDepts = this.deptCards.toArray();
    if (allDepts.length === 0) return;

    const allRegs = this.regCards.toArray();
    allRegs.forEach((regCard) => {
      const regEl = regCard.nativeElement;
      const regParent = regEl.closest('.department-wrapper') as HTMLElement;
      if (!regParent) return;

      const siblingsInGroup = Array.from(regParent.querySelectorAll('[data-regulator-card]'));
      if (siblingsInGroup.length <= 1) return;

      const firstRegInGroup = siblingsInGroup[0] as HTMLElement;
      const lastRegInGroup = siblingsInGroup[siblingsInGroup.length - 1] as HTMLElement;

      const firstRegRect = firstRegInGroup.getBoundingClientRect();
      const lastRegRect = lastRegInGroup.getBoundingClientRect();

      const firstRegCenterX = firstRegRect.left + firstRegRect.width / 2;
      const lastRegCenterX = lastRegRect.left + lastRegRect.width / 2;

      const connector = regParent.querySelector('[data-reg-horizontal-connector]') as HTMLElement;
      if (connector) {
        const connectorParentRect = regParent.getBoundingClientRect();
        const relativeFirstX = firstRegCenterX - connectorParentRect.left;
        const relativeLastX = lastRegCenterX - connectorParentRect.left;

        connector.style.left = relativeFirstX + 'px';
        connector.style.right = (connectorParentRect.width - relativeLastX) + 'px';
      }
    });
  }

  toggleMode(): void {
    this.isEditMode.set(!this.isEditMode());
  }

  async openRegulator(regulator: RegulatorSummary): Promise<void> {
    this.activeRegulator.set(regulator);
    this.showSailorModal.set(true);
    this.modalLoading.set(true);
    this.assignedSailors.set([]);
    this.unassignedSailors.set([]);
    this.selectedSailorIds.set(new Set());

    try {
      const res = await firstValueFrom(this.call.getRegulatorSailors(regulator.id));
      this.assignedSailors.set(res.assigned || []);
      this.unassignedSailors.set(res.unassigned || []);
      this.selectedSailorIds.set(new Set(res.assigned.map((s) => s.id)));
    } catch {
      this.notify.error("Failed to load sailors for this regulator.");
    } finally {
      this.modalLoading.set(false);
    }
  }

  closeSailorModal(): void {
    this.showSailorModal.set(false);
    this.activeRegulator.set(null);
  }

  toggleSailorSelection(sailorId: number): void {
    const set = new Set(this.selectedSailorIds());
    if (set.has(sailorId)) {
      set.delete(sailorId);
    } else {
      set.add(sailorId);
    }
    this.selectedSailorIds.set(set);
  }

  allEligibleSailors(): RegulatorSailor[] {
    return [...this.assignedSailors(), ...this.unassignedSailors()];
  }

  async saveAssignments(): Promise<void> {
    const regulator = this.activeRegulator();
    if (!regulator) return;

    this.saving.set(true);
    try {
      await firstValueFrom(
        this.call.assignRegulatorBulk(regulator.id, Array.from(this.selectedSailorIds())),
      );
      this.notify.success("Assignments saved.");
      this.closeSailorModal();
      await this.loadTree();
    } catch {
      this.notify.error("Failed to save assignments.");
    } finally {
      this.saving.set(false);
    }
  }
}
