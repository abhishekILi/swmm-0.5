import {
  ACTIVITY_PLANNER_ICON,
  ADMIN_ICON,
  BOX_ICON,
  DASHBOARD_GRID_ICON,
  DEFECT_ICON,
  // HELP_ICON, // unused while Help is hidden from the sidebar
  HOME_ICON,
  HOTWORK_ICON,
  INVENTORY_ICON,
  KMS_ICON,
  // KPI_ICON, // unused while KPIs is hidden from the sidebar
  E_LOGBOOKS_ICON,
  OP_MAINT_ICON,
  OP_UTILITIES_ICON,
  // REPORTS_ICON, // unused while Reports is hidden from the sidebar
  ROUTINES_ICON,
  SHIP_CREW_ICON,
  SHIP_INVENTORY_OBS_ICON,
  SHIP_RETURNS_ICON,
  SRAR_ICON,
  TAG_IN_TAG_OUT_ICON,
  TRIAL_RETURNS_ICON,
  HULL_RETURNS_ICON,
  OTHER_RETURNS_ICON,
  OTHER_UTILITIES_ICON,
  SHORE_INVENTORY_MO_ICON,
  SHORE_INVENTORY_WED_ICON,
} from "../../constants/sidebar-icons";
import { HeaderConfig, NavigationModule } from "./navigation.model";
import {
  createHeader,
  createModule,
  createSidebar,
  createSidebarItem,
  createSidebarWithChildren,
} from "./navigation.builders";

const SECTIONS = {
  operationsMaintenance: "Operations & Maintenance",
  inventoryReturns: "Inventory & Returns",
  utilitiesCrew: "Utilities & Crew",
  admin: "Admin",
} as const;

export const DEFAULT_HEADER: HeaderConfig = createHeader({
  dlGeneration: { enabled: false, route: null },
});

const createHomeHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Dashboard", route: "overview" },
    actions: { label: "Divisional Organisation", route: "divisional-organisation" },
    reports: { label: "Know Your Regulators", route: "know-your-regulators" },
    dlGeneration: { enabled: true, label: "Gallery", route: "gallery" },
    insights: { enabled: false, route: null },
    configuration: {
      label: "References",
      route: "references/master",
      children: [
        createSidebarItem({ id: "master", label: "Master", route: "references/master" }),
      ],
    },
  });

const createRefitHeader = (): HeaderConfig =>
  createHeader({
    overview: {
      label: "Dashboard",
      route: "overview",
    },
    configuration: {
      enabled: false,
      route: null
    },
    actions: {
      label: "DL Monitoring",
      route: "tracking/DL1",
      children: [
        { id: "dl-type", label: "DL I Monitoring", route: "tracking/DL1" },
        { id: "import", label: "DL II/ AWRF/ SDL Monitoring", route: "tracking/DL2" },
        { id: "tracking", label: "DL III Monitoring", route: "tracking/DL3" },
      ],
    },
    reports: {
      label: "History",
      route: "history",
    },
    dlGeneration: { enabled: false, route: null },
    insights: {
      enabled: true,
      label: "References",
      route: "references",
      children: [
        { id: "master", label: "Master", route: "master" },
      ],
    },
  })

/** KMS repurposes the 6 generic header tabs (the 5 shared ones plus the opt-in
 * `references` slot) as its own screen switcher — Dashboard / Technical Manuals /
 * Certificates / Correspondences▾ / Share Point / References▾ — matching the
 * reference Django app's single-header-block layout exactly, six distinct tabs
 * included. Every tab/child route is marked `absoluteRoute` since they jump between
 * unrelated screens rather than switching sub-views of one screen (the default
 * behavior other modules still use).
 *
 * Key-to-label mapping deliberately doesn't follow each key's usual meaning —
 * it's picked to land tabs in the right left-to-right order given the header's
 * fixed rendering sequence (`HeaderTabKeys` in header.ts): overview, actions,
 * reports, dlGeneration, insights, references, configuration. `dlGeneration` is
 * left disabled (reserved for Op. Maintenance's Routines sub-header elsewhere),
 * so `configuration` ends up last, correctly holding References▾. */
const createKmsHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Dashboard", route: "dashboard/overview", absoluteRoute: true },
    actions: { label: "Technical Manuals", route: "technical/overview", absoluteRoute: true },
    reports: { label: "Certificates", route: "certificates/overview", absoluteRoute: true },
    dlGeneration: { enabled: false, route: null },
    insights: {
      label: "Correspondences",
      route: "in-mail/overview",
      absoluteRoute: true,
      children: [
        createSidebarItem({ id: "in-mail", label: "In Mail", route: "in-mail/overview", absoluteRoute: true }),
        createSidebarItem({ id: "out-mail", label: "Out Mail", route: "out-mail/overview", absoluteRoute: true }),
      ],
    },
    references: {
      enabled: true,
      label: "Share Point",
      route: "sharepoint/overview",
      absoluteRoute: true,
    },
    configuration: {
      label: "References",
      route: "category-master/overview",
      absoluteRoute: true,
      children: [
        createSidebarItem({ id: "category-master", label: "Category Master", route: "category-master/overview", absoluteRoute: true }),
      ],
    },
  });


const createOcPlannerHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Dashboard", route: "dashboard" },
    configuration: { label: "Ship Activity Calendar", route: "calendar" },
    actions: { enabled: false, route: null },
    reports: { enabled: false, route: null },
    dlGeneration: { enabled: false, route: null },
    insights: { enabled: false, route: null },
  });



const createDefectHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Overview", route: "defect/overview" },
    configuration: { label: "Configuration", route: "defect/configuration" },
    actions: { label: "Actions", route: "defect/actions" },
    reports: { label: "Reports", route: "defect/reports" },
    insights: { label: "Insights", route: "defect/insights" },

  });

const createRoutineHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Dashboard", route: "dashboard" },
    actions: {
      label: "Routines",
      route: "search-routines",
      children: [
        createSidebarItem({ id: "search-routines", label: "Search / Plan Routines", route: "search-routines" }),
        createSidebarItem({ id: "planned-routines", label: "Planned Routines", route: "planned-routines" }),
        createSidebarItem({ id: "fuss-triger-list", label: "Raised FUSS", route: "FUSS-triger-list" }),
      ],
    },
    reports: {
      label: "Reports",
      route: "reports/weekly",
      children: [
        createSidebarItem({ id: "reports-weekly", label: "Weekly Maintenance Plan", route: "reports/weekly" }),
        createSidebarItem({ id: "reports-fortnightly", label: "Fortnightly Maintenance Plan", route: "reports/fortnightly" }),
        createSidebarItem({ id: "reports-monthly", label: "Monthly Maintenance Plan", route: "reports/monthly" }),
        createSidebarItem({ id: "reports-six-monthly", label: "Six Monthly Maintenance Plan", route: "reports/six-monthly" }),
        createSidebarItem({ id: "reports-yearly", label: "Annual Maintenance Plan", route: "reports/yearly" }),
      ],
    },
    dlGeneration: {
      enabled: true,
      label: "DL I Generation",
      route: "dl1-generation/search-refit",
      children: [
        createSidebarItem({ id: "dl1-search-refit", label: "Search Refit Routines", route: "dl1-generation/search-refit" }),
        createSidebarItem({ id: "dl1-generate", label: "Generate DL 1", route: "dl1-generation/generate" }),
      ],
    },
    insights: {
      label: "History",
      route: "history/equipment-routine-history",
      children: [
        createSidebarItem({ id: "equipment-routine-history", label: "Equipment Routine History", route: "history/equipment-routine-history" }),
        createSidebarItem({ id: "search-equipment-running-history", label: "Equipment Running History", route: "history/search-equipment-running-history" }),
        createSidebarItem({ id: "slip-history", label: "Slip History", route: "history/slip-history" }),
        createSidebarItem({ id: "close-routine-history", label: "Close Routine History", route: "history/close-routine-history" }),
      ],
    },
    configuration: {
      label: "References",
      route: "references/masters",
      children: [
        createSidebarItem({ id: "masters", label: "Masters", route: "references/masters" }),
        createSidebarItem({ id: "exported-files", label: "Exported files DL 1", route: "references/exported-files" }),
        createSidebarItem({ id: "about", label: "About Op. Maintenance", route: "references/about-us" }),
      ],
    },
  });

const createOpUtilitiesHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Onboard POL Status", route: "onboard-pol-status" },
    actions: { label: "Slip Calculator", route: "slip-calculator" },
    configuration: { label: "Endurance Calculator", route: "endurance-calculator" },
    reports: { enabled: false, route: null },
    dlGeneration: { enabled: false, route: null },
    insights: { enabled: false, route: null },
  });

const createSrarHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Dashboard", route: "dashboard" },
    configuration: { label: "Masters", route: "masters" },
    actions: { label: "Transaction", route: "transaction" },
    reports: { label: "History", route: "history" },
    dlGeneration: { enabled: false, route: null },
    insights: { enabled: false, route: null },
  });

const TRIAL_INT_MASTER_CHILDREN = [
  { id: "master-equipments", label: "Equipments", route: "master/equipments" },
  { id: "master-equipment-oil-mapping", label: "Equipment Oil Mapping", route: "master/equipment-oil-mapping" },
  { id: "master-satellite-units", label: "Satellite Units", route: "master/satellite-units" },
  { id: "master-sections", label: "Sections", route: "master/sections" },
  { id: "master-tools", label: "Tools", route: "master/tools" },
  { id: "master-trial-types", label: "Trial Types", route: "master/trial-types" },
];

const createTrialReturnsHeader = (): HeaderConfig =>
  createHeader({
    overview: {
      enabled: false, route: null
    },
    actions: {
      label: "Transaction",
      route: "transaction",
    },
    configuration: {
      label: "Masters",
      route: "master/equipments",
      children: TRIAL_INT_MASTER_CHILDREN,
    },
    reports: { enabled: false, route: null },
    dlGeneration: { enabled: false, route: null },
    insights: { enabled: false, route: null },
  });
const createTrialsHeader = (): HeaderConfig => createTrialReturnsHeader();

const createHotworkHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Dashboard", route: "dashboard" },
    actions: {
      label: "Transactions",
      route: "manage-hotwork",
      children: [
        { id: "raise-hotwork-req", label: "Raise Hotwork Requisition", route: "raise-requisition" },
        { id: "req-approval-pending", label: "Requisitions - Approval Pending", route: "requisitions-approval-pending" },
        { id: "monitor-approved-req", label: "Monitor Approved Requisitions", route: "monitor-approved-requisitions" },
      ],
    },
    reports: {
      label: "Action",
      route: "inbox",
      children: [
        { id: "inbox", label: "Inbox", route: "inbox" },
        { id: "outbox", label: "Outbox", route: "outbox" },
      ],
    },
    dlGeneration: { enabled: false, route: null },
    insights: { label: "History", route: "history" },
    configuration: { enabled: false, route: null },
  });

const createTagInOutHeader = (): HeaderConfig =>
  createHeader({
    overview: { label: "Dashboard", route: "dashboard" },
    actions: { label: "Tag Out", route: "tag-out" },
    reports: { label: "Tag In", route: "tag-in" },
    dlGeneration: {
      enabled: true,
      label: "Approval",
      route: "tag-out-approval",
      children: [
        { id: "tag-out-approval", label: "Approve Tag Out", route: "tag-out-approval" },
        { id: "tag-in-approval", label: "Approve Tag In", route: "tag-in-approval" },
      ],
    },
    insights: { label: "History", route: "history" },
    configuration: { enabled: false, route: null },
  });

const createHullReturnsHeader = (): HeaderConfig =>
  createHeader({
    overview: { enabled: false, route: null },
    configuration: { enabled: false, route: null },
    actions: { enabled: false, route: null },
    reports: { enabled: false, route: null },
    dlGeneration: { enabled: false, route: null },
    insights: { enabled: false, route: null },

  });
