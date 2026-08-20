import { environment } from "../../../../environments/environment";
import { InventoryTabItem } from "../shared/models/inventory-nav.model";

const OBS_BASE = "/afterAuth/inventory/ship-inventory-obs";

/** Real static files under `frontend/public/assests/` — served directly by Angular from the app's
 * own origin at `/assests/...` (`angular.json`'s `public` asset glob copies the folder as-is,
 * typo and all — the same path every other `/assests/...` reference in this codebase already
 * uses, e.g. `home.ts`'s dashboard images), so a bare relative href is correct here (unlike the
 * backend-origin PDF link below). The filename in each `externalHref` must match a real file in
 * `public/assests/` exactly — a mismatch 404s and the browser just navigates to the dead link
 * instead of downloading anything. */

/** Real static file — `backend/media/obs/osms_documentation.pdf` — served by Django's `static()`
 * helper at `MEDIA_URL` (`swmm/urls.py`, unconditional, not gated behind `DEBUG`). Must be an
 * absolute backend-origin URL: a bare `/media/...` href resolves against the Angular dev server's
 * own origin (which has no such file) instead of the API host. */
const SPARES_IMPORT_RULES_PDF_URL = `${environment.apiUrl}media/obs/osms_documentation.pdf`;

export const SHIP_INVENTORY_OBS_TABS: InventoryTabItem[] = [
  { label: "Dashboard", route: `${OBS_BASE}/dashboard` },
  {
    label: "Ship Inventory",
    children: [
      { label: "Search / Add Spare", route: `${OBS_BASE}/search` },
      { label: "Maintainer Spare Request - Routine DART", route: `${OBS_BASE}/requisitions/routine` },
      { label: "Maintainer Spare Request - Defect DART", route: `${OBS_BASE}/requisitions/defect` },
    ],
  },
  { label: "Return Spares", route: `${OBS_BASE}/return` },
  {
    label: "Internal Transactions",
    children: [
      { label: "Due for Survey - P / R Items", route: `${OBS_BASE}/transactions/survey` },
      { label: "Due for Demand - Cons. Items", route: `${OBS_BASE}/transactions/demand` },
      { label: "Due for IIF - Not INcatted Items", route: `${OBS_BASE}/transactions/iif` },
    ],
  },
  { label: "History", route: `${OBS_BASE}/history` },
  {
    label: "References",
    children: [
      { label: "Spares Import Rules", externalHref: SPARES_IMPORT_RULES_PDF_URL },
      {
        label: "Download Template Excel Sheets",
        children: [
          { label: "D787J", externalHref: "/assests/D787J_import_spares.xlsx" },
          { label: "Other Authorites", externalHref: "/assests/Ship_Inventory_Template_Excel_Sheet_MO_Items.xlsx" },
        ],
      },
      { label: "Masters", route: `${OBS_BASE}/references/masters` },
      { label: "About Ship Inventory", route: `${OBS_BASE}/references/about` },
    ],
  },
];
