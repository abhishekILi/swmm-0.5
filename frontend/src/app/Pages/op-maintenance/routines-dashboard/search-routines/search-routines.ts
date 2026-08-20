import { CommonModule } from "@angular/common";
import { Component, OnInit, inject, signal } from "@angular/core";
import { FormBuilder, FormGroup, ReactiveFormsModule } from "@angular/forms";
import { debounceTime, distinctUntilChanged } from "rxjs";

import { NotificationService } from '../../../../Core/services/notification/notification.service';

import { MasterCard } from "../../../refit-maintenance/master-card/master-card";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { SelectInput } from "../../../../shared/components/select-input/select-input";

import { Call } from "../../../../services/network/call";
import {
  EmsSearchResultItem,
  HeaderStats,
  RoutineItem,
  SelectOption,
} from "./search-routines.model";
import { ColDef, ICellRendererParams } from "ag-grid-community";
import { ICellRendererAngularComp } from "ag-grid-angular";
import { Router } from "@angular/router";
import { FussStatusRendererComponent } from "../../action-forms/fuss-status-renderer";
import { IconComponent } from '../../../../shared/components/icon/icon.component';

@Component({
  selector: "app-search-routine-action-renderer",
  standalone: true,
  imports: [IconComponent],
  template: `
    <button
      type="button"
      class="hover:opacity-80 transition-opacity flex items-center justify-center w-full h-full"
      title="Due Routines"
      (click)="onClick($event)"
    >
      <app-icon
        name="file-text"
        [size]="16"
        color="#dc2626">
      </app-icon>
    </button>
  `,
})
export class SearchRoutineActionRendererComponent implements ICellRendererAngularComp {
  private params: (ICellRendererParams & { onClick?: (data: RoutineItem) => void }) | null = null;

  agInit(params: ICellRendererParams & { onClick?: (data: RoutineItem) => void }): void {
    this.params = params;
  }

  refresh(params: ICellRendererParams & { onClick?: (data: RoutineItem) => void }): boolean {
    this.params = params;
    return true;
  }

  onClick(event: MouseEvent): void {
    event.stopPropagation();
    if (this.params?.onClick && this.params?.data) {
      this.params.onClick(this.params.data as RoutineItem);
    }
  }
}

const ROUTINE_CATEGORY_OPTIONS: SelectOption[] = [
  { value: "CALENDAR BASED", label: "Calendar Based" },
  { value: "RUNNING HOUR BASED", label: "Running Hour Based" },
  { value: "ALTERNATE PERIODIC", label: "Alternate Periodic" },
];

const STATUS_COLOR_DUE = "#FF9999";
const STATUS_COLOR_DUE_LT_3M = "#f7e687";
const STATUS_COLOR_DUE_3_6M = "orange";