export const NAVIGATION_CONFIG: NavigationModule[] = [
  createModule({
    id: "home",
    title: "Home",
    section: "",
    baseRoute: "home",
    sidebar: createSidebar({
      id: "home",
      label: "Home",
      route: "overview",
      icon: HOME_ICON,
    }),
    header: createHomeHeader(),
    headers: {},
  }),
  createModule({
    id: "activity",
    title: "Activity Planner",
    section: SECTIONS.operationsMaintenance,
    baseRoute: "activity",
    sidebar: createSidebar({
      id: "activity",
      label: "Activity Planner",
      route: "dashboard",
      icon: ACTIVITY_PLANNER_ICON,
    }),
    header: createOcPlannerHeader(),
    headers: {},
  }),
  // createModule({
  //   id: "divisional_Organisation",
  //   title: "Divisional Organisation",
  //   section: SECTIONS.operations,
  //   baseRoute: "divisional_Organisation",
  //   sidebar: createSidebar({
  //     id: "divisional_Organisation",
  //     label: "Divisional Organisation",
  //     route: "overview",
  //     icon: USERS_ICON,
  //   }),
  // }),
  createModule({
    id: "ship",
    title: "Ship Configuration",
    section: SECTIONS.operationsMaintenance,
    baseRoute: "ship",
    sidebar: createSidebar({
      id: "ship",
      label: "Ship Configuration",
      route: "overview",
      icon: BOX_ICON,
    }),
    header: createHeader({
      dlGeneration: { enabled: false, route: null },

    }),
    headers: {},
  }),
  createModule({
    id: "op-maintenance",
    section: SECTIONS.operationsMaintenance,
    title: "Operational Maintenance",
    baseRoute: "op-maintenance",
    sidebar: createSidebarWithChildren({
      id: "op-maintenance",
      label: "Operations Maintenance",
      route: "defect/overview",
      icon: OP_MAINT_ICON,
      children: [
        createSidebarItem({ id: "defect", label: "Defect", route: "overview", icon: DEFECT_ICON }),
        createSidebarItem({ id: "routine", label: "Routines", route: "dashboard", icon: ROUTINES_ICON }),
        createSidebarItem({ id: "op-utilities", label: "Op Utilities", route: "onboard-pol-status", icon: OP_UTILITIES_ICON }),
        createSidebarItem({ id: "e-logbooks", label: "e-Logbooks", icon: E_LOGBOOKS_ICON }),
      ],
    }),
    header: createDefectHeader(),
    headers: {
      defect: createDefectHeader(),
      routine: createRoutineHeader(),
      "op-utilities": createOpUtilitiesHeader(),
    },
    headerNestedKeys: ["routine", "op-utilities"],
    headerTabOrders: {
      defect: ["overview", "configuration", "actions", "reports", "insights"],
    },
  }),
  createModule({
    id: "inventory",
    title: "Inventory",
    section: SECTIONS.inventoryReturns,
    baseRoute: "inventory",
    sidebar: createSidebarWithChildren({
      id: "inventory",
      label: "Inventory",
      icon: INVENTORY_ICON,
      children: [
        createSidebarItem({
          id: "ship-inventory-obs",
          label: "Ship Inventory - OBS",
          icon: SHIP_INVENTORY_OBS_ICON,
        }),
        createSidebarItem({
          id: "shore-inventory-mo",
          label: "Shore Inventory - MO",
          icon: SHORE_INVENTORY_MO_ICON,
        }),
        createSidebarItem({
          id: "shore-inventory-wed",
          label: "Shore Inventory - WED",
          icon: SHORE_INVENTORY_WED_ICON,
        }),
      ],
    }),
  }),
  createModule({
    id: "refit_dashboard",
    title: "Refit Maintenance",
    section: SECTIONS.operationsMaintenance,
    baseRoute: "refit_dashboard",
    sidebar: createSidebar({
      id: "refit_dashboard",
      label: "Refit Maintenance",
      route: "overview",
      icon: DASHBOARD_GRID_ICON,
    }),
    header: createRefitHeader(),
  }),
  createModule({
    id: "ship-returns",
    title: "Ship Returns",
    section: SECTIONS.inventoryReturns,
    baseRoute: "ship-returns",
    header: createSrarHeader(),
    headers: {
      "srar": createSrarHeader(),
      "returns": createTrialReturnsHeader(),
      "trials": createTrialsHeader(),
      "hull-returns": createHullReturnsHeader(),
      "other-returns": createHullReturnsHeader(),
    },
    sidebar: createSidebarWithChildren({
      id: "ship-returns",
      label: "Ship Returns",
      icon: SHIP_RETURNS_ICON,
      children: [
        createSidebarItem({ id: "srar", label: "SRAR", route: "srar", icon: SRAR_ICON }),
        createSidebarItem({ id: "returns", label: "Trial Returns", route: "returns", icon: TRIAL_RETURNS_ICON }),
        createSidebarItem({ id: "trials", label: "Trials", route: "trials", icon: TRIAL_RETURNS_ICON }),
        createSidebarItem({ id: "hull-returns", label: "Hull Returns", route: "hull-returns", icon: HULL_RETURNS_ICON }),
        createSidebarItem({ id: "other-returns", label: "Other Returns", route: "other-returns", icon: OTHER_RETURNS_ICON }),
      ],
    }),
  }),
  createModule({
    id: "other-utilities",
    title: "Other Utilities",
    section: SECTIONS.utilitiesCrew,
    baseRoute: "other-utilities",
    header: createHotworkHeader(),
    headers: {
      "hotwork": createHotworkHeader(),
      "tag-in-tag-out": createTagInOutHeader(),
    },
    sidebar: createSidebarWithChildren({
      id: "other-utilities",
      label: "Other Utilities",
      icon: OTHER_UTILITIES_ICON,
      children: [
        createSidebarItem({ id: "hotwork", label: "HotWork", route: "hotwork/dashboard", icon: HOTWORK_ICON }),
        createSidebarItem({ id: "tag-in-tag-out", label: "Tag In / Tag Out", route: "tag-in-tag-out/dashboard", icon: TAG_IN_TAG_OUT_ICON }),
      ],
    }),
  }),
  createModule({
    id: "kms",
    title: "Knowledge Management",
    section: SECTIONS.utilitiesCrew,
    baseRoute: "kms",
    sidebar: createSidebar({
      id: "kms",
      label: "KMS",
      tooltip: "Knowledge Management System",
      route: "dashboard/overview",
      icon: KMS_ICON,
    }),
    header: createKmsHeader(),
  }),
  createModule({
    id: "Ship_Crew_and_HR",
    title: "Ship Crew",
    section: SECTIONS.utilitiesCrew,
    baseRoute: "Ship_Crew_and_HR",
    sidebar: createSidebar({
      id: "Ship_Crew_and_HR",
      label: "Ship Crew",
      route: "dashboard",
      icon: SHIP_CREW_ICON,
    }),
  }),
  createModule({
    id: "Administration",
    title: "Users",
    section: SECTIONS.admin,
    baseRoute: "administration",
    sidebar: createSidebar({
      id: "user",
      label: "Users",
      route: "overview",
      icon: ADMIN_ICON,
    }),
    roles: ["admin"],
  }),
  // createModule({
  //   id: "Audit_and_Logs",
  //   title: "Audit & Logs",
  //   section: SECTIONS.admin,
  //   baseRoute: "Audit & Logs",
  //   sidebar: createSidebar({
  //     id: "Audit_and_Logs",
  //     label: "Audit & Logs",
  //     route: "overview",
  //     icon: AUDIT_ICON,
  //   }),
  //   roles: ["admin"],
  // }),
  // createModule({
  //   id: "Help",
  //   title: "Help",
  //   section: SECTIONS.admin,
  //   baseRoute: "Help",
  //   sidebar: createSidebar({
  //     id: "Help",
  //     label: "Help",
  //     route: "overview",
  //     icon: HELP_ICON,
  //   }),
  // }),
];
