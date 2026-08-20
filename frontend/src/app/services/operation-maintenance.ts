import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";
import { Call } from "./network/call";
import {
  DartDashboardResponse,
  MaintenancePeriodRow,
  SubDeptDefectRow,
} from "../Pages/op-maintenance/op-maintenance-dashboard/op-maintenance-dashboard.model";

@Injectable({
  providedIn: "root",
})
export class OperationMaintenance {
  private calls = inject(Call);


  async getDartSpares(type: string) {
    try {
      const res = await firstValueFrom(this.calls.getDartSpares(type));

      return res;
    } catch (error) {
      console.error("Error fetching spares", error);
      throw error;
    }
  }

  async getCurrentDepartmentId(): Promise<number | null> {
    try {
      const res = await firstValueFrom(this.calls.getCurrentUser());
      return res?.profile?.department ?? null;
    } catch (error) {
      console.error("Error fetching current user's department", error);
      return null;
    }
  }

  async getDartDashboard(departmentId: number): Promise<DartDashboardResponse> {
    try {
      return await firstValueFrom(this.calls.getDartDashboard(departmentId));
    } catch (error) {
      console.error("Error fetching DART dashboard", error);
      throw error;
    }
  }

  async getSubDeptDefects(subDept: string): Promise<SubDeptDefectRow[]> {
    try {
      const res = await firstValueFrom(this.calls.getSubDeptDefects(subDept));
      return res?.data ?? [];
    } catch (error) {
      console.error("Error fetching sub-department defects", error);
      return [];
    }
  }

  async getMaintenancePeriodsList(): Promise<MaintenancePeriodRow[]> {
    try {
      return await firstValueFrom(this.calls.getMaintenancePeriodsList());
    } catch (error) {
      console.error("Error fetching maintenance periods", error);
      return [];
    }
  }
}