@Component({
  selector: "app-search-routines",
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MasterCard, DataGrid, SelectInput, IconComponent],
  templateUrl: "./search-routines.html",
  styleUrl: "./search-routines.css",
})
export class SearchRoutines implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(Call);
  private readonly router = inject(Router);
  private readonly toastr = inject(NotificationService);

  searchForm: FormGroup = this.fb.group({
    sub_department: [""],
    equipment: [""],
    routine_type: [""],
    routine_name: [""],
    search: [""],
  });
  readonly routines = signal<RoutineItem[]>([]);
  readonly subDepartmentOptions = signal<SelectOption[]>([]);
  readonly equipmentOptions = signal<SelectOption[]>([]);
  readonly routineTypeOptions = signal<SelectOption[]>(ROUTINE_CATEGORY_OPTIONS);
  readonly routineNameOptions = signal<SelectOption[]>([]);
  readonly headerStats = signal<HeaderStats>({
    due: 0,
    dueLessThan3M: 0,
    due3To6M: 0,
    other: 0,
  });
  readonly columnDefs: ColDef[] = [
    {
      headerName: "Sub Department",
      field: "section_name",
      flex: 1,
    },
    {
      headerName: "Equipment Name",
      field: "equipment_name",
      flex: 2,
    },
    {
      headerName: "Routine Type",
      field: "routine_type",
      flex: 1.2,
    },
    {
      headerName: "Routine Name",
      field: "routine_name",
      flex: 2,
    },
    {
      headerName: "Last Routine Date",
      field: "last_routine_date",
      flex: 1.3,
    },
    {
      headerName: "Next Due Date",
      field: "next_due_date",
      flex: 1.3,
    },
    {
      headerName: "Status",
      field: "due_status",
      flex: 1.2,
      minWidth: 120,
      cellRenderer: FussStatusRendererComponent,
    },
    {
      headerName: "Actions",
      field: "id",
      flex: 1,
      cellRenderer: SearchRoutineActionRendererComponent,
      cellRendererParams: {
        onClick: (data: RoutineItem) => this.onRowClicked(data),
      },
    },
  ];

  ngOnInit(): void {
    this.loadSubDepartmentOptions();
    this.getSearchPlanData();

    this.searchForm.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
      )
      .subscribe(({ sub_department }) => {
        this.loadEquipmentOptions(sub_department);
        this.getSearchPlanData();
      });
  }

  private loadSubDepartmentOptions(): void {
    this.api.getEmsSections().subscribe({
      next: (response) => {
        this.subDepartmentOptions.set(
          Object.entries(response.section_name ?? {}).map(([label, value]) => ({
            label,
            value,
          })),
        );
      },
      error: (error: unknown) => console.error("EMS Sections API Error:", error),
    });
  }

  private loadEquipmentOptions(sectionId?: number | string | null): void {
    this.api.getEmsEquipmentNames(sectionId || undefined).subscribe({
      next: (response) => {
        this.equipmentOptions.set(
          Object.entries(response.equipment_name ?? {}).map(([label, value]) => ({
            label,
            value,
          })),
        );
      },
      error: (error: unknown) => console.error("EMS Equipment Name API Error:", error),
    });
  }

  // All filters (including free-text search) are sent to the backend on every change.
  // NOTE: backend api/v1/ems/search/ does not yet read the `search` param — needs server-side support.
  private getSearchPlanData(): void {
    const { sub_department, equipment, routine_type, routine_name, search } =
      this.searchForm.getRawValue();

    this.api
      .getSearchPlanData({
        subDepartment: sub_department || undefined,
        equipment: equipment || undefined,
        routineType: routine_type || undefined,
        routineName: routine_name || undefined,
        search: search || undefined,
      })
      .subscribe({
        next: (response: EmsSearchResultItem[]) => {
          const data = (response ?? []).map((item) => this.toRoutineItem(item));
          this.routines.set(data);
          this.setHeaderStats(data);
          this.setRoutineNameOptions(data);
        },
        error: (error: unknown) => {
          console.error("Search Routine API Error:", error);
          this.routines.set([]);
        },
      });
  }

  private toRoutineItem(item: EmsSearchResultItem): RoutineItem {
    return {
      id: item.pk,
      section_id: 0,
      section_name: item.section,
      equipment_id: 0,
      equipment_name: item.equipment_name,
      routine_type: "",
      routine_name: item.routine_name,
      maintop_no: item.maintop_no,
      last_routine_date: item.last_routine_date,
      next_due_date: item.date,
      last_routine_running_hours: String(item.last_routine_running_hrs ?? ""),
      next_due_running_hours: String(item.next_due_running_hrs ?? ""),
      total_running_hours: String(item.total_running_hrs ?? ""),
      running_hours_updated_till: item.running_hrs_updated_tilldate,
      running_hours_available: String(item.running_hrs_available ?? ""),
      due_status: item.due_status,
      due_bucket: item.due_status,
      status_color: item.status_color,
    };
  }

  private setHeaderStats(routines: RoutineItem[]): void {
    let due = 0;
    let dueLessThan3M = 0;
    let due3To6M = 0;
    let other = 0;

    for (const routine of routines) {
      if (routine.status_color === STATUS_COLOR_DUE) due++;
      else if (routine.status_color === STATUS_COLOR_DUE_LT_3M) dueLessThan3M++;
      else if (routine.status_color === STATUS_COLOR_DUE_3_6M) due3To6M++;
      else other++;
    }

    this.headerStats.set({ due, dueLessThan3M, due3To6M, other });
  }

  private setRoutineNameOptions(routines: RoutineItem[]): void {
    const names = new Set(routines.map((routine) => routine.routine_name).filter(Boolean));
    this.routineNameOptions.set([...names].map((name) => ({ label: name, value: name })));
  }

  clearFilters(): void {
    this.searchForm.reset();

    this.searchForm.patchValue({
      sub_department: null,
      equipment: null,
      routine_type: null,
      routine_name: null,
      search: "",
    });

    this.equipmentOptions.set([]);
    this.getSearchPlanData();
  }

  onRowClicked(routine: unknown): void {
    this.router.navigate(["/afterAuth/op-maintenance/routine/due-routines"], {
      state: {
        routine,
      },
    });
  }
}
