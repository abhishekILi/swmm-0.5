import { CommonModule } from "@angular/common";
import { Component, inject } from "@angular/core";
import { Router } from "@angular/router";
import { ICellRendererAngularComp } from "ag-grid-angular";
import { ICellRendererParams } from "ag-grid-community";
import { IconComponent } from "../../../shared/components/icon/icon.component";

interface ActionRendererData {
  dart_number?: string;
  opra_no?: string;
  dl_no?: string;
  id?: string | number;
}

interface ActionRendererParams extends ICellRendererParams {
  onView?: (data: ActionRendererData | undefined) => void;
}

@Component({
  selector: "app-action-renderer",
  standalone: true,
  imports: [CommonModule, IconComponent],
  templateUrl: "./action-renderer.html",
  styleUrl: "./action-renderer.css",
})
export class ActionRenderer implements ICellRendererAngularComp {
  private router = inject(Router);

  params!: ActionRendererParams;
  showActions = false;

  agInit(params: ActionRendererParams): void {
    this.params = params;

    const data = params.data as ActionRendererData | undefined;

    this.showActions =
      !!data?.dart_number ||
      !!data?.opra_no ||
      !!data?.dl_no;
  }

  refresh(): boolean {
    return false;
  }

  openDetails(): void {
    this.params.onView?.(this.params.data as ActionRendererData | undefined)
  }

  closeDart(): void {
    this.router.navigate([
      "/afterAuth/op-maintenance/close-defects",
      (this.params.data as ActionRendererData | undefined)?.id,
    ]);
  }
}
