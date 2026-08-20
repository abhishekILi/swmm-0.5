import { CommonModule } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { FormBuilder, ReactiveFormsModule } from "@angular/forms";
import { Subject, debounceTime } from "rxjs";
import { MasterCard } from "../../../refit-maintenance/master-card/master-card";
import { NotificationService } from '../../../../Core/services/notification/notification.service';
import { Call } from "../../../../services/network/call";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { SelectInput } from "../../../../shared/components/select-input/select-input";
import {
  EquipmentDueForAber,
  EquipmentDueForAberResponse,
} from "./equipment-due-for-aber.model";
import { Router } from "@angular/router";
import { RaiseAberRenderer } from "../../action-forms/raise-aber-renderer/raise-aber-renderer";
import { StatusRenderer } from "../../action-forms/status-renderer";
import { IconComponent } from '../../../../shared/components/icon/icon.component';

@Component({
  selector: "app-equipment-due-for-aber",
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MasterCard, DataGrid, SelectInput, IconComponent],
  templateUrl: "./equipment-due-for-aber.html",
  styleUrl: "./equipment-due-for-aber.css",
})
export class EquipmentDueForABER implements OnInit {

  private api = inject(Call);
  private toastr = inject(NotificationService);
  private fb = inject(FormBuilder);
  private router = inject(Router);

  filteredMaintopRoutines = signal<EquipmentDueForAber[]>([]);
  nomenclatureOptions: { label: string; value: string }[] = [];
  compartmentOptions: { label: string; value: string }[] = [];

  searchText = "";

  equipment_due_for_aber_form = this.fb.group({
    nomenclature: [""],
    compartment: [""],
  });

  private readonly filtersChanged = new Subject<void>();

  ngOnInit(): void {
    this.loadAberData();

    // Backend does the filtering — debounce so typing/dropdown changes don't
    // fire a request per keystroke/click.
    this.filtersChanged.pipe(debounceTime(300)).subscribe(() => {
      this.loadAberData();
    });

    this.equipment_due_for_aber_form.valueChanges.subscribe(() => {
      this.filtersChanged.next();
    });
  }

  loadAberData(): void {
    const { nomenclature, compartment } =
      this.equipment_due_for_aber_form.getRawValue();

    this.api
      .getABERTriggerRoutinesData({
        nomenclature: nomenclature || undefined,
        compartment: compartment || undefined,
        search: this.searchText.trim() || undefined,
      })
      .subscribe({
        next: (res: EquipmentDueForAberResponse) => {
          this.filteredMaintopRoutines.set(res.result || [])

          this.nomenclatureOptions = (res.nomenclatures || []).map((item) => ({
            label: item,
            value: item,
          }));

          this.compartmentOptions = (res.compartments || []).map((item) => ({
            label: item,
            value: item,
          }));
        },
        error: (err) => {
          console.error(err);
          this.toastr.error("Failed to load ABER data");
        },
      });
  }

  onSearch(event: Event): void {
    this.searchText = (event.target as HTMLInputElement).value;
    this.filtersChanged.next();
  }

  clearFilters(): void {
    this.searchText = "";

    this.equipment_due_for_aber_form.reset({
      nomenclature: "",
      compartment: "",
    });

    this.loadAberData();
  }

  defectColumnDefs = [
    {
      headerName: "INSMA Equipment Code",
      field: "insma_code",
      flex: 1,
    },
    {
      headerName: "Equipment Nomenclature",
      field: "nomenclature",
      flex: 2,
    },
    {
      headerName: "Compartment Name",
      field: "compartment",
      flex: 1.2,
    },
    {
      headerName: "Date of Installation",
      field: "installation_date",
      flex: 1.5,
    },
    {
      headerName: "Years since Installation",
      field: "years_since",
      flex: 1,
    },
    {
      headerName: "Status",
      field: "status",
      flex: 1,
      cellRenderer: StatusRenderer,
    },
    {
      headerName: "Actions",
      field: "actions",
      cellRenderer: RaiseAberRenderer,
      cellRendererParams: {
        buttonLabel: "Raise ABER",
        onClick: (data: EquipmentDueForAber) => this.raiseAber(data),
      },
      width: 180,
    },
  ];
  raiseAber(data: EquipmentDueForAber): void {
    this.router.navigate(["/afterAuth/op-maintenance/routine/raise-FUSS"], {
      state: { equipment: data },
    });
  }
}
