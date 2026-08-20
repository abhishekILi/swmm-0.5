import { CommonModule } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { ColDef } from "ag-grid-community";
import { MasterCard } from "../../../../refit-maintenance/master-card/master-card";
import { DataGrid } from "../../../../../shared/components/data-grid/data-grid";
import { FussStatusRendererComponent } from "../../../action-forms/fuss-status-renderer";
import { RaiseAberRenderer } from "../../../action-forms/raise-aber-renderer/raise-aber-renderer";
import { Call } from "../../../../../services/network/call";
import { NotificationService } from '../../../../../Core/services/notification/notification.service';
import { RoutineDetailItem, SearchDetailResultItem } from "../search-routines.model";
import { FormBuilder, FormGroup, ReactiveFormsModule } from "@angular/forms";
import { Router } from "@angular/router";
import { IconComponent } from '../../../../../shared/components/icon/icon.component';

interface SelectedRoutineState {
  id: number;
  maintop_no?: string;
  routine_name?: string;
  equipment_name?: string;
}

@Component({
  selector: "app-routine-due",
  standalone: true,
  imports: [CommonModule, MasterCard, ReactiveFormsModule, DataGrid, IconComponent],
  templateUrl: "./routine-due.html",
  styleUrl: "./routine-due.css",
})
export class RoutineDue implements OnInit {
  private readonly api = inject(Call);
  private readonly toastr = inject(NotificationService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  readonly maintopRoutines = signal<RoutineDetailItem[]>([]);
  readonly filteredRoutines = signal<RoutineDetailItem[]>([]);
  private readonly selectedRoutine = history.state.routine as SelectedRoutineState | undefined;
  readonly routineForm: FormGroup = this.fb.group({
    maintop_no: [{ value: "", disabled: true }],
    routine_name: [{ value: "", disabled: true }],
    equipment_name: [{ value: "", disabled: true }],
  });

  ngOnInit(): void {
    if (!this.selectedRoutine?.id) {
      this.toastr.warning("No routine selected.");
      return;
    }

    this.routineForm.patchValue({
      maintop_no: this.selectedRoutine.maintop_no ?? "",
      routine_name: this.selectedRoutine.routine_name ?? "",
      equipment_name: this.selectedRoutine.equipment_name ?? "",
    });

    this.getRoutineDetails(this.selectedRoutine.id);
  }

  private getRoutineDetails(id: number): void {
    this.api.getRoutineById(id).subscribe({
      next: (response) => {
        const items = (response?.result ?? []).map((item) => this.toRoutineDetailItem(item));
        this.maintopRoutines.set(items);
        this.filteredRoutines.set(items);
      },
      error: (error: unknown) => {
        console.error("Unable to fetch routine detail.", error);
        this.toastr.error("Unable to fetch routine detail.");
        this.maintopRoutines.set([]);
        this.filteredRoutines.set([]);
      },
    });
  }

  private toRoutineDetailItem(item: SearchDetailResultItem): RoutineDetailItem {
    return {
      id: item.pk,
      routine_name: item.routine_name,
      equipment_name: item.equipment_name,
      maintop_no: item.maintop_no,
      dart_number: item.dart_number,
      routine_description: item.routine_description,
      routine_no: item.routine_no,
      previous_routine_completed_date: item.previous_routine_completed_date,
      due_date: item.due_date,
      due_at_rh: String(item.due_at_rh ?? ""),
      previous_completed_at_rh: String(item.previous_completed_at_rh ?? ""),
      action_by: item.action_by,
      due_status: item.due_status,
      due_bucket: item.due_status,
      status_color: item.status_color,
    };
  }

  columnDefs: ColDef[] = [
    {
      headerName: "DART Number",
      field: "dart_number",
      flex: 1,
    },
    {
      headerName: "Status",
      field: "due_status",
      flex: 1.2,
      minWidth: 120,
      cellRenderer: FussStatusRendererComponent,
    },
    {
      headerName: "Routine No",
      field: "routine_no",
      flex: 1.5,
    },
    {
      headerName: "Previous Routine Completion Date",
      field: "previous_routine_completed_date",
      flex: 1.5,
    },
    {
      headerName: "Sub Routine Description",
      field: "routine_description",
      flex: 1.5,
    },
    {
      headerName: "Actions",
      flex: 1,
      sortable: false,
      filter: false,
      cellRenderer: RaiseAberRenderer,
      cellRendererParams: {
        buttonLabel: "Plan Routine",
        onClick: (data: RoutineDetailItem) => this.planRoutine(data),
      },
      width: 180,
    },
  ];

  planRoutine(data: RoutineDetailItem): void {
    this.router.navigate(
      ["/afterAuth/op-maintenance/routine/r-d-plan-routine"],
      {
        state: {
          routine: data,
        },
      },
    );
  }
}
