import { Component, OnDestroy, OnInit, inject, signal, ChangeDetectionStrategy } from "@angular/core";

import { ActivatedRoute } from "@angular/router";
import { Subscription } from "rxjs";
import { SfdOverviewComponent } from "./overview/sfd-overview.component";
import { SfdConfigComponent } from "./config/sfd-config.component";
import { SfdManagementComponent } from "./management/sfd-management.component";
import { SfdReportsComponent } from "./reports/sfd-reports.component";
import { SfdInsightsComponent } from "./insights/sfd-insights.component";
import { SfdReferencesComponent } from "./sfd-references/sfd-references.component";

export type SfdTab =
  | "overview"
  | "config"
  | "actions"
  | "reports"
  | "insights"
  | "sfd-references";

/** Header tab route segment (:tab) → internal screen id. */
const TAB_ROUTE_MAP: Record<string, SfdTab> = {
  overview: "overview",
  configuration: "config",
  actions: "actions",
  reports: "reports",
  insights: "insights",
  "sfd-references": "sfd-references",
};

/**
 * Host shell for the SFD (Ship Fit Definition) module. The active screen is
 * driven by the `:tab` route segment, which is navigated to by the existing
 * app Header tabs (navigation.config: dashboard/overview|configuration|…).
 * No local tab strip and no Header/Sidebar changes.
 */
@Component({
  selector: "app-sfd-shell",
  standalone: true,
  imports: [
    SfdOverviewComponent,
    SfdConfigComponent,
    SfdManagementComponent,
    SfdReportsComponent,
    SfdInsightsComponent,
    SfdReferencesComponent
],
  templateUrl: "./sfd-shell.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrls: ["./sfd-shell.component.css"],
})
export class SfdShellComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private sub?: Subscription;

  readonly activeTab = signal<SfdTab>("overview");

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe((params) => {
      const tab = params.get("tab") ?? "overview";
      this.activeTab.set(TAB_ROUTE_MAP[tab] ?? "overview");
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
