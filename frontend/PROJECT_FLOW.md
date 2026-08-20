# SWMM Frontend - Project Flow Documentation

## Overview
Angular 22 single-page application for **Ship-Wide Maintenance Management (SWMM)** system.
- Standalone-component architecture
- Signal-based state management
- Tailwind CSS styling
- Lazy-loaded standalone components and route configurations; legacy NgModule files still exist in DL Monitoring

---

## Tech Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| Angular | 22.0.5 | Framework (mostly standalone components; legacy DL Monitoring NgModules remain) |
| TypeScript | 6.0.3 | Strict mode enabled |
| State | Angular Signals | `signal`, `computed` (no NgRx) |
| Styling | Tailwind CSS 3.4 | Utility-first + global component classes |
| Data Grid | ag-grid-community 35 | `AllCommunityModule` registered globally |
| Charts | ECharts 6 (ngx-echarts), ng2-charts | Gauge, donut, bar charts |
| Toasts | ngx-sonner | Global toaster via `NotificationService` |
| Icons | @lucide/angular v1.x | By-name via global registry |

---

## Project Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── Core/
│   │   │   ├── layout/
│   │   │   │   ├── main-layout/      # Authenticated shell
│   │   │   │   └── outer-layout/     # Public shell
│   │   │   ├── component/            # App chrome (header, sidebar, footer, loader, alert, breadcrum)
│   │   │   ├── config/navigation/    # Config-driven nav system
│   │   │   ├── constants/            # Icons, enums
│   │   │   ├── services/             # Cross-cutting services
│   │   │   │   ├── auth/             # Auth service
│   │   │   │   ├── user/             # User service
│   │   │   │   ├── master/           # Master data
│   │   │   │   ├── theme/            # Theme service
│   │   │   │   ├── notification/     # Toast store
│   │   │   │   ├── network/          # HTTP interceptors, call wrapper
│   │   │   │   └── common/           # HTTP feedback, network status
│   │   │   └── auth/guards/          # Route guards (authGuard, guestGuard)
│   │   ├── Pages/                    # Feature modules (one folder per domain)
│   │   │   ├── home/
│   │   │   ├── op-maintenance/
│   │   │   ├── inventory/
│   │   │   ├── ship-returns/
│   │   │   ├── kms/
│   │   │   ├── operational-coordination-planner/
│   │   │   ├── dl-monitoring/
│   │   │   ├── ship-crew/
│   │   │   └── ...
│   │   ├── Modules/                  # Feature areas and route configurations
│   │   │   ├── landing/
│   │   │   ├── kms/
│   │   │   └── other-utilities/
│   │   ├── shared/                   # Reusable UI components and directives
│   │   │   ├── components/
│   │   │   │   ├── data-grid/        # ag-grid wrapper
│   │   │   │   ├── modal/
│   │   │   │   ├── kpi-card/
│   │   │   │   ├── icon/
│   │   │   │   ├── input-field/
│   │   │   │   └── ...
│   │   │   └── app-* wrappers
│   │   ├── services/network/call.ts  # Central HTTP/domain API service (Call service)
│   │   ├── app.ts                    # Root component
│   │   ├── app.routes.ts             # Route definitions
│   │   ├── app.config.ts             # Providers bootstrap
│   │   └── app.html/css              # Root template/styles
│   ├── environments/                 # environment.ts, .dev, .uat, .prod
│   ├── assets/json/                  # Static JSON data files
│   └── styles.css                    # Global Tailwind + component classes
```

---

## Bootstrap Flow
```mermaid
main.ts
  → bootstrapApplication(App, appConfig)
      → app.config.ts (providers: router, HTTP + interceptors, animations, toastr, charts, ag-grid, echarts)
      → App (app.ts)
          → OnInit: Auth.initializeSession() → restores token/user from localStorage or attempts refresh
          → User.getLoggedInUserDetails() → loads user profile
