import { CommonModule } from "@angular/common";
import { Component, OnInit, inject, signal } from "@angular/core";
import { Subject, debounceTime, distinctUntilChanged } from "rxjs";
import { MasterCard } from "../../../refit-maintenance/master-card/master-card";
import { Call } from "../../../../services/network/call";
import { NotificationService } from '../../../../Core/services/notification/notification.service';
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { Routine, RoutineResponse } from "./calendar-based-routines.model";
import { IconComponent } from '../../../../shared/components/icon/icon.component';

@Component({
  selector: "app-calendar-based-routines",
  standalone: true,
  imports: [CommonModule, MasterCard, DataGrid, IconComponent],
  templateUrl: "./calendar-based-routines.html",
  styleUrls: ["./calendar-based-routines.css"],
})
export class CalendarBasedRoutines implements OnInit {

  private api = inject(Call);
  private toastr = inject(NotificationService);

  filteredMaintopRoutines = signal<Routine[]>([]);
  searchText = '';

  private readonly searchChanged = new Subject<string>();

  ngOnInit(): void {
    this.loadCalendarBasedRoutines();

    this.searchChanged.pipe(debounceTime(300), distinctUntilChanged()).subscribe((search) => {
      this.loadCalendarBasedRoutines(search);
    });
  }

  loadCalendarBasedRoutines(search?: string): void {
    this.api.getCalenderRoutinesData(search).subscribe({
      next: (res: RoutineResponse) => {
        this.filteredMaintopRoutines.set(res.result ?? [])
      },
      error: (err) => {
        console.error(err);
        this.toastr.error("Failed to load Calendar Based Routines");
      },
    });
  }

  defectColumnDefs = [
    {
      headerName: "Sub-Department",
      field: "sub_department",
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
      flex: 2,
    },
    {
      headerName: "Routine Status",
      field: "routine_status",
      flex: 1.5,
    },
    {
      headerName: "Total SS Routines",
      field: "total_ss_routines",
      flex: 1,
    },
    {
      headerName: "Total DYD Routines",
      field: "total_dyd_routines",
      flex: 1,
    },
    {
      headerName: "Last Routine Completion Date",
      field: "last_routine_completion_date",
      flex: 2,
    },
    {
      headerName: "Next Due Date",
      field: "next_due_date",
      flex: 2,
    },
    {
      headerName: "MAINTOP No",
      field: "maintop_no",
      flex: 1.5,
    },
    {
      headerName: "Total Sub-routines",
      field: "total_sub_routines",
      flex: 1.5,
    },
  ];
  onSearch(event: Event): void {
    this.searchText = (event.target as HTMLInputElement).value;
    this.searchChanged.next(this.searchText);
  }
}
