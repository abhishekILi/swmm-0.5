import { Routes } from "@angular/router";
import { ObsShell } from "./shell/obs-shell/obs-shell";

export const SHIP_INVENTORY_OBS_ROUTES: Routes = [
  {
    path: "",
    component: ObsShell,
    children: [
      { path: "", redirectTo: "dashboard", pathMatch: "full" },
      {
        path: "dashboard",
        loadComponent: () => import("./dashboard/obs-dashboard").then((m) => m.ObsDashboard),
      },
      {
        path: "search",
        loadComponent: () => import("./search/item-search/item-search").then((m) => m.ItemSearch),
      },
      {
        path: "search/add",
        loadComponent: () => import("./search/spare-add/spare-add").then((m) => m.SpareAdd),
      },
      {
        path: "search/issue-multiple",
        loadComponent: () => import("./search/multi-issue/multi-issue").then((m) => m.MultiIssue),
      },
      {
        path: "search/:id",
        loadComponent: () => import("./search/spare-detail/spare-detail").then((m) => m.SpareDetail),
      },
      {
        path: "search/:id/edit",
        loadComponent: () => import("./search/spare-edit/spare-edit").then((m) => m.SpareEdit),
      },
      {
        path: "search/:id/issue",
        loadComponent: () => import("./search/spare-issue/spare-issue").then((m) => m.SpareIssue),
      },
      {
        path: "return",
        loadComponent: () => import("./returns/return-list/return-list").then((m) => m.ReturnList),
      },

      // Ship Inventory ▾ — Maintainer Spare Requests
      {
        path: "requisitions/routine",
        loadComponent: () =>
          import("./requisitions/requisition-list/requisition-list").then((m) => m.RequisitionList),
        data: { kind: "routine", title: "Maintainer Spare Request - Routine DART" },
      },
      {
        path: "requisitions/defect",
        loadComponent: () =>
          import("./requisitions/requisition-list/requisition-list").then((m) => m.RequisitionList),
        data: { kind: "defect", title: "Maintainer Spare Request - Defect DART" },
      },
      {
        path: "requisitions/:kind/issue",
        loadComponent: () =>
          import("./requisitions/requisition-issue/requisition-issue").then((m) => m.RequisitionIssue),
      },

      // Internal Transactions ▾
      {
        path: "transactions/survey",
        loadComponent: () => import("./transactions/survey-list/survey-list").then((m) => m.SurveyList),
      },
      {
        path: "transactions/survey/:id",
        loadComponent: () =>
          import("./transactions/survey-details/survey-details").then((m) => m.SurveyDetails),
      },
      {
        path: "transactions/demand",
        loadComponent: () => import("./transactions/demand-list/demand-list").then((m) => m.DemandList),
      },
      {
        path: "transactions/demand/:id",
        loadComponent: () =>
          import("./transactions/demand-details/demand-details").then((m) => m.DemandDetails),
      },
      {
        path: "transactions/iif",
        loadComponent: () => import("./transactions/iif-list/iif-list").then((m) => m.IifList),
      },

      // History
      {
        path: "history",
        loadComponent: () => import("./history/history-page/history-page").then((m) => m.HistoryPage),
      },

      // References ▾
      {
        path: "references/masters",
        loadComponent: () =>
          import("./references/masters-page/masters-page").then((m) => m.MastersPage),
      },
      {
        path: "references/about",
        loadComponent: () => import("./references/about-page/about-page").then((m) => m.AboutPage),
      },

      // Dashboard "View more" drill-downs
      {
        path: "spares-issued-to-maintainers",
        loadComponent: () => import("./dashboard/issue-status-list/issue-status-list").then((m) => m.IssueStatusList),
        data: { kind: "to-maintainers", title: "Spares Issued to Maintainers" },
      },
      {
        path: "spares-issued-on-tyloan",
        loadComponent: () => import("./dashboard/issue-status-list/issue-status-list").then((m) => m.IssueStatusList),
        data: { kind: "ty-loan", title: "Spares Issued on Ty Loan" },
      },
      {
        path: "spares-returned",
        loadComponent: () =>
          import("./dashboard/spares-returned-list/spares-returned-list").then((m) => m.SparesReturnedList),
      },
      {
        path: "spares-less-than-50",
        loadComponent: () => import("./dashboard/spare-status-list/spare-status-list").then((m) => m.SpareStatusList),
        data: { kind: "less-than-50", title: "Spares < 50% in Inventory" },
      },
      {
        path: "d787j-deficiency",
        loadComponent: () => import("./dashboard/spare-status-list/spare-status-list").then((m) => m.SpareStatusList),
        data: { kind: "d787j-deficiency", title: "D787J Deficiency" },
      },
      {
        path: "critical-spare-list",
        loadComponent: () => import("./dashboard/spare-status-list/spare-status-list").then((m) => m.SpareStatusList),
        data: { kind: "critical", title: "Critical Spare List" },
      },
    ],
  },
];
