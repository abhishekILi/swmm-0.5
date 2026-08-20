import { CommonModule } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { Subject, debounceTime, distinctUntilChanged } from "rxjs";
import { MasterCard } from "../../../refit-maintenance/master-card/master-card";
import { Call } from "../../../../services/network/call";
import { NotificationService } from '../../../../Core/services/notification/notification.service';
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import {
  Routine,
  RoutineResponse,
} from "../calendar-based-routines/calendar-based-routines.model";

@Component({
  selector: "app-r-h-routines",
  standalone: true,
  imports: [CommonModule, MasterCard, DataGrid, IconComponent],
  templateUrl: "./r-h-routines.html",
  styleUrl: "./r-h-routines.css",
})
export class RHRoutines implements OnInit {
  filteredMaintopRoutines = signal<Routine[]>([]);
  searchText = "";
  private api = inject(Call);
  private toastr = inject(NotificationService);
  private readonly searchChanged = new Subject<string>();

  defectColumnDefs = [
    {
      headerName: "PK",
      field: "pk",
      flex: 1,
    },
    {
      headerName: "Routine Name",
      field: "routine_name",
      flex: 2,
    },
    {
      headerName: "Section",
      field: "section",
      flex: 1.5,
    },
    {
      headerName: "Equipment Name",
      field: "equipment_name",
      flex: 1.5,
    },
    {
      headerName: "Maintop No",
      field: "maintop_no",
      flex: 1,
    },
    {
      headerName: "Last Routine RH",
      field: "last_routine_running_hrs",
      flex: 1,
    },
    {
      headerName: "Next Due RH",
      field: "next_due_running_hrs",
      flex: 1,
    },
    {
      headerName: "Total Running Hrs",
      field: "total_running_hrs",
      flex: 1,
    },
    {
      headerName: "Running Hrs Available",
      field: "running_hrs_available",
      flex: 1,
    },
    {
      headerName: "Updated Till Date",
      field: "running_hrs_updated_tilldate",
      flex: 1.5,
    },
  ];

  ngOnInit(): void {
    this.loadRHBasedRoutines();

    this.searchChanged.pipe(debounceTime(300), distinctUntilChanged()).subscribe((search) => {
      this.loadRHBasedRoutines(search);
    });
  }

  loadRHBasedRoutines(search?: string): void {
    this.api.getRHBasedRoutinesData(search).subscribe({
      next: (res: RoutineResponse) => {
        this.filteredMaintopRoutines.set(res.result ?? [])
      },
      error: (err) => {
        console.error(err);
        this.toastr.error("Failed to load R/H Based Routines");
      },
    });
  }
  onSearch(event: Event): void {
    this.searchText = (event.target as HTMLInputElement).value;
    this.searchChanged.next(this.searchText);
  }
}
