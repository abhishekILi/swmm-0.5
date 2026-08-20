import { CommonModule } from "@angular/common";
import { HttpErrorResponse } from "@angular/common/http";
import { Component, OnInit, inject } from "@angular/core";
import { FormBuilder, ReactiveFormsModule } from "@angular/forms";
import { NotificationService } from '../../../../../Core/services/notification/notification.service';

import { MasterCard } from "../../../../refit-maintenance/master-card/master-card";

import { SelectInput } from "../../../../../shared/components/select-input/select-input";
import { InputField } from "../../../../../shared/components/input-field/input-field";

import { Call } from "../../../../../services/network/call";
import {
  CloseRoutinePayload,
  CloseRoutineResponse,
} from "../fuss-trigger-list.model";
import { Router } from "@angular/router";

@Component({
  selector: "app-close-fuss",
  standalone: true,
  imports: [CommonModule, MasterCard, ReactiveFormsModule, SelectInput, InputField],
  templateUrl: "./close-fuss.html",
  styleUrl: "./close-fuss.css",
})
export class CloseFUSS implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(Call);
  private router = inject(Router);
  private toastr = inject(NotificationService);

  routineId!: number;

  closeRoutineFuss = this.fb.group({
    routineDartNo: [""],
    equipmentClass: [""],
    equipmentSerialNo: [""],
    nomenclature: [""],
    dueDate: [""],
    maintenanceRemarks: [""],
    locationOnBoard: [""],
    maintopRoutineNo: [""],
    routineDescription: [""],
    routineCompletionDate: [""],
    runningHours: [""],
    timeConsumedHours: [""],
    timeConsumedMinutes: [""],
    completedByPno: [""],
    name: [""],
    rank: [""],
    totalManpower: [""],
    trialTeamNeeded: ["Yes"],
    remarks: [""],
  });

  hoursOptions: { label: string; value: number }[] = [];

  minutesOptions: { label: string; value: number }[] = [];

  rankOptions: { label: string; value: number }[] = [];

  manpowerOptions = [
    { label: "1", value: 1 },
    { label: "2", value: 2 },
    { label: "3", value: 3 },
    { label: "4", value: 4 },
    { label: "5", value: 5 },
  ];

  trialOptions = [
    { label: "Yes", value: true },
    { label: "No", value: false },
  ];

  ngOnInit(): void {
    this.routineId = history.state.routineId;

    console.log("Routine ID:", this.routineId);

    if (this.routineId) {
      this.getCloseRoutineDetails();
    }
  }

  getCloseRoutineDetails(): void {
    this.api
      .getCloseRoutineById(this.routineId)
      .subscribe({
        next: (response: CloseRoutineResponse) => {
          this.hoursOptions = response.hours_range.map((hour) => ({
            label: hour.toString(),
            value: hour,
          }));

          this.minutesOptions = response.minutes_range.map((minute) => ({
            label: minute.toString(),
            value: minute,
          }));

          this.rankOptions = response.rank_obj.map((rank) => ({
            label: rank.rankdescription,
            value: rank.rankid,
          }));

          this.closeRoutineFuss.patchValue({
            routineDartNo: response.old_dart_number ?? "",
            equipmentClass: response.equipment_class,
            equipmentSerialNo: response.equipment_serial_no,
            nomenclature: response.nomenclature,
            dueDate: response.due_date,
            maintenanceRemarks: response.maintop_remarks,
            locationOnBoard: response.location_on_board,
            maintopRoutineNo: response.maintop_routine_number,
            routineDescription: response.routine_description,
            name: response.fullname,
            rank:
              response.rank_obj
                .find((r) => r.rankdescription === response.rankname)
                ?.rankid.toString() ?? null,
          });
        },
        error: (error) => {
          console.error(error);
          this.toastr.error("Failed to load routine details.");
        },
      });
  }

  backToList(): void {
    this.router.navigateByUrl(
      "/afterAuth/op-maintenance/routine/FUSS-triger-list",
    );
  }

  closeRoutine(): void {
    const form = this.closeRoutineFuss.getRawValue();

    const payload: CloseRoutinePayload = {
      date_of_completion: form.routineCompletionDate ?? "",

      running_hour: Number(form.runningHours ?? 0),

      rank_routine: Number(form.rank ?? 0),

      rank_other: "",

      hours: Number(form.timeConsumedHours ?? 0),

      minutes: Number(form.timeConsumedMinutes ?? 0),

      carried_by: form.name ?? "",

      p_no: form.completedByPno ?? "",

      total_manpower: Number(form.totalManpower ?? 0),

      due_running_hour: 0, // Update if this value comes from another field/API

      remarks: form.remarks ?? "",

      completion_details: "", // Add a form field if user should enter this

      trial_team: String(form.trialTeamNeeded ?? ""),

      rec_for_deletion: "No", // Change if required by backend

      old_dart_number: form.routineDartNo ?? "",

      spares: [],
    };

    this.api
      .updateCloseFUSSRoutine(this.routineId, payload)
      .subscribe({
        next: () => {
          this.toastr.success("Routine closed successfully.");
          this.router.navigateByUrl(
            "/afterAuth/op-maintenance/routine/planned-routines",
          );
        },
        error: (error: HttpErrorResponse) => {
          console.error(error);
          this.toastr.error("Failed to close routine.");
        },
      });
  }
}
