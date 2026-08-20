import {
  AfterViewInit,
  Component,
  EventEmitter,
  Input,
  Output,
  computed,
  inject,
  ChangeDetectionStrategy,
  signal,
  ChangeDetectorRef
} from "@angular/core";

import { NavigationEnd, Router, RouterModule } from "@angular/router";
import { filter } from "rxjs/operators";
import { User } from "../../services/user/user";
import { NavigationNode } from "../../config/navigation/navigation.model";
import { SidebarDataService, SidebarSection } from "./SidebarDataService";
import { LandingPageService } from "../../../Modules/landing/landing-page.service";
import { IconComponent } from "../../../shared/components/icon/icon.component";
import { ThemeService } from "../../services/theme/theme.service";

@Component({
  selector: "app-sidebar",
  standalone: true,
  imports: [RouterModule, IconComponent],
  templateUrl: "./sidebar.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrls: ["./sidebar.css"],
})
export class Sidebar implements AfterViewInit {
  readonly router = inject(Router);
  readonly landingService = inject(LandingPageService);
  readonly userStore = inject(User);
  readonly sidebarDataService = inject(SidebarDataService);
  readonly cdr = inject(ChangeDetectorRef);
  private readonly themeService = inject(ThemeService);

  readonly currentUser = computed(() => {
    return this.userStore.userDetails() || this.landingService.user();
  });

  @Input() collapsed = false;
  @Output() collapsedChange = new EventEmitter<boolean>();

  readonly sections = computed<SidebarSection[]>(() =>
    this.sidebarDataService.getSidebarSections(),
  );
  /** Home has no section label (rendered header-less, pinned above Inbox/Outbox) — pulled out
   *  of `sections()` here so the template can pin it outside the scrollable nav. */
  readonly homeItem = computed<NavigationNode | undefined>(
    () => this.sections().find((s) => !s.sectionLabel)?.items[0],
  );
  readonly scrollableSections = computed<SidebarSection[]>(() =>
    this.sections().filter((s) => !!s.sectionLabel),
  );
  readonly currentUrl = signal(this.router.url);
  expandedItems = new Set<string>();
  /** Section headers (e.g. "Operations & Maintenance") collapsed by the user — absent from this set means expanded, so every section starts open by default. */
  collapsedSections = new Set<string>();

  ngAfterViewInit(): void {
    this.expandParentsForActiveRoute();
    this.router.events
      .pipe(
        filter(
          (event): event is NavigationEnd => event instanceof NavigationEnd,
        ),
      )
      .subscribe((event: NavigationEnd) => {
        this.currentUrl.set(event.urlAfterRedirects);
        this.expandParentsForActiveRoute();
        this.cdr.markForCheck();
      });
  }

  getUserInitial(): string {
    const firstName = this.currentUser()?.['first_name'] as string | undefined;
    return firstName?.charAt(0) || "U";
  }

  /** From `/api/v1/user/me/`'s nested `profile.ship_name` (e.g. "INS Rama"). */
  getShipName(): string {
    const profile = this.currentUser()?.['profile'] as Record<string, unknown> | undefined;
    return (profile?.['ship_name'] as string | undefined) ?? '';
  }

  getUserFullName(): string {
    const user = this.currentUser();
    if (!user) {
      return "Profile & Settings";
    }
    const firstName = (user['first_name'] as string) || "";
    const lastName = (user['last_name'] as string) || "";
    return `${firstName} ${lastName}`.trim();
  }

  getUserFirstName(): string {
    return (this.currentUser()?.['first_name'] as string) || "User";
  }

  getUserDesignation(): string {
    return (this.currentUser()?.['designation'] as string) || "--";
  }

  isExpanded(item: NavigationNode): boolean {
    return this.expandedItems.has(item.label);
  }

  toggle(item: NavigationNode): void {
    if (item.children?.length) {
      if (this.expandedItems.has(item.label)) {
        this.expandedItems.delete(item.label);
      } else {
        this.expandedItems.add(item.label);
      }

      this.expandedItems = new Set(this.expandedItems);

      if (item.route) {
        this.navigate(item.route);
      }
    }
  }

  open(item: NavigationNode): void {
    this.navigate(item.route);
  }

  isSectionExpanded(sectionLabel: string): boolean {
    return !this.collapsedSections.has(sectionLabel);
  }

  toggleSection(sectionLabel: string): void {
    if (this.collapsedSections.has(sectionLabel)) {
      this.collapsedSections.delete(sectionLabel);
    } else {
      this.collapsedSections.add(sectionLabel);
    }
    this.collapsedSections = new Set(this.collapsedSections);
  }

  toggleSidebar(): void {
    this.collapsed = !this.collapsed;
    this.collapsedChange.emit(this.collapsed);
  }

  navigate(route?: string): void {
    console.log("route>>>", route)
    if (route) this.router.navigateByUrl(route);
  }

  isActive(route?: string): boolean {
    if (!route) {
      return false;
    }
    const url = this.currentUrl();
    if (url === route || url.startsWith(route + "/")) {
      return true;
    }
    const parts = route.split('/').filter(Boolean);
    if (parts.length > 3) {
      const routeWithoutTab = "/" + parts.slice(0, -1).join('/');
      if (routeWithoutTab && url.startsWith(routeWithoutTab + '/')) {
        return true;
      }
    }
    return false;
  }
  isModuleActive(item: NavigationNode): boolean {
    if (!item.route) {
      return this.isChildActive(item);
    }

    const segments = item.route.split("/").filter(Boolean);

    const afterAuthIndex = segments.indexOf("afterAuth");

    if (afterAuthIndex === -1) {
      return false;
    }

    const module = segments[afterAuthIndex + 1];

    const url = this.currentUrl();
    return url.startsWith(`/afterAuth/${module}`);
  }

  isChildActive(item: NavigationNode): boolean {
    const url = this.currentUrl();
    return (
      item.children?.some(
        (child) =>
          !!child.route &&
          (url === child.route ||
            url.startsWith(child.route + "/")),
      ) ?? false
    );
  }

  get allItems(): NavigationNode[] {
    return this.sections().flatMap((s) => s.items);
  }

  private expandParentsForActiveRoute(): void {
    let changed = false;
    for (const item of this.allItems) {
      if (item.children?.length && this.isChildActive(item)) {
        if (!this.expandedItems.has(item.label)) {
          this.expandedItems.add(item.label);
          changed = true;
        }
      }
    }
    if (changed) this.expandedItems = new Set(this.expandedItems);
  }

  getLogoPath(): string {
    // Light theme uses a single dedicated logo asset for both collapsed and
    // expanded states. Dark theme keeps its existing per-state assets.
    if (this.themeService.theme() === "light") {
      return "assests/logo/swmm-sidebar-logo-light.png";
    }
    return this.collapsed
      ? "assests/logo/swmm-sidebar-collaps-logo.png"
      : "assests/logo/swmm-sidebar-open-logo.png";
  }
}
