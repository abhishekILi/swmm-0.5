import { Routes } from "@angular/router";
import { MainLayout } from "./Core/layout/main-layout/main-layout";
import { OuterLayout } from "./Core/layout/outer-layout/outer-layout";
import { authGuard } from "./Core/auth/guards/auth-guard";
export const routes: Routes = [
  // OUTER LAYOUT
  {
    path: "",
    component: OuterLayout,
    children: [
      {
        path: "",
        redirectTo: "landing",
        pathMatch: "full",
      },

      {
        path: "landing",
        //   canActivate: [guestGuard],
        loadComponent: () =>
          import("./Modules/landing/landing.component").then(
            (m) => m.LandingComponent,
          ),
      },
    ],
  },
  {
    path: "afterAuth",
    canActivate: [authGuard],
    component: MainLayout,
    children: [
      {
        path: "home",
        children: [
          {
            path: "",
            redirectTo: "overview",
            pathMatch: "full",
          },
          {
            path: "overview",
            loadComponent: () =>
              import("./Pages/home/home/home").then(
                (m) => m.Home,
              ),
          },
          {
            path: "daily-orders-history",
            loadComponent: () =>
              import("./Pages/home/daily-orders-history/daily-orders-history").then(
                (m) => m.DailyOrdersHistory,
              ),
          },
          {
            path: "divisional-organisation",
            loadComponent: () =>
              import("./Pages/home/divisional-organisation/divisional-organisation").then(
                (m) => m.DivisionalOrganisation,
              ),
          },
          {
            path: "know-your-regulators",
            loadComponent: () =>
              import("./Pages/home/know-your-regulators/know-your-regulators").then(
                (m) => m.KnowYourRegulators,
              ),
          },
          {
            path: "gallery",
            loadComponent: () =>
              import("./Pages/home/gallery/gallery").then((m) => m.Gallery),
          },
          {
            path: "references",
            children: [
              {
                path: "",
                redirectTo: "master",
                pathMatch: "full",
              },
              {
                path: "master",
                loadComponent: () =>
                  import("./Pages/home/department-master/department-master").then(
                    (m) => m.DepartmentMasterComponent,
                  ),
              },
            ],
          },
        ],
      },
      {
        path: "ship",
        children: [
          {
            path: "",
            redirectTo: "overview",
            pathMatch: "full",
          },
          {
            path: ":tab",
            loadComponent: () =>
              import(
                "./Modules/Operations & Sustainment/ship-configuration/sfd/sfd-shell.component"
              ).then((m) => m.SfdShellComponent),
          },
        ],
      },

      {
        path: "inbox",
        children: [
          {
            path: "",
            redirectTo: "dashboard",
            pathMatch: "full",
          },
          {
            path: "dashboard",
            loadComponent: () =>
              import("./shared/components/development-in-progress/development-in-progress").then(
                (m) => m.DevelopmentInProgress,
              ),
          },
          {
            path: "overview",
            loadComponent: () =>
              import("./shared/components/development-in-progress/development-in-progress").then(
                (m) => m.DevelopmentInProgress,
              ),
          },
        ],
      },
      {
        path: "outbox",
        children: [
          {
            path: "",
            redirectTo: "dashboard",
            pathMatch: "full",
          },
          {
            path: "dashboard",
            loadComponent: () =>
              import("./shared/components/development-in-progress/development-in-progress").then(
                (m) => m.DevelopmentInProgress,
              ),
          },
          {
            path: "overview",
            loadComponent: () =>
              import("./shared/components/development-in-progress/development-in-progress").then(
                (m) => m.DevelopmentInProgress,
              ),
          },
        ],
      },
      {
        path: "divisional_Organisation",
        children: [
          { path: "", redirectTo: "overview", pathMatch: "full" },

        ],
      },
      {
        path: "Ship_Crew_and_HR",
        loadChildren: () =>
          import("./Pages/ship-crew/ship-crew.routes").then((m) => m.SHIP_CREW_ROUTES),
      },
      // {
      //   path: "op-maintenance",
      //   children: [
      //     { path: "", redirectTo: "defect/overview", pathMatch: "full" },
      //     {
      //       path: "defect",
      //       children: [
      //         { path: "", redirectTo: "overview", pathMatch: "full" },
      //         {
      //           path: "overview",
      //           loadComponent: () =>
      //             import(
      //               "./Pages/op-maintenance/op-maintenance-dashboard/op-maintenance-dashboard"
      //             ).then((m) => m.OpMaintenanceDashboard),
      //         },
      //         {
      //           path: "create",
      //           loadComponent: () =>
      //             import(
      //               "./Pages/op-maintenance/defect/create-defect/create-defect"
      //             ).then((m) => m.CreateDefect),
      //         },
      //       ],
      //     },
      //   ],
      // },


      {
        path: "op-maintenance",
        children: [
          { path: "", redirectTo: "defect/overview", pathMatch: "full" },

          {
            path: "routine",
            children: [
              {
                path: "",
                redirectTo: "dashboard",
                pathMatch: "full",
              },
              {
                path: "dashboard",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/ems-dashboard/ems-dashboard").then(
                    (m) => m.EmsDashboard,
                  ),
              },
              {
                path: "unique-maintop-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/routines-dashboard").then(
                    (m) => m.RoutinesDashboard,
                  ),
              },
              {
                path: "slip-calculator",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/slip-calculator/slip-calculator").then(
                    (m) => m.SlipCalculator,
                  ),
              },
              {
                path: "r-h-based-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/r-h-routines/r-h-routines").then(
                    (m) => m.RHRoutines,
                  ),
              },
              {
                path: "calendar-based-routing",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/calendar-based-routines/calendar-based-routines").then(
                    (m) => m.CalendarBasedRoutines,
                  ),
              },
              {
                path: "equipment-due-for-ABER",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/equipment-due-for-aber/equipment-due-for-aber").then(
                    (m) => m.EquipmentDueForABER,
                  ),
              },
              {
                path: "FUSS-triger-list",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/fuss-triger-list/fuss-triger-list").then(
                    (m) => m.FUSSTrigerList,
                  ),
                children: [],
              },
              {
                path: "close-fuss",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/fuss-triger-list/close-fuss/close-fuss").then(
                    (m) => m.CloseFUSS,
                  ),
              },
              {
                path: "fuss-triger-raise-fuss",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/fuss-triger-list/fuss-triger-raise-fuss/fuss-triger-raise-fuss").then(
                    (m) => m.FUSSTrigerRaiseFuss,
                  ),
              },
              {
                path: "search-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/search-routines/search-routines").then(
                    (m) => m.SearchRoutines,
                  ),
              },
              {
                path: "reference",
                redirectTo: "references/masters",
                pathMatch: "full",
              },
              {
                path: "references/masters",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/references/references").then(
                    (m) => m.References,
                  ),
              },
              {
                path: "references/exported-files",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/references/exported-files-dl1/exported-files-dl1").then(
                    (m) => m.ExportedFilesDl1,
                  ),
              },
              {
                path: "references/about-us",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/references/about-us/about-us").then(
                    (m) => m.AboutUs,
                  ),
              },
              {
                path: "dl1-generation/search-refit",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/dl1-generation/search-refit-routines/search-refit-routines").then(
                    (m) => m.SearchRefitRoutines,
                  ),
              },
              {
                path: "dl1-generation/refit-routine-detail",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/dl1-generation/refit-routine-detail/refit-routine-detail").then(
                    (m) => m.RefitRoutineDetailComponent,
                  ),
              },
              {
                path: "dl1-generation/generate",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/dl1-generation/generate-dl1/generate-dl1").then(
                    (m) => m.GenerateDl1,
                  ),
              },
              {
                path: "due-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/search-routines/routine-due/routine-due").then(
                    (m) => m.RoutineDue,
                  ),
              },
              {
                path: "r-d-plan-routine",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/search-routines/r-d-plan-routine/r-d-plan-routine").then(
                    (m) => m.RDPlanRoutine,
                  ),
              },
              {
                path: "planned-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/planned-routines/planned-routines").then(
                    (m) => m.PlannedRoutines,
                  ),
              },
              {
                path: "planned-routine-detail",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/planned-routine-detail/planned-routine-detail").then(
                    (m) => m.PlannedRoutineDetailComponent,
                  ),
              },
              {
                path: "close-routine",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/close-routine/close-routine").then(
                    (m) => m.CloseRoutine,
                  ),
              },
              {
                path: "raise-FUSS",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/raise-fuss/raise-fuss").then(
                    (m) => m.RaiseFUSS,
                  ),
              },
              {
                path: "history/equipment-routine-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/equipment-routine-history/equipment-routine-history").then(
                    (m) => m.EquipmentRoutineHistoryComponent,
                  ),
              },
              {
                path: "history/search-equipment-running-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/search-equipment-running-history/search-equipment-running-history").then(
                    (m) => m.SearchEquipmentRunningHistory,
                  ),
              },
              {
                path: "history/slip-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/slip-history/slip-history").then(
                    (m) => m.SlipHistory,
                  ),
              },
              {
                path: "history/close-routine-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/close-routine-history/close-routine-history").then(
                    (m) => m.CloseRoutineHistory,
                  ),
              },
              {
                path: "reports",
                redirectTo: "reports/weekly",
                pathMatch: "full",
              },
              {
                path: "reports/weekly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/fortnightly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/monthly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/six-monthly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/yearly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "about",
                loadComponent: () =>
                  import("./Pages/op-maintenance/about/about").then((m) => m.About),
              },
            ],
          },

          {
            path: "op-utilities",
            children: [
              { path: "", redirectTo: "onboard-pol-status", pathMatch: "full" },
              {
                path: "onboard-pol-status",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/op-utilities/onboard-pol-status/onboard-pol-status").then(
                    (m) => m.OnboardPolStatus,
                  ),
              },
              {
                path: "slip-calculator",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/slip-calculator/slip-calculator").then(
                    (m) => m.SlipCalculator,
                  ),
              },
              {
                path: "endurance-calculator",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/op-utilities/endurance-calculator/endurance-calculator").then(
                    (m) => m.EnduranceCalculator,
                  ),
              },
            ],
          },
          {
            path: "about",
            loadComponent: () =>
              import("./Pages/op-maintenance/about/about").then((m) => m.About),
          },
          {
            path: "endurance-calculator",
            loadComponent: () =>
              import("./Pages/op-maintenance/endurance-calculator/endurance-calculator").then(
                (m) => m.EnduranceCalculator,
              ),
          },
          {
            path: "other-utilities",
            loadComponent: () =>
              import("./Pages/op-maintenance/other-utilities/other-utilities").then(
                (m) => m.OtherUtilities,
              ),
          },
          {
            path: "ra-signal",
            loadComponent: () =>
              import("./Pages/op-maintenance/ra-signal/ra-signal").then((m) => m.RaSignal),
          },
          {
            path: "gd-report",
            loadComponent: () =>
              import("./Pages/op-maintenance/gd-report/gd-report").then((m) => m.GdReport),
          },
          {
            path: "maintenance-periods",
            loadComponent: () =>
              import("./Pages/op-maintenance/maintenance-periods/maintenance-periods").then(
                (m) => m.MaintenancePeriods,
              ),
          },
          {
            path: "e-logbooks",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import('./shared/components/development-in-progress/development-in-progress').then((m) => m.DevelopmentInProgress)
              },
            ],
          },
          {
            path: ":child/:tab",
            loadComponent: () =>
              import("./Pages/operational-maintenance/operational-maintenance").then(
                (m) => m.OperationalMaintenance,
              ),
          },

        ],
      },






      /* Superseded by the new "op-maintenance" route above (./Pages/operational-maintenance) — kept for reference, not removed.
      {
        path: "op-maintenance",
        children: [
          {
            path: "",
            redirectTo: "defect/overview",
            pathMatch: "full",
          },

          {
            path: "defect/overview",
            loadComponent: () =>
              import("./Pages/op-maintenance/op-maintenance-dashboard/op-maintenance-dashboard").then(
                (m) => m.OpMaintenanceDashboard,
              ),
          },
          {
            path: "dashboard",

            loadComponent: () =>
              import("./shared/components/under-construction/under-construction").then(
                (m) => m.UnderConstruction,
              ),
          },

          {
            path: "action",
            loadComponent: () =>
              import("./Pages/op-maintenance/action-forms/action-forms").then(
                (m) => m.ActionForms,
              ),
          },
          {
            path: "history",
            loadComponent: () =>
              import("./Pages/op-maintenance/history/history.component").then(
                (m) => m.HistoryComponent,
              ),
          },
          {
            path: "history/view-action",
            loadComponent: () =>
              import("./Pages/op-maintenance/history/view-action/view-action.component").then(
                (m) => m.HistoryViewActionComponent,
              ),
          },

          {
            path: "references",
            loadComponent: () =>
              import("./Pages/op-maintenance/references/masters/masters.component").then(
                (m) => m.MastersComponent,
              ),
          },

          {
            path: "references/masters",
            loadComponent: () =>
              import("./Pages/op-maintenance/references/masters/masters.component").then(
                (m) => m.MastersComponent,
              ),
          },

          {
            path: "references/exported-files",
            loadComponent: () =>
              import("./Pages/op-maintenance/references/exported-files/exported-files.component").then(
                (m) => m.ExportedFilesComponent,
              ),
          },
          {
            path: "close-defects/:id",
            loadComponent: () =>
              import("./Pages/op-maintenance/defect-closure-details/defect-closure-details").then(
                (m) => m.DefectClosureDetails,
              ),
          },
          {
            path: "open-darts",
            loadComponent: () =>
              import("./Pages/op-maintenance/open-defects/open-defects").then(
                (m) => m.OpenDefects,
              ),
          },
          {
            path: "closed-darts",
            loadComponent: () =>
              import("./Pages/op-maintenance/closed-darts/closed-darts").then(
                (m) => m.ClosedDarts,
              ),
          },
          {
            path: "ra-defect-list",
            loadComponent: () =>
              import("./Pages/op-maintenance/ra-defect-list/ra-defect-list").then(
                (m) => m.RaDefectList,
              ),
          },
          {
            path: "complete-dart-list",
            loadComponent: () =>
              import("./Pages/op-maintenance/complete-dart-list/complete-dart-list").then(
                (m) => m.CompleteDartList,
              ),
          },
          {
            path: "create-dlii",
            loadComponent: () =>
              import("./Pages/op-maintenance/create-dliii/create-dliii").then(
                (m) => m.CreateDLIII,
              ),
          },
          {
            path: "create-ra",
            loadComponent: () =>
              import("./Pages/op-maintenance/create-ra/create-ra").then(
                (m) => m.CreateRA,
              ),
          },
          {
            path: "routine",
            children: [
              {
                path: "",
                redirectTo: "dashboard",
                pathMatch: "full",
              },
              {
                path: "dashboard",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/ems-dashboard/ems-dashboard").then(
                    (m) => m.EmsDashboard,
                  ),
              },
              {
                path: "unique-maintop-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/routines-dashboard").then(
                    (m) => m.RoutinesDashboard,
                  ),
              },
              {
                path: "slip-calculator",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/slip-calculator/slip-calculator").then(
                    (m) => m.SlipCalculator,
                  ),
              },
              {
                path: "r-h-based-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/r-h-routines/r-h-routines").then(
                    (m) => m.RHRoutines,
                  ),
              },
              {
                path: "calendar-based-routing",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/calendar-based-routines/calendar-based-routines").then(
                    (m) => m.CalendarBasedRoutines,
                  ),
              },
              {
                path: "equipment-due-for-ABER",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/equipment-due-for-aber/equipment-due-for-aber").then(
                    (m) => m.EquipmentDueForABER,
                  ),
              },
              {
                path: "FUSS-triger-list",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/fuss-triger-list/fuss-triger-list").then(
                    (m) => m.FUSSTrigerList,
                  ),
                children: [],
              },
              {
                path: "close-fuss",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/fuss-triger-list/close-fuss/close-fuss").then(
                    (m) => m.CloseFUSS,
                  ),
              },
              {
                path: "fuss-triger-raise-fuss",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/fuss-triger-list/fuss-triger-raise-fuss/fuss-triger-raise-fuss").then(
                    (m) => m.FUSSTrigerRaiseFuss,
                  ),
              },
              {
                path: "search-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/search-routines/search-routines").then(
                    (m) => m.SearchRoutines,
                  ),
              },
              {
                path: "reference",
                redirectTo: "references/masters",
                pathMatch: "full",
              },
              {
                path: "references/masters",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/references/references").then(
                    (m) => m.References,
                  ),
              },
              {
                path: "references/exported-files",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/references/exported-files-dl1/exported-files-dl1").then(
                    (m) => m.ExportedFilesDl1,
                  ),
              },
              {
                path: "references/about-us",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/references/about-us/about-us").then(
                    (m) => m.AboutUs,
                  ),
              },
              {
                path: "dl1-generation/search-refit",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/dl1-generation/search-refit-routines/search-refit-routines").then(
                    (m) => m.SearchRefitRoutines,
                  ),
              },
              {
                path: "dl1-generation/refit-routine-detail",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/dl1-generation/refit-routine-detail/refit-routine-detail").then(
                    (m) => m.RefitRoutineDetailComponent,
                  ),
              },
              {
                path: "dl1-generation/generate",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/dl1-generation/generate-dl1/generate-dl1").then(
                    (m) => m.GenerateDl1,
                  ),
              },
              {
                path: "due-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/search-routines/routine-due/routine-due").then(
                    (m) => m.RoutineDue,
                  ),
              },
              {
                path: "r-d-plan-routine",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/search-routines/r-d-plan-routine/r-d-plan-routine").then(
                    (m) => m.RDPlanRoutine,
                  ),
              },
              {
                path: "planned-routines",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/planned-routines/planned-routines").then(
                    (m) => m.PlannedRoutines,
                  ),
              },
              {
                path: "planned-routine-detail",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/planned-routine-detail/planned-routine-detail").then(
                    (m) => m.PlannedRoutineDetailComponent,
                  ),
              },
              {
                path: "close-routine",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/close-routine/close-routine").then(
                    (m) => m.CloseRoutine,
                  ),
              },
              {
                path: "raise-FUSS",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/raise-fuss/raise-fuss").then(
                    (m) => m.RaiseFUSS,
                  ),
              },
              {
                path: "history/equipment-routine-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/equipment-routine-history/equipment-routine-history").then(
                    (m) => m.EquipmentRoutineHistoryComponent,
                  ),
              },
              {
                path: "history/search-equipment-running-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/search-equipment-running-history/search-equipment-running-history").then(
                    (m) => m.SearchEquipmentRunningHistory,
                  ),
              },
              {
                path: "history/slip-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/slip-history/slip-history").then(
                    (m) => m.SlipHistory,
                  ),
              },
              {
                path: "history/close-routine-history",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/history/close-routine-history/close-routine-history").then(
                    (m) => m.CloseRoutineHistory,
                  ),
              },
              {
                path: "reports",
                redirectTo: "reports/weekly",
                pathMatch: "full",
              },
              {
                path: "reports/weekly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/fortnightly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/monthly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/six-monthly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "reports/yearly",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/reports/reports.component").then(
                    (m) => m.ReportsComponent,
                  ),
              },
              {
                path: "about",
                loadComponent: () =>
                  import("./Pages/op-maintenance/about/about").then((m) => m.About),
              },
            ],
          },
          {
            path: "op-utilities",
            children: [
              { path: "", redirectTo: "onboard-pol-status", pathMatch: "full" },
              {
                path: "onboard-pol-status",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/op-utilities/onboard-pol-status/onboard-pol-status").then(
                    (m) => m.OnboardPolStatus,
                  ),
              },
              {
                path: "slip-calculator",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/slip-calculator/slip-calculator").then(
                    (m) => m.SlipCalculator,
                  ),
              },
              {
                path: "endurance-calculator",
                loadComponent: () =>
                  import("./Pages/op-maintenance/routines-dashboard/op-utilities/endurance-calculator/endurance-calculator").then(
                    (m) => m.EnduranceCalculator,
                  ),
              },
            ],
          },
          {
            path: "about",
            loadComponent: () =>
              import("./Pages/op-maintenance/about/about").then((m) => m.About),
          },
          {
            path: "endurance-calculator",
            loadComponent: () =>
              import("./Pages/op-maintenance/endurance-calculator/endurance-calculator").then(
                (m) => m.EnduranceCalculator,
              ),
          },
          {
            path: "other-utilities",
            loadComponent: () =>
              import("./Pages/op-maintenance/other-utilities/other-utilities").then(
                (m) => m.OtherUtilities,
              ),
          },
          {
            path: "ra-signal",
            loadComponent: () =>
              import("./Pages/op-maintenance/ra-signal/ra-signal").then((m) => m.RaSignal),
          },
          {
            path: "gd-report",
            loadComponent: () =>
              import("./Pages/op-maintenance/gd-report/gd-report").then((m) => m.GdReport),
          },
          {
            path: "maintenance-periods",
            loadComponent: () =>
              import("./Pages/op-maintenance/maintenance-periods/maintenance-periods").then(
                (m) => m.MaintenancePeriods,
              ),
          },
          {
            path: "e-logbooks",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import('./shared/components/development-in-progress/development-in-progress').then((m) => m.DevelopmentInProgress)
              },
            ],
          },
        ],
      },
      */
      {
        path: "inventory",
        children: [
          { path: "", redirectTo: "ship-inventory-obs", pathMatch: "full" },
          {
            path: "ship-inventory-obs",
            loadChildren: () =>
              import("./Pages/inventory/ship-inventory-obs/ship-inventory-obs.routes").then(
                (m) => m.SHIP_INVENTORY_OBS_ROUTES,
              ),
          },
          {
            path: "shore-inventory-mo",
            loadChildren: () =>
              import("./Pages/inventory/shore-inventory-mo/shore-inventory-mo.routes").then(
                (m) => m.SHORE_INVENTORY_MO_ROUTES,
              ),
          },
          {
            path: "shore-inventory-wed",
            loadChildren: () =>
              import("./Pages/inventory/shore-inventory-wed/shore-inventory-wed.routes").then(
                (m) => m.SHORE_INVENTORY_WED_ROUTES,
              ),
          },
        ],
      },
      {
        path: "ship-returns",
        loadChildren: () =>
          import("./Pages/ship-returns/ship-returns.routes").then(
            (m) => m.SHIP_RETURNS_ROUTES
          ),
      },
      // {
      //   path: "dynamic-form/:formName",
      //   loadComponent: () =>
      //     import(
      //       "./Pages/ship-returns/Trial-INT/angulerFromconverting/dynamic-form-host.component"
      //     ).then((m) => m.DynamicFormHostComponent),
      // },
      {
        path: "other-utilities",
        loadChildren: () =>
          import("./Modules/other-utilities/other-utilities.routes").then(
            (m) => m.OTHER_UTILITIES_ROUTES
          ),
      },
      {
        path: "activity",
        children: [
          { path: "", redirectTo: "dashboard", pathMatch: "full" },
          {
            path: "dashboard",
            children: [
              {
                path: "",
                loadComponent: () =>
                  import(
                    "./Pages/operational-coordination-planner/pages/dashboard/dashboard.component"
                  ).then((m) => m.OcPlannerDashboardComponent),
              },
              {
                path: "equipment-status",
                loadComponent: () =>
                  import(
                    "./Pages/operational-coordination-planner/pages/equipment-status/equipment-status.component"
                  ).then((m) => m.EquipmentStatusComponent),
              },
            ],
          },
          {
            path: "calendar",
            data: { initialView: "Month" },
            loadComponent: () =>
              import(
                "./Pages/operational-coordination-planner/pages/planner/planner.component"
              ).then((m) => m.OperationalCoordinationPlannerComponent),
          },
        ],
      },
      {
        path: "dss",
        children: [
          { path: "", redirectTo: "overview", pathMatch: "full" },

        ],
      },
      {
        path: "Reports",
        children: [
          { path: "", redirectTo: "overview", pathMatch: "full" },

        ],
      },
      {
        path: "KPIs",
        children: [
          { path: "", redirectTo: "overview", pathMatch: "full" },

        ],
      },
      {
        path: "kms",
        children: [
          { path: "", redirectTo: "dashboard/overview", pathMatch: "full" },
          {
            path: "dashboard",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import("./Modules/kms/dashboard/kms-dashboard").then(
                    (m) => m.KmsDashboard,
                  ),
              },
            ],
          },
          {
            path: "technical",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import("./Modules/kms/technical/kms-technical").then(
                    (m) => m.KmsTechnical,
                  ),
              },
            ],
          },
          {
            path: "certificates",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import("./Modules/kms/certificates/kms-certificates").then(
                    (m) => m.KmsCertificates,
                  ),
              },
            ],
          },
          {
            path: "in-mail",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import("./Modules/kms/in-mail/kms-in-mail").then(
                    (m) => m.KmsInMail,
                  ),
              },
            ],
          },
          {
            path: "out-mail",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import("./Modules/kms/out-mail/kms-out-mail").then(
                    (m) => m.KmsOutMail,
                  ),
              },
            ],
          },
          {
            path: "sharepoint",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import("./Modules/kms/sharepoint/kms-sharepoint").then(
                    (m) => m.KmsSharepoint,
                  ),
              },
            ],
          },
          {
            path: "category-master",
            children: [
              { path: "", redirectTo: "overview", pathMatch: "full" },
              {
                path: "overview",
                loadComponent: () =>
                  import("./Modules/kms/category-master/kms-category-master").then(
                    (m) => m.KmsCategoryMaster,
                  ),
              },
            ],
          },
        ],
      },
      {
        path: "Audit_and_Logs",
        children: [
          { path: "", redirectTo: "overview", pathMatch: "full" },

        ],
      },
      {
        path: "Help",
        children: [
          { path: "", redirectTo: "overview", pathMatch: "full" },

        ],
      },
      {
        path: "administration",
        children: [
          { path: "", redirectTo: "overview", pathMatch: "full" },

        ],
      },
      {
        path: "refit_dashboard",
        loadChildren: () =>
          import("./Pages/dl-monitoring/dl-monitoring.routes").then(
            (m) => m.DL_MONITORING_ROUTES
          ),
      },
      {
        path: "profile",
        loadComponent: () =>
          import("./Modules/profile/profile").then((m) => m.Profile),
      }
    ],
  },
  {
    path: "other-utilities/:sub/:page",
    redirectTo: "afterAuth/other-utilities/:sub/:page",
  },
  {
    path: "other-utilities/:sub",
    redirectTo: "afterAuth/other-utilities/:sub",
  },
  {
    path: "other-utilities",
    redirectTo: "afterAuth/other-utilities",
  },
  {
    path: "**",
    loadComponent: () =>
      import("./shared/components/under-construction/under-construction").then(
        (m) => m.UnderConstruction,
      ),
  },
];
