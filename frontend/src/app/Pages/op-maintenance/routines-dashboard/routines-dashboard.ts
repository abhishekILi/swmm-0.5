import { CommonModule } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { MasterCard } from "../../refit-maintenance/master-card/master-card";
import { FormBuilder, FormGroup, ReactiveFormsModule } from "@angular/forms";
import { SelectInput } from "../../../shared/components/select-input/select-input";
import { Call } from "../../../services/network/call";
import { DataGrid } from "../../../shared/components/data-grid/data-grid";
import { UniqueMaintopResponse, UniqueMaintopRoutine } from "./main-top.model";
import { MaintopActionRenderer } from "../../../shared/components/maintop-action-renderer";
import { NotificationService } from '../../../Core/services/notification/notification.service';
import { Subject, debounceTime } from "rxjs";
import { IconComponent } from '../../../shared/components/icon/icon.component';

@Component({
  selector: "app-routines-dashboard",
  standalone: true,
  imports: [CommonModule, MasterCard, ReactiveFormsModule, SelectInput, DataGrid, IconComponent],
  templateUrl: "./routines-dashboard.html",
  styleUrl: "./routines-dashboard.css",
})
export class RoutinesDashboard implements OnInit {
  unique_main_top!: FormGroup;
  private fb = inject(FormBuilder);
  private api = inject(Call);
  private toastr = inject(NotificationService);
  filteredMaintopRoutines = signal<UniqueMaintopRoutine[]>([])
  searchText = "";
  subDepartmentOptions: { label: string; value: string | number }[] = [];
  equipmentNameOptions: { label: string; value: string | number }[] = [];
  routineCategoryOptions: { label: string; value: string | number }[] = [];
  routineNameOptions: { label: string; value: string | number }[] = [];

  private readonly filtersChanged = new Subject<void>();

  ngOnInit(): void {
    this.initializeForm();
    this.getUniqueMaintopRoutines();

    // Backend does the filtering — debounce so typing/dropdown changes don't
    // fire a request per keystroke/click.
    this.filtersChanged.pipe(debounceTime(300)).subscribe(() => {
      this.getUniqueMaintopRoutines();
    });
  }

  initializeForm(): void {
    this.unique_main_top = this.fb.group({
      subDepartment: [""],
      equipmentName: [""],
      routineCategory: [""],
      routineName: [""],
    });
    this.unique_main_top.valueChanges.subscribe(() => {
      this.filtersChanged.next();
    });
  }

  onSearch(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.searchText = target.value;
    this.filtersChanged.next();
  }

  getUniqueMaintopRoutines(): void {
    const { equipmentName } = this.unique_main_top.getRawValue();

    this.api
      .getUniqueMaintopRoutinesData(equipmentName || undefined, this.searchText.trim() || undefined)
      .subscribe({
        next: (response: UniqueMaintopResponse) => {
          this.filteredMaintopRoutines.set(response.result ?? [])

          this.subDepartmentOptions =
            response.filter_options?.sub_departments?.map((item) => ({
              label: item.name,
              value: item.id,
            })) ?? [];

          this.equipmentNameOptions =
            response.filter_options?.equipment_names?.map((item) => ({
              label: item,
              value: item,
            })) ?? [];

          this.routineCategoryOptions =
            response.filter_options?.routine_categories?.map((item) => ({
              label: item,
              value: item,
            })) ?? [];

          this.routineNameOptions =
            response.filter_options?.routine_names?.map((item) => ({
              label: item,
              value: item,
            })) ?? [];
        },

        error: (error) => {
          console.error(error);

          this.toastr.error(
            error?.error?.message || "Failed to load Unique Maintop Routines",
          );
        },
      });
  }

  clearFilters(): void {
    this.unique_main_top.reset();
    this.searchText = "";
    this.getUniqueMaintopRoutines();
  }
  defectColumnDefs = [
    { headerName: "INSMA Equipment Name", field: "equipment_name" },
    { headerName: "INSMA Equipment Code", field: "equipment_code" },
    { headerName: "No. of Equipment Nomenclature", field: "eq_count" },
    { headerName: "MAINTOP No.", field: "maintop_no" },
    { headerName: "Total Sub Routines", field: "sub_routine_count" },
    { headerName: "Total Routines", field: "routine_count" },
    { headerName: "No. of DYD Routines", field: "dyd_routine_count" },

    {
      headerName: "Actions",
      field: "pk",
      cellRenderer: MaintopActionRenderer,
      cellRendererParams: {
        onView: (data: UniqueMaintopRoutine) => {
          this.openMaintopDetails(data);
        },
      },
      width: 100,
    },
  ];
  openMaintopDetails(data: UniqueMaintopRoutine): void {
    console.log("Selected Record", data);
    // future popup/navigation
  }
}