```

---

## Layout System

### OuterLayout (`/`)
- Public routes: `/landing`
- Sets `data-theme="dark"` on `<html>`
- `guestGuard` exists but is currently not attached to `/landing`.

### MainLayout (`/afterAuth/**`)
- Authenticated shell with:
  - `Header` (top nav tabs)
  - `Sidebar` (config-driven navigation)
  - `Breadcrum`
  - `RouterOutlet` (page content)
  - `Footer`
- Special handling for inventory modules with custom top nav (`InventoryTabNav`)

---

## Routing Architecture (`app.routes.ts`)

### Route Groups
| Path | Module | Children |
|------|--------|----------|
| `/` | Landing | - |
| `/afterAuth/home` | Home | overview, daily-orders, divisional-org, regulators, gallery, references |
| `/afterAuth/ship/:tab` | Ship Config | SFD shell |
| `/afterAuth/op-maintenance` | Op Maintenance | defect, routine, op-utilities, e-logbooks, ra-signal, gd-report, maintenance-periods |
| `/afterAuth/inventory` | Inventory | ship-inventory-obs, shore-inventory-mo, shore-inventory-wed |
| `/afterAuth/ship-returns` | Ship Returns | srar, returns, trials, hull-returns, other-returns |
| `/afterAuth/kms` | Knowledge Mgmt | dashboard, technical, certificates, in-mail, out-mail, sharepoint, category-master |
| `/afterAuth/activity` | Activity Planner | dashboard, calendar |
| `/afterAuth/refit_dashboard` | Refit Maintenance | DL monitoring |
| `/afterAuth/other-utilities` | Other Utilities | hotwork, tag-in-tag-out |
| `/afterAuth/Ship_Crew_and_HR` | Ship Crew | (lazy routes) |
| `/afterAuth/administration` | Admin | users (admin only) |
| `/afterAuth/profile` | Profile | - |

### Route Features
- Feature pages are generally lazy-loaded via `loadComponent: () => import(...)`.
- Several route groups are lazy-loaded via `loadChildren`, including Ship Crew, Inventory, Ship Returns, Other Utilities and DL Monitoring.
- **Auth guard** on `/afterAuth` parent
- **Default redirects** to `overview` or `dashboard`
- Root wildcard fallback → `UnderConstruction`; there is no separate wildcard child inside `/afterAuth`.

---

## Authentication & Session

### Auth Service (`Core/services/auth/auth.ts`)
```typescript
// Token handling
- accessToken: signal plus localStorage persistence (`access_token`)
- refreshToken: signal plus localStorage persistence (`refresh_token`); requests also use `withCredentials`
- Session initialization restores access token/user, but currently does not restore the refresh token signal before refresh.

// Key methods
loginUser(cred)           → POST /api/v1/user/token/
refreshAccessToken()      → POST /api/v1/user/token/access/ (deduped via in-flight promise)
logout()                  → POST /api/v1/user/logout/ + clearClientSession()
initializeSession()       → Restore from localStorage OR refresh token
getuserDetails()          → Fetch user profile
```

### Interceptors (`Core/services/interceptor/interceptor.ts`)
| Interceptor | Purpose |
|-------------|---------|
| `authInterceptor` | Adds `withCredentials: true` + `Bearer` header |
| `refreshTokenInterceptor` | On 401 → refresh token → retry once (skips auth/landing URLs) |
| `loaderInterceptor` | Full-screen loader on mutating requests |
| `feedbackInterceptor` | Auto toasts on success/error for POST/PUT/PATCH/DELETE |

### Guards (`Core/auth/guards/`)
- `authGuard` → Requires session, else redirect to `/landing`
- `guestGuard` → Redirects authenticated users to `/afterAuth/home`; currently defined but not enabled on the landing route.

---

## Navigation System (`Core/config/navigation/`)

### Config-Driven Approach
```typescript
// navigation.config.ts
export const NAVIGATION_CONFIG: NavigationModule[] = [
  createModule({
    id: "op-maintenance",
    title: "Operational Maintenance",
    section: "Operations & Maintenance",
    baseRoute: "op-maintenance",
    sidebar: createSidebarWithChildren({...}),  // Tree with children
    header: createDefectHeader(),                // Default header
    headers: {                                   // Per-child headers
      defect: createDefectHeader(),
      routine: createRoutineHeader(),
      "op-utilities": createOpUtilitiesHeader(),
    },
    headerNestedKeys: ["routine", "op-utilities"],
    headerTabOrders: { defect: ["overview", "configuration", "actions", "reports", "insights"] }
  }),
  // ... other modules
]
```

### Header Tab Keys (Fixed Order)
`overview` → `actions` → `reports` → `dlGeneration` → `insights` → `references` → `configuration`

### Sidebar Icons
Defined in `Core/constants/sidebar-icons.ts` as Lucide **names** (not SVGs), consumed by nav config.

---

## HTTP Layer

### Central Service: `Call` (`services/network/call.ts`)
- Wraps `HttpClient` with generic `get/post/put/delete`
- Base URL from `environment.apiUrl` (resolved at runtime via `api-url.ts`)
- Most shared endpoints and many domain endpoints live here
- Some GET calls fall back to `dummy-responses.ts` when the backend is unavailable
- Legacy phase-2 authentication calls also exist here

### Feature API Services
Larger features own dedicated services (e.g., `planner-api.service.ts`)

### Response Typing
- Co-located `*.model.ts` interfaces
- Legacy calls may use `any` (don't expand)

---

## State Management
- **Signals** are the primitive (`signal`, `computed`)
- **Shared state**: `LandingPageService` and `User` service
- **Feature stores**: e.g., `planner.store.ts` (`providedIn: 'root'`)
- **Async**: `firstValueFrom(observable)` → `async/await` in services

---

## Shared Components (`shared/`)

### Data Display
| Component | Selector | Purpose |
|-----------|----------|---------|
| Data Grid | `app-data-grid` | ag-grid wrapper (pagination, selection, custom cells) |
| KPI Card | `app-kpi-card` | Dashboard metric card |
| Stat Card | `app-stat-card` | Simple stat display |
| Info Card | `app-info-card` | Informational card |
| Donut Chart | `app-donut-chart` | Circular progress |
| Speedometer | `app-speedometer-card` | Gauge chart |
| Stacked Bar | `app-stacked-bar-chart` | Stacked bar chart |

### Form Inputs
- `app-input-field`, `app-select-input`, `app-radio-input`
- `app-textarea-input`, `app-file-input`
- `app-date-picker`, `app-date-wheel-picker`, `app-custom-calendar`

### Layout/Navigation
- `app-modal` (size variants: sm/md/lg/xl)
- `app-button`, `app-dropdown`, `app-search`, `app-tabs`
- `app-breadcrumb`, `app-export-actions`, `app-export-menu`

### Placeholders
- `DevelopmentInProgress` → Unbuilt routes
- `UnderConstruction` → Fallback routes

### Additional Reusable Components
- `app-panel-card`, `app-gauge-chart`, `app-pill-toggle`
- `app-toolbar-search`, `app-export-toolbar`, `app-dynamic-field`
- `app-detail-drawer`, `app-form-modal`, `app-status-chip`
- `app-select-cards`, `app-rich-text-editor`, `app-image-preview`
- `app-count-up` directive and multiple grid cell renderers

---

## Icon System (Lucide)

### Usage (Preferred)
```html
<app-icon name="filter" variant="accent" [size]="16" />
```
Variants: `default | inherit | muted | accent | success | warning | danger`

### Low-Level
```html
<svg lucideIcon="filter" [class.icon--accent]="isActive"></svg>
```

### Registration
Add to `provideLucideIcons([...])` in `app.config.ts` — **required before use**

### Nav Icons
Defined in `sidebar-icons.ts` as names, rendered via `<app-icon>` in sidebar

### Theming
Global token customization in `styles.css` → `[data-theme]` blocks (ICON SYSTEM section)

---

## Commands
```bash
npm start         # ng serve — dev server on http://localhost:4200
npm run build     # Production build
npm run build:dev # Dev environment build
npm run build:uat # UAT environment build
npm run build:prod# Production build
npm run watch     # Rebuild on change
 npm test          # Vitest-based Angular unit tests; Jasmine/Karma packages remain installed
npm run lint      # angular-eslint
```

---

## Conventions

### Components
- `standalone: true` with explicit `imports` array
- `CommonModule` for `*ngIf`/`*ngFor`, `FormsModule` for `ngModel`
- Selectors: `app-` prefix, kebab-case
- Separate files: `templateUrl`/`styleUrl` (not inline)

### Dependency Injection
- Prefer `inject()` function over constructor injection
- Mark injected fields `private readonly`

### Naming
| Pattern | Example |
|---------|---------|
| Angular 20 default (most files) | `dashboard.ts` → class `Dashboard` |
| Newer/feature code | `dashboard.component.ts` → class `DashboardComponent` |
| Models | `*.model.ts` co-located with feature |
| Services | `*.service.ts` |
| Stores | `*.store.ts` |

### TypeScript
- Strict mode: respect it
- Avoid `any` for new code
- Type API responses with `*.model.ts` interfaces

### Styling
- Tailwind utility-first
- Reuse global classes from `styles.css` (`@layer components`)
- Theme tokens in `tailwind.config.js`: `accent-blue #1D96E9`, fonts Inter/Poppins
- Match neighboring component style format (`.css` or `.scss`)

---

## Do / Don't

### Do
- Add shared API endpoints to `Call` service
- Add page routes as lazy `loadComponent` entries
- Register nav entries in `navigation.config.ts`
- Use signals for state + `firstValueFrom` for HTTP
- Check `shared/` before building new UI

### Don't
- Introduce new NgModules; legacy DL Monitoring NgModules still exist and should be migrated before enforcing this rule
- Add new token storage patterns; current auth implementation persists tokens in localStorage and should be standardized before changing this rule
- Hardcode API base URL (use `environment.apiUrl`)
- Bypass interceptors
- Duplicate existing shared components
- Use `toast` from ngx-sonner directly (use `NotificationService`)

---

## Key Entry Points
| File | Purpose |
|------|---------|
| `src/main.ts` | Bootstrap |
| `src/app/app.config.ts` | All providers |
| `src/app/app.routes.ts` | Route definitions |
| `src/app/app.ts` | Root component + session init |
| `src/app/Core/config/navigation/navigation.config.ts` | Nav structure |
| `src/app/Core/services/auth/auth.ts` | Auth logic |
| `src/app/services/network/call.ts` | Central HTTP and domain API service |
| `src/styles.css` | Global styles + theme tokens |
| `tailwind.config.js` | Tailwind theme config |

---

## Application Bug List (Source Checked)

The following are behavioral/runtime bugs or high-risk flow defects found during source review. These are separate from documentation-only differences.

## Critical Architecture and Error Risks

These issues should be handled before treating the application as production-safe.

### P0 - Security and Authentication
- **Production phase-2 API is hardcoded to plain HTTP and a private IP.** Every environment resolves phase-2 APIs to `http://172.16.40.87:8080/`. In production this risks credentials/tokens being sent without TLS and may fail outside the internal network. File: `src/environments/api-url.ts:21-27`.
- **Authentication has two unrelated token contracts.** The primary flow uses `access_token`/`refresh_token`/`user_data`, while phase-2 interception reads `localStorage.user`. This can authenticate one backend while silently failing another. Files: `src/app/Core/services/auth/auth.ts:44-97`, `src/app/Core/services/interceptor/interceptor.ts:37-50`, `src/app/services/network/call.ts:85-132`.
- **Authorization is not enforced at route level for administration.** Navigation visibility is not access control. A user who knows the URL can still attempt direct access because `/afterAuth/administration` has no admin guard. Files: `src/app/app.routes.ts:28-30, 1191-1196`, `src/app/Core/config/navigation/access-control.service.ts`.

### P0 - Error Visibility and Data Integrity
- **Backend errors can be converted into fake success data.** `Call.get()` catches all errors and returns dummy data when available. This can hide 401, 403, 404 and 500 responses, display stale/demo data, and prevent the UI from entering its error state. File: `src/app/services/network/call.ts:833-843`.
- **Login errors are swallowed in the legacy phase-2 flow.** `Call.logincall()` catches the error, returns `of(null)`, and performs an internal subscription. `Auth.loginUser()` can then continue through the separate primary flow while phase-2 failure is only stored in a signal. Files: `src/app/services/network/call.ts:85-106`, `src/app/Core/services/auth/auth.ts:44-50, 79-113`.
- **Startup errors are not contained.** `App.ngOnInit()` awaits `User.getLoggedInUserDetails()` without a catch or error state. A profile API failure can leave the application partially initialized with no controlled recovery flow. Files: `src/app/app.ts:24-30`, `src/app/Core/services/user/user.ts:20-29`.
- **Corrupt browser storage can break all requests or startup.** Unprotected `JSON.parse()` calls process `user` and `user_data`. A malformed value can throw before the request reaches the backend. Files: `src/app/Core/services/interceptor/interceptor.ts:38-40`, `src/app/Core/services/auth/auth.ts:165-168`.

### P1 - Architecture That Creates Regressions
- **`Call` is a God service.** It owns generic HTTP helpers, domain APIs for many modules, dummy fallbacks, phase-2 login/refresh/logout, localStorage mutation and error state. A change in one feature can affect unrelated authentication or API behavior. File: `src/app/services/network/call.ts`.
- **Authentication responsibilities are split across `Auth`, `Call`, `AppService`, and `LandingPageService`.** Login, refresh, logout, token state and persistence do not have one source of truth. Files: `src/app/Core/services/auth/auth.ts`, `src/app/services/network/call.ts`, `src/app/Core/services/app/app.service.ts`, `src/app/Modules/landing/landing-page.service.ts`.
- **Session initialization is duplicated.** `App` initializes the session, `authGuard` can initialize it again, and `guestGuard` can initialize it again when enabled. Concurrent navigation can produce duplicate refresh/master-data requests. Files: `src/app/app.ts:24-30`, `src/app/Core/auth/guards/auth-guard.ts:5-26`.
- **Legacy and standalone routing coexist without one boundary.** DL Monitoring has legacy NgModule routing while the rest of the app uses standalone route configurations. This increases the risk of duplicate route definitions and inconsistent providers. Files: `src/app/Pages/dl-monitoring/dl-monitoring.module.ts`, `src/app/Pages/dl-monitoring/dl-monitoring-routing.module.ts`, `src/app/app.routes.ts:1198-1202`.
- **Route access and navigation configuration can drift.** Navigation is configured separately from `app.routes.ts`; hidden/disabled navigation does not imply a blocked route, and several navigation entries point to incomplete routes. Files: `src/app/Core/config/navigation/navigation.config.ts`, `src/app/app.routes.ts`.
- **Runtime API configuration is not environment-isolated.** `environment.dev.ts`, `environment.uat.ts`, and `environment.prod.ts` all call runtime URL resolvers, while the phase-2 resolver always returns the same fixed address. Deployment mistakes can send UAT or production traffic to the wrong backend. Files: `src/environments/environment*.ts`, `src/environments/api-url.ts:2-27`.
- **Global storage cleanup is unsafe.** `localStorage.clear()` removes theme settings and unrelated keys owned by other features or integrations. Files: `src/app/Core/services/auth/auth.ts:235-241`, `src/app/services/network/call.ts:125-137`.
- **The codebase has no verified build/lint gate in this review.** `npm run build` and `npm run lint` could not start because `node_modules` is absent. Without CI enforcement, these routing and type errors can reach deployment.

### Critical
- **Refresh can fail after a page reload.** `initializeSession()` restores `access_token` and `user_data`, but does not restore `refresh_token` into `LandingPageService.refreshToken`. A later refresh sends an empty refresh token. Files: `src/app/Core/services/auth/auth.ts:160-180, 204-212`.
- **Landing guest protection is disabled.** `guestGuard` is implemented but commented out on `/landing`, so an authenticated user can open the login landing screen instead of being redirected to `/afterAuth/home`. Files: `src/app/app.routes.ts:18-20`, `src/app/Core/auth/guards/auth-guard.ts:18-27`.
- **Administration flow is broken.** `/afterAuth/administration` redirects to `/overview`, but no administration overview/users route is defined. The navigation entry is role-filtered, but the route itself has no admin guard. Files: `src/app/app.routes.ts:1191-1196`, `src/app/Core/config/navigation/navigation.config.ts:522-534`.
- **Several placeholder routes redirect to non-existent screens.** `divisional_Organisation`, `dss`, `Reports`, `KPIs`, `Audit_and_Logs`, and `Help` redirect to `overview` without defining an overview component. Files: `src/app/app.routes.ts:159-164, 1059-1077, 1177-1189`.

### High
- **Two login flows execute for one login attempt.** `Auth.logincall()` starts `Call.logincall()` and then separately returns the primary `AppService.post()` request. This can create duplicate authentication requests and inconsistent localStorage state. Files: `src/app/Core/services/auth/auth.ts:44-50`, `src/app/services/network/call.ts:85-106`.
- **Phase-2 token selection is inconsistent.** `authInterceptor` reads the phase-2 token from `localStorage.user`, while the primary auth flow stores `access_token`, `refresh_token`, and `user_data`. If the phase-2 login side effect fails or its storage is stale, phase-2 requests can be sent without the correct bearer token. Files: `src/app/Core/services/interceptor/interceptor.ts:37-50`, `src/app/Core/services/auth/auth.ts:86-97`.
- **Malformed localStorage can crash authentication or every HTTP request.** `JSON.parse()` is used without protection in `initializeSession()` and in `authInterceptor`. A corrupted `user_data` or `user` value can break startup/request processing. Files: `src/app/Core/services/auth/auth.ts:165-168`, `src/app/Core/services/interceptor/interceptor.ts:38-40`.
- **Logout deletes unrelated browser storage.** `clearClientSession()` calls `localStorage.clear()`, removing theme preferences and any other application keys, not only auth keys. Files: `src/app/Core/services/auth/auth.ts:235-241`.
- **The secondary logout service also clears storage before the API request.** `Call.logoutcall()` removes all localStorage entries before calling the logout endpoint, which can remove the refresh token required by the request. Files: `src/app/services/network/call.ts:125-137`.
- **HTTP error responses can be hidden by dummy data.** `Call.get()` catches backend errors and serves a dummy response when one exists. A real 401/403/500 can therefore appear as successful data to the screen instead of showing the actual failure. Files: `src/app/services/network/call.ts:833-843`.
- **Admin authorization is only applied to the sidebar.** `AccessControlService` can hide navigation entries, but hiding a menu item does not prevent direct URL access. The administration route needs its own authorization guard. Files: `src/app/Core/config/navigation/navigation.service.ts:40-46`, `src/app/app.routes.ts:1191-1196`.

### Medium
- **The route fallback can escape the authenticated layout.** Unknown `/afterAuth/...` URLs are handled by the root wildcard, so the `UnderConstruction` page may render without `MainLayout` chrome instead of inside the authenticated shell. File: `src/app/app.routes.ts:1211-1229`.
- **Invalid dynamic ship tabs are accepted by routing.** `/afterAuth/ship/:tab` accepts any tab value and relies on the component to handle invalid values. There is no route-level validation or not-found behavior. Files: `src/app/app.routes.ts:93-107`.
- **Refresh behavior is not explicitly limited by a request marker.** The interceptor retries a failed request after refresh, but there is no explicit retry marker on the cloned request. Future interceptor changes can make a repeated 401 loop easier to introduce. Files: `src/app/Core/services/interceptor/interceptor.ts:89-117`.
- **The app initializes session only when the path is not exactly `/landing`.** Other public paths such as `/` are not included in `blockedRoutes`, so startup behavior differs between equivalent public entry URLs. Files: `src/app/app.ts:22-30`, `src/app/app.routes.ts:7-24`.

### Verification Gaps
- `npm run build` and `npm run lint` could not be executed because `node_modules` is not installed (`ng` and `eslint` were unavailable).
- Browser-level reproduction was not performed because browser automation access was unavailable in this session.

---

## Documentation Drift Found During Revalidation

This section records known differences found while comparing this document with the current source tree.

### High Priority
- Angular and TypeScript versions were outdated in this document. Current versions are Angular `22.0.5` and TypeScript `6.0.3` from `package.json`.
- Auth tokens are persisted in localStorage as `access_token`, `refresh_token`, and `user_data`. The previous memory-only/httpOnly-cookie description was incorrect.
- `initializeSession()` restores the access token and user, but currently does not restore the refresh-token signal before a later refresh attempt.
- `guestGuard` exists but is commented out on the `/landing` route.
- Administration currently has no `/users` route and no route-level admin guard; role filtering is currently applied to navigation configuration.
- Legacy `@NgModule` files still exist under `Pages/dl-monitoring/`.
- The test runner is Vitest in `angular.json`; the project still contains Karma/Jasmine dependencies and specs.

### Routing Differences
- Not every route uses `loadComponent`; several feature groups use `loadChildren` route configuration files.
- The wildcard `UnderConstruction` route is at the root level, not inside the `/afterAuth` children.
- The route table above is a high-level summary. Actual nested routes include inventory searches, requisitions, transactions, approvals, histories, ship returns masters, routine history/reports, DL generation and crew utilities.
- Actual route groups missing from the summary include `/afterAuth/inbox`, `/afterAuth/outbox`, `/afterAuth/dss`, `/afterAuth/Reports`, `/afterAuth/KPIs`, `/afterAuth/Audit_and_Logs`, `/afterAuth/Help`, and `/afterAuth/divisional_Organisation`.
- Home uses `daily-orders-history`, not `daily-orders`.
- KMS screens use nested paths such as `dashboard/overview`, `technical/overview`, and `category-master/overview`.
- Refit/DL Monitoring uses routes such as `overview`, `tracking/:type`, `import`, `master`, `references`, and `history`.

### Architecture Differences
- Shared state is held by `LandingPageService` and `User`; there is no current shared `Data` service matching the earlier description.
- `Call` contains domain APIs, legacy phase-2 auth calls, and dummy GET fallbacks in addition to generic HTTP helpers.
- Some reusable components missing from the earlier inventory include `app-panel-card`, `app-gauge-chart`, `app-pill-toggle`, `app-toolbar-search`, `app-export-toolbar`, `app-detail-drawer`, `app-form-modal`, `app-status-chip`, and `app-rich-text-editor`.

### Verification Status
- `npm run build` and `npm run lint` could not be executed in the review environment because `node_modules` was not installed (`ng` and `eslint` were unavailable).
- Browser-level validation was not performed because browser automation access was not available in the current session.
