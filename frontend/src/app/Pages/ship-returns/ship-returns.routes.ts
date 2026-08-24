import { Routes } from "@angular/router";

function loadHituComponent(path: string): Promise<any> {
  switch (path) {
    case "hvac-phase1":
      return import("./Trial-INT/Transaction/hitu/HituForms/hvac-phase-1-add/hvac-phase-1-add.component").then((m) => m.HvacPhase1AddComponent);
    case "hvac-phase2":
      return import("./Trial-INT/Transaction/hitu/HituForms/hvac-phase-2-add/hvac-phase-2-add.component").then((m) => m.HvacPhase2AddComponent);
    case "water-tight-door":
      return import("./Trial-INT/Transaction/hitu/HituForms/water-tight-Door-add/water-tight-door.component").then((m) => m.WaterTightDoorAdd);
    case "water-tight-hatches":
      return import("./Trial-INT/Transaction/hitu/HituForms/water-tight-hatches-add/water-tight-hatches-add.component").then((m) => m.WaterTightHatchesAdd);
    case "emergency-escape-hatch":
      return import("./Trial-INT/Transaction/hitu/HituForms/emergency-escape-hatches-add/emergency-escape-hatches-add.component").then((m) => m.EmergencyEscapeHatchesAdd);
    case "helo-traversing-system":
      return import("./Trial-INT/Transaction/hitu/HituForms/helo-traversing-sys-port-stbd-add/helo-traversing-sys-port-stbd-add.component").then((m) => m.HeloTraversingSysPortStbdAddComponent);
    case "achor-capstan":
      return import("./Trial-INT/Transaction/hitu/HituForms/anchor-capstan-add/anchor-capstan-add.component").then((m) => m.AnchorCapstanAdd);
    case "mooring-warping-capstan":
      return import("./Trial-INT/Transaction/hitu/HituForms/mooring-capstan-warping-capstan-port-stbd-add/mooring-capstan-warping-capstan-port-stbd-add.component").then((m) => m.MooringCapstanWarpingCapstan);
    case "store-passenger-ammunition-lift":
      return import("./Trial-INT/Transaction/hitu/HituForms/store-passenger-ammunition-lift-data-feeding-add/store-passenger-ammunition-lift-data-feeding-add.component").then((m) => m.StorePassengerAmmunitionLiftDataFeedingAdd);
    case "ras-cargo-winch":
      return import("./Trial-INT/Transaction/hitu/HituForms/RAS-cargo-winch-data-feeding-add/ras-cargo-winch-data-feeding-add.component").then((m) => m.RASCargoWinchAdd);
    case "float-worthiness-ship":
      return import("./Trial-INT/Transaction/hitu/HituForms/float-worthiness/float-worthiness-add.component").then((m) => m.FloatWorthiness);
    case "boat-davit-crane":
      return import("./Trial-INT/Transaction/hitu/HituForms/boat-davit-crane/boat-davit-crane").then((m) => m.BoatDavitCrane);
    case "air-pressure-hose-test":
      return import("./Trial-INT/Transaction/hitu/HituForms/air-pressure-hose-test/air-pressure-hose-test").then((m) => m.AirPressureHoseTest);
    case "accommodation-ladder":
      return import("./Trial-INT/Transaction/hitu/HituForms/accommodation-ladder/accommodation-ladder").then((m) => m.AccommodationLadder);
    case "checks-of-iccp-system":
      return import("./Trial-INT/Transaction/hitu/HituForms/checks-of-iccp-system/checks-of-iccp-system").then((m) => m.ChecksOfIccpSystem);
    case "stp-vts":
      return import("./Trial-INT/Transaction/hitu/HituForms/stp-vts-data-feeding/stp-vts-data-feeding").then((m) => m.STPVTSDataFeeding);
    case "structural-helo-hanger":
      return import("./Trial-INT/Transaction/hitu/HituForms/structural-helo-hanger/structural-helo-hanger").then((m) => m.StructuralHeloHanger);
    case "submarine-door":
      return import("./Trial-INT/Transaction/hitu/HituForms/submarine-door/submarine-door").then((m) => m.SubmarineDoor);
    case "submarine-ohmi":
      return import("./Trial-INT/Transaction/hitu/HituForms/submarine-ohmi/submarine-ohmi").then((m) => m.SubmarineOHMI);
    case "puwhi":
      return import("./Trial-INT/Transaction/hitu/HituForms/puwhi/puwhi").then((m) => m.PUWHI);
    case "iuwhi":
      return import("./Trial-INT/Transaction/hitu/HituForms/iuwhi/iuwhi").then((m) => m.IUWHI);
    case "fuwhi":
      return import("./Trial-INT/Transaction/hitu/HituForms/fuwhi/fuwhi").then((m) => m.FUWHI);
    case "rss":
      return import("./Trial-INT/Transaction/hitu/HituForms/rss/rss").then((m) => m.RSS);
    case "prewetting-trials":
      return import("./Trial-INT/Transaction/hitu/HituForms/prewetting-trials/prewetting-trials").then((m) => m.PrewettingTrials);
    case "lst-lpd":
      return import("./Trial-INT/Transaction/hitu/HituForms/lst-lpd/lst-lpd").then((m) => m.LSTLPD);
    case "tow-worthiness-submarine":
      return import("./Trial-INT/Transaction/hitu/HituForms/tow-worthiness/tow-worthiness").then((m) => m.TowWorthiness);
    case "hanger-shutter":
      return import("./Trial-INT/Transaction/hitu/HituForms/hanger-shutter/hanger-shutter").then((m) => m.HangerShutter);
    case "paint-inspection":
      return import("./Trial-INT/Transaction/hitu/HituForms/paint-inspection/paint-inspection").then((m) => m.PaintInspection);
    case "underwater-tanks":
      return import("./Trial-INT/Transaction/hitu/HituForms/underwater-tanks/underwater-tanks").then((m) => m.UnderwaterTanks);
    case "float-worthiness-submarine":
      return import("./Trial-INT/Transaction/hitu/HituForms/float-worthiness-submarine/float-worthiness-submarine").then((m) => m.FloatWorthinessSubmarine);
    case "tow-worthiness-ship":
      return import("./Trial-INT/Transaction/hitu/HituForms/tow-worthiness-ship/tow-worthiness-ship").then((m) => m.TowWorthinessShip);
    case "boat-trials-data":
      return import("./Trial-INT/Transaction/hitu/HituForms/boat-trials-data/boat-trials-data").then((m) => m.BoatTrialsData);
    case "hello-deck-flight-friction":
      return import("./Trial-INT/Transaction/hitu/HituForms/hello-deck-flight-friction/hello-deck-flight-friction").then((m) => m.HelloDeckFlightFriction);
    case "ship-ohmi":
      return import("./Trial-INT/Transaction/hitu/HituForms/ship-ohmi/ship-ohmi").then((m) => m.ShipOhmi);
    case "vkd-fire-screen-driver":
      return import("./Trial-INT/Transaction/hitu/HituForms/vkd-fire-screen-driver/vkd-fire-screen-driver").then((m) => m.VkdFireScreenDriver);
    case "vkd-manual-lifting-transporting-device":
      return import("./Trial-INT/Transaction/hitu/HituForms/vkd-manual-lifting-transporting-device/vkd-manual-lifting-transporting-device").then((m) => m.VkdManualLiftingTransportingDevice);
    case "vkd-ras-winch":
      return import("./Trial-INT/Transaction/hitu/HituForms/vkd-ras-winch/vkd-ras-winch").then((m) => m.VkdRasWinch);
    case "vkd-sac-blade-replacement-device":
      return import("./Trial-INT/Transaction/hitu/HituForms/vkd-sac-blade-replacement-device/vkd-sac-blade-replacement-device").then((m) => m.VkdSacBladeReplacementDevice);
    case "vkd-lifting-transporting-device":
      return import("./Trial-INT/Transaction/hitu/HituForms/vkd-lifting-transporting-device/vkd-lifting-transporting-device").then((m) => m.VkdLiftingTransportingDevice);
    case "garbage-compactor":
      return import("./Trial-INT/Transaction/hitu/HituForms/garbage-compactor/garbage-compactor").then((m) => m.GarbageCompactor);
    case "vkt-crane":
      return import("./Trial-INT/Transaction/hitu/HituForms/vkt-crane/vkt-crane").then((m) => m.VktCrane);
    case "vkt-movable-hight-point":
      return import("./Trial-INT/Transaction/hitu/HituForms/vkt-movable-hight-point/vkt-movable-hight-point").then((m) => m.VktMovableHightPoint);
    case "grease-separator":
      return import("./Trial-INT/Transaction/hitu/HituForms/grease-separator/grease-separator").then((m) => m.GreaseSeparator);
    default:
      return import("./Trial-INT/angulerFromconverting/dynamic-form-host.component").then((m) => m.DynamicFormHostComponent);
  }
}

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
      {
        path: "etma/load-trial-proforma-da",
        loadComponent: () =>
          import(
            "./Trial-INT/Transaction/etma/load-trial-proforma-da/load-trial-proforma-da"
          ).then((m) => m.LoadTrialProformaDa),
      },
      {
        path: "etma/load-trial-proformaGtg",
        loadComponent: () =>
          import(
            "./Trial-INT/Transaction/etma/load-trial-proforma-gtg/load-trial-proforma-gtg"
          ).then((m) => m.LoadTrialProformaGtg),
      },
      {
        path: "nec/nec-part-a-induction-survey-report",
        loadComponent: () =>
          import(
            "./Trial-INT/Transaction/nec/part-a-induction-survey-report/part-a-induction-survey-report"
          ).then((m) => m.PartAInductionSurveyReport),
      },
      {
        path: "nec/nec-part-b-induction-survey-report",
        loadComponent: () =>
          import(
            "./Trial-INT/Transaction/nec/part-b-induction-survey-report/part-b-induction-survey-report"
          ).then((m) => m.PartBInductionSurveyReport),
      },
      // Legacy HITU route slugs. Each route uses the Trial-INT-compatible
      // host, so all forms share E-POL's prefill/save/submit API behavior.
      {
        path: "hitu/hvac-phase1/:trialId",
        loadComponent: () =>
          import(
            "./Trial-INT/Transaction/hitu/HituForms/hvac-phase-1-add/hvac-phase-1-add.component"
          ).then((m) => m.HvacPhase1AddComponent),
      },
      {
        path: "hitu/citadel-data-feeding",
        loadComponent: () =>
          import(
            "./Trial-INT/Transaction/hitu/HituForms/citadel-data-feeding/citadel-data-feeding"
          ).then((m) => m.CitadelDataFeeding),
      },
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
        loadComponent: () => loadHituComponent(path),
      })),
      {
        path: "hitu/:formName",
        loadComponent: () =>
          import(
            "./Trial-INT/angulerFromconverting/dynamic-form-host.component"
          ).then((m) => m.DynamicFormHostComponent),
      }
      
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
