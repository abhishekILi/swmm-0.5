import { CommonModule } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { Router } from "@angular/router";
import { Subject, debounceTime } from "rxjs";

import { MasterCard } from "../../../refit-maintenance/master-card/master-card";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { Call } from "../../../../services/network/call";
import { NotificationService } from '../../../../Core/services/notification/notification.service';
import { FormBuilder, ReactiveFormsModule } from "@angular/forms";
import { SelectInput } from "../../../../shared/components/select-input/select-input";

import {
  FUSSTriggerListResponse,
  FUSSTriggerRoutine,
} from "./fuss-trigger-list.model";
import { FussStatusRendererComponent } from "../../action-forms/fuss-status-renderer";
import { IconComponent } from '../../../../shared/components/icon/icon.component';

@Component({
  selector: "app-fuss-triger-list",
  standalone: true,
  imports: [CommonModule, MasterCard, DataGrid, SelectInput, ReactiveFormsModule, IconComponent],
  templateUrl: "./fuss-triger-list.html",
  styleUrl: "./fuss-triger-list.css",
})
export class FUSSTrigerList implements OnInit {
  private router = inject(Router);

  private api = inject(Call);
  private fb = inject(FormBuilder);
  private toastr = inject(NotificationService);

  fussTriggerForm = this.fb.group({
    equipmentSection: [""],
    equipmentName: [""],
    routineName: [""],
  });

  equipmentSectionOptions: { label: string; value: string }[] = [];
  equipmentNameOptions: { label: string; value: string }[] = [];
  routineNameOptions: { label: string; value: string }[] = [];

  searchText = "";
  filteredMaintopRoutines = signal<FUSSTriggerRoutine[]>([])

  private readonly filtersChanged = new Subject<void>();

  defectColumnDefs = [
    {
      headerName: "Sub Dept",
      field: "sub_dept",
      flex: 1.5,
    },
    {
      headerName: "Equipment Nomenclature",
      field: "equipment_nomenclature",
      flex: 2,
    },
    {
      headerName: "Routine Name",
      field: "routine_name",
      flex: 2.5,
    },
    {
      headerName: "Status",
      field: "status",
      flex: 1,
      cellRenderer: FussStatusRendererComponent,
    },
    {
      headerName: "Previous Routine Completion Date",
      field: "prev_completion_date",
      flex: 1.5,
    },
    {
      headerName: "Next Routine Due Date",
      field: "next_due_date",
      flex: 1.5,
    },
    {
      headerName: "Total R/H Updated Upto",
      field: "total_rh_updated_upto",
      flex: 1.5,
    },
    {
      headerName: "RHSI",
      field: "rhsi",
      flex: 1,
    },
    {
      headerName: "Routine Completed @ R/H",
      field: "routine_completed_at_rh",
      flex: 1.5,
    },
    {
      headerName: "Routine Due @ R/H",
      field: "routine_due_at_rh",
      flex: 1.5,
    },
    {
      headerName: "Maintops No",
      field: "maintops_no",
      flex: 1.5,
    },
    {
      headerName: "Total Sub-Subroutines",
      field: "total_sub_subroutines",
      flex: 1.5,
    },
    {
      headerName: "SS Routines",
      field: "ss_routines",
      flex: 1,
    },
    {
      headerName: "DYD Routines",
      field: "dyd_routines",
      flex: 1,
    },

  ];

  ngOnInit(): void {
    this.getFUSSTriggerList();

    // Backend does the filtering — debounce so typing/dropdown changes don't
    // fire a request per keystroke/click.
    this.filtersChanged.pipe(debounceTime(300)).subscribe(() => {
      this.getFUSSTriggerList();
    });

    this.fussTriggerForm.valueChanges.subscribe(() => {
      this.filtersChanged.next();
    });
  }

  clearFilters(): void {
    this.fussTriggerForm.reset();
    this.searchText = "";
    this.getFUSSTriggerList();
  }

  onSearch(event: Event): void {
    this.searchText = (event.target as HTMLInputElement).value;
    this.filtersChanged.next();
  }

  getFUSSTriggerList(): void {
    const { equipmentSection, equipmentName, routineName } =
      this.fussTriggerForm.getRawValue();

    this.api
      .getFUSSTriggerListRoutinesData({
        subDept: equipmentSection || undefined,
        equipment: equipmentName || undefined,
        routineName: routineName || undefined,
        search: this.searchText.trim() || undefined,
      })
      .subscribe({
        next: (response: FUSSTriggerListResponse) => {
          this.filteredMaintopRoutines.set(response?.result ?? [])
          const filterArrays = Object.entries(response)
            .filter(([key, value]) => key !== "result" && Array.isArray(value))
            .map(([, value]) => value as string[]);
          this.equipmentSectionOptions = (filterArrays[0] ?? []).map(
            (item: string) => ({
              label: item,
              value: item,
            }),
          );

          this.equipmentNameOptions = (filterArrays[1] ?? []).map(
            (item: string) => ({
              label: item,
              value: item,
            }),
          );

          this.routineNameOptions = (filterArrays[2] ?? []).map(
            (item: string) => ({
              label: item,
              value: item,
            }),
          );
        },
        error: (error) => {
          console.error(error);
          this.toastr.error("Failed to load FUSS Trigger List", "Error");
        },
      });
  }

  navigateTo(url: string): void {
    this.router.navigateByUrl(url);
  }
}
