import { Routes } from "@angular/router";

export const SHIP_RETURNS_ROUTES: Routes = [
  {
    path: "",
    redirectTo: "srar/dashboard",
    pathMatch: "full",
  },
  {
    path: "overview",
    loadComponent: () =>
      import("./overview/overview.component").then(
        (m) => m.ShipReturnsOverviewComponent
      ),
  },
  {
    path: "srar",
    loadComponent: () =>
      import("./srar/srar.component").then((m) => m.SrarComponent),
    children: [
      {
        path: "",
        redirectTo: "dashboard",
        pathMatch: "full",
      },
      {
        path: "dashboard",
        loadComponent: () =>
          import("./srar/dashboard/srar-dashboard.component").then(
            (m) => m.SrarDashboardComponent
          ),
      },
      {
        path: "transaction",
        loadComponent: () =>
          import("./srar/transaction/srar-transaction.component").then(
            (m) => m.SrarTransactionComponent
          ),
      },
      {
        path: "history",
        loadComponent: () =>
          import("./srar/history/srar-history.component").then(
            (m) => m.SrarHistoryComponent
          ),
      },
      {
        path: "masters",
        loadComponent: () =>
          import("./srar/masters/srar-masters.component").then(
            (m) => m.SrarMastersComponent
          ),
      },
    ],
  },
  {
    path: "trial-returns",
    loadComponent: () =>
      import("./trial-returns/trial-returns.component").then(
        (m) => m.TrialReturnsComponent
      ),
    children: [
      {
        path: "",
        redirectTo: "dashboard",
        pathMatch: "full",
      },
      {
        path: "dashboard",
        loadComponent: () =>
          import("./trial-returns/dashboard/trial-dashboard.component").then(
            (m) => m.TrialDashboardComponent
          ),
      },
      {
        path: "transaction",
        loadComponent: () =>
          import("./trial-returns/transaction/trial-transaction.component").then(
            (m) => m.TrialTransactionComponent
          ),
      },
      {
        path: "inbox",
        loadComponent: () =>
          import("./trial-returns/inbox/trial-inbox.component").then(
            (m) => m.TrialInboxComponent
          ),
      },
      {
        path: "outbox",
        loadComponent: () =>
          import("./trial-returns/outbox/trial-outbox.component").then(
            (m) => m.TrialOutboxComponent
          ),
      },
      {
        path: "history",
        loadComponent: () =>
          import("./trial-returns/history/trial-history.component").then(
            (m) => m.TrialHistoryComponent
          ),
      },
      {
        path: "aboutus",
        loadComponent: () =>
          import("./trial-returns/aboutus/trial-aboutus.component").then(
            (m) => m.TrialAboutusComponent
          ),
      },
    ],
  },
  {
    path: "returns",
    loadComponent: () =>
      import("./Trial-INT/returns-container/returns-container").then(
        (m) => m.ReturnsContainerComponent
      ),
    children: [
      {
        path: "",
        redirectTo: "transaction",
        pathMatch: "full",
      },
      {
        path: "dashboard",
        loadComponent: () =>
          import("./Trial-INT/returns-dashboard/returns-dashboard").then(
            (m) => m.ReturnsDashboardComponent
          ),
      },
      {
        path: "transaction",
        loadComponent: () =>
          import("./Trial-INT/Transaction/transaction-return/transaction-return").then(
            (m) => m.TransactionReturn
          ),
      },
      {
        path: "mtu/e-pol",
        loadComponent: () =>
          import("./Trial-INT/Transaction/e-pol/e-pol").then(
            (m) => m.EPol
          ),
      },
      {
        path: "master/equipments",
        loadComponent: () =>
          import("./Trial-INT/master/equipments/equipments").then(
            (m) => m.Equipments
          ),
      },
      {
        path: "master/equipment-oil-mapping",
        loadComponent: () =>
          import("./Trial-INT/master/equipment-oil-mapping/equipment-oil-mapping").then(
            (m) => m.EquipmentOilMapping
          ),
      },
      {
        path: "master/satellite-units",
        loadComponent: () =>
          import("./Trial-INT/master/satellite-units/satellite-units").then(
            (m) => m.SatelliteUnits
          ),
      },
      {
        path: "master/sections",
        loadComponent: () =>
          import("./Trial-INT/master/sections/sections").then(
            (m) => m.Sections
          ),
      },
      {
        path: "master/tools",
        loadComponent: () =>
          import("./Trial-INT/master/tools/tool").then(
            (m) => m.Tool
          ),
      },
      {
        path: "master/trial-types",
        loadComponent: () =>
          import("./Trial-INT/master/trial-types/trial-types").then(
            (m) => m.TrialTypes
          ),
      },
      {
        path: "dynamic-form/:formName",
        loadComponent: () =>
          import(
            "./Trial-INT/angulerFromconverting/dynamic-form-host.component"
          ).then((m) => m.DynamicFormHostComponent),
      }
    ],
  },
  {
    path: "trials",
    loadComponent: () =>
      import("./Trial-INT/trials-container/trials-container").then(
        (m) => m.TrialsContainerComponent
      ),
    children: [
      {
        path: "",
        redirectTo: "transaction",
        pathMatch: "full",
      },
      {
        path: "dashboard",
        loadComponent: () =>
          import("./Trial-INT/trials-dashboard/trials-dashboard").then(
            (m) => m.TrialsDashboardComponent
          ),
      },
      {
        path: "transaction",
        loadComponent: () =>
          import("./Trial-INT/Transaction/transaction-trail/transaction-trail").then(
            (m) => m.TransactionTrail
          ),
      },
      {
        path: "master/equipments",
        loadComponent: () =>
          import("./Trial-INT/master/equipments/equipments").then(
            (m) => m.Equipments
          ),
      },
      {
        path: "master/equipment-oil-mapping",
        loadComponent: () =>
          import("./Trial-INT/master/equipment-oil-mapping/equipment-oil-mapping").then(
            (m) => m.EquipmentOilMapping
          ),
      },
      {
        path: "master/satellite-units",
        loadComponent: () =>
          import("./Trial-INT/master/satellite-units/satellite-units").then(
            (m) => m.SatelliteUnits
          ),
      },
      {
        path: "master/sections",
        loadComponent: () =>
          import("./Trial-INT/master/sections/sections").then(
            (m) => m.Sections
          ),
      },
      {
        path: "master/tools",
        loadComponent: () =>
          import("./Trial-INT/master/tools/tool").then(
            (m) => m.Tool
          ),
      },
      {
        path: "master/trial-types",
        loadComponent: () =>
          import("./Trial-INT/master/trial-types/trial-types").then(
            (m) => m.TrialTypes
          ),
      },
      {
        path: "dynamic-form/:formName",
        loadComponent: () =>
          import(
            "./Trial-INT/angulerFromconverting/dynamic-form-host.component"
          ).then((m) => m.DynamicFormHostComponent),
      },
      // Legacy HITU route slugs. Each route uses the Trial-INT-compatible
      // host, so all forms share E-POL's prefill/save/submit API behavior.
      ...[
        "hvac-phase1",
        "hvac-phase2",
        "water-tight-door",
        "water-tight-hatches",
        "emergency-escape-hatch",
        "helo-traversing-system",
        "achor-capstan",
        "mooring-warping-capstan",
        "store-passenger-ammunition-lift",
        "ras-cargo-winch",
        "float-worthiness-ship",
        "boat-davit-crane",
        "citadel-data-feeding",
        "air-pressure-hose-test",
        "accommodation-ladder",
        "checks-of-iccp-system",
        "stp-vts",
        "structural-helo-hanger",
        "submarine-door",
        "submarine-ohmi",
        "puwhi",
        "iuwhi",
        "fuwhi",
        "rss",
        "prewetting-trials",
        "lst-lpd",
        "tow-worthiness-submarine",
        "hanger-shutter",
        "paint-inspection",
        "underwater-tanks",
        "float-worthiness-submarine",
        "tow-worthiness-ship",
        "boat-trials-data",
        "hello-deck-flight-friction",
        "ship-ohmi",
        "vkd-fire-screen-driver",
        "vkd-manual-lifting-transporting-device",
        "vkd-ras-winch",
        "vkd-sac-blade-replacement-device",
        "vkd-lifting-transporting-device",
        "garbage-compactor",
        "vkt-crane",
        "vkt-movable-hight-point",
        "grease-separator",
      ].map((path) => ({
        path: `hitu/${path}`,
        loadComponent: () =>
          import("./Trial-INT/Transaction/hitu/hitu-form").then(
            (m) => m.HituForm,
          ),
      })),
      {
        path: "hitu/:formName",
        loadComponent: () =>
          import(
            "./Trial-INT/angulerFromconverting/dynamic-form-host.component"
          ).then((m) => m.DynamicFormHostComponent),
      },
      {
        path: "hitu",
        loadComponent: () =>
          import("./Trial-INT/hitu-module/hitu-module.component").then(
            (m) => m.HituModuleComponent,
          ),
      },
    ],
  },
  {
    path: "hull-returns",
    loadComponent: () =>
      import("./hull-returns/hull-returns.component").then(
        (m) => m.HullReturnsComponent
      ),
  },
  {
    path: "other-returns",
    loadComponent: () =>
      import("./other-returns/other-returns.component").then(
        (m) => m.OtherReturnsComponent
      ),
  },
];
