import { Component, ChangeDetectionStrategy, OnInit, inject, signal } from "@angular/core";
import { RouterLink } from "@angular/router";
import { ColDef } from "ag-grid-community";

import { KpiCard } from "../../../shared/components/kpi-card/kpi-card";
import { PanelCard } from "../../../shared/components/panel-card/panel-card";
import { BarChart } from "../../../shared/components/bar-chart/bar-chart";
import { LineChart } from "../../../shared/components/line-chart/line-chart";
import { ModalComponent } from "../../../shared/components/modal/modal.component";
import { DataGrid } from "../../../shared/components/data-grid/data-grid";
import { PageHeaderBar } from "../../../shared/components/page-header-bar/page-header-bar";
import { KmsStateService } from "../state/kms-state.service";

@Component({
  selector: "app-kms-dashboard",
  standalone: true,
  imports: [KpiCard, PanelCard, BarChart, LineChart, ModalComponent, DataGrid, RouterLink, PageHeaderBar],
  templateUrl: "./kms-dashboard.html",
  styleUrl: "./kms-dashboard.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KmsDashboard implements OnInit {
  private readonly store = inject(KmsStateService);

  /** Hidden for now per request — flip back to true to restore the header bar. */
  readonly showHeaderBar = false;

  readonly stats = this.store.stats;
  readonly dashboardLoading = this.store.dashboardLoading;
  readonly dashboardError = this.store.dashboardError;
  readonly equipmentChartData = this.store.equipmentChartData;
  readonly categoryChartData = this.store.categoryChartData;
  readonly correspondenceLabels = this.store.correspondenceLabels;
  readonly correspondenceSeries = this.store.correspondenceSeries;
  readonly correspondenceDetail = this.store.correspondenceDetail;

  readonly showDetailModal = signal(false);

  readonly detailColumnDefs: ColDef[] = [
    { field: "name", headerName: "Ref / File No.", flex: 1 },
    { field: "certificate_subtype", headerName: "Type", width: 120, valueFormatter: (p) => (p["value"] === "inmail" ? "In-mail" : "Out-mail") },
    { field: "issue_date", headerName: "Date", width: 130 },
    { field: "recieved_from_unit", headerName: "Received From", flex: 1 },
    { field: "addressed_to_unit", headerName: "Addressed To", flex: 1 },
    { field: "remarks", headerName: "Remarks", flex: 1.5 },
  ];

  ngOnInit(): void {
    void this.store.loadDashboard();
  }

  openDetailModal(): void {
    this.showDetailModal.set(true);
  }

  closeDetailModal(): void {
    this.showDetailModal.set(false);
  }
}
