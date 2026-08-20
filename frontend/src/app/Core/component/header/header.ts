import { Component, OnInit, HostListener, ElementRef, ViewChild, inject, effect, ChangeDetectorRef, ChangeDetectionStrategy, signal } from "@angular/core";
import { Router, RouterModule, NavigationEnd } from "@angular/router";

import { filter } from "rxjs/operators";
import { MailNotiCenter } from "../mail-noti-center/mail-noti-center";
import { IconComponent } from "../../../shared/components/icon/icon.component";
import { Auth } from "../../services/auth/auth";
import { NetworkStatusService } from "../../services/common/network-status.service";
import { NavigationService } from "../../config/navigation/navigation.service";
import { AccessControlService } from "../../config/navigation/access-control.service";
import { HeaderTabConfig, HeaderTabKey } from "../../config/navigation/navigation.model";
import { NotificationStore } from "../../services/notification/notification-store";
import { ThemeService } from "../../services/theme/theme.service";
import { CommonModule } from "@angular/common";

const DEFAULT_TAB_LABELS: Record<HeaderTabKey, string> = {
  overview: "Overview",
  configuration: "Configuration",
  actions: "Actions",
  reports: "Reports",
  dlGeneration: "DL I Generation",
  insights: "Insights",
  references: "References",
};

@Component({
  selector: "app-header",
  standalone: true,
  imports: [RouterModule, MailNotiCenter, IconComponent, CommonModule],
  templateUrl: "./header.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: "./header.css",
})
export class Header implements OnInit {
  router = inject(Router);
  navigationService = inject(NavigationService);
  readonly authService = inject(Auth);
  private readonly access = inject(AccessControlService);
  private readonly cdr = inject(ChangeDetectorRef);
  readonly networkStatus = inject(NetworkStatusService);
  readonly notifications = inject(NotificationStore);
  readonly themeService = inject(ThemeService);
  readonly currentUrl = signal(this.router.url);

  constructor() {
    effect(() => {
      this.access.roles();
      this.access.rbacActive();
      this.updateHeader(this.currentUrl());
      this.cdr.markForCheck();
    });
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  pageTitle = "";
  headerTabs: Partial<Record<HeaderTabKey, HeaderTabConfig>> = {};
  currentModuleId = "";
  private currentModuleHeaderKeys: string[] | null = null;

  @ViewChild("popupRef") popupRef!: ElementRef;
  @ViewChild("mailBtn") mailBtn?: ElementRef;
  @ViewChild("notificationBtn") notificationBtn!: ElementRef;
  @ViewChild("profileBtn") profileBtn!: ElementRef;
  @ViewChild("mobileToggleBtn") mobileToggleBtn?: ElementRef;
  @ViewChild("navContainer") navContainer?: ElementRef;

  popupType: "mail" | "notification" | "profile" = "mail";
  showMailPopup = false;
  /** Mail button hidden for now — flip back to true to restore it. */
  readonly showMailButton = false;
  hoveredTab: string | null = null;
  mobileMenuOpen = false;
  readonly HeaderTabKeys: HeaderTabKey[] = ["overview", "actions", "reports", "dlGeneration", "insights", "references", "configuration"];
  tabOrder: HeaderTabKey[] = this.HeaderTabKeys;

  toggleMobileMenu(): void {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen = false;
    this.hoveredTab = null;
  }

  toggleMailPopup(event: MouseEvent, type: "mail" | "notification" | "profile"): void {
    event.stopPropagation();
    if (this.showMailPopup && this.popupType === type) {
      this.showMailPopup = false;
      return;
    }
    this.popupType = type;
    this.showMailPopup = true;
    if (type === "notification") {
      this.notifications.loadFeed();
    }
  }

  closeMailPopup(): void {
    this.showMailPopup = false;
  }

  onTabClick(tabKey: HeaderTabKey): void {
    const tab = this.headerTabs[tabKey];
    if (!tab) return;
    if (this.hasDropdownChildren(tabKey)) {
      this.openDropdown(tabKey);
      return;
    }
    if (tab.route) {
      const route = this.buildTabRoute(tab.route, tab.absoluteRoute);
      this.navigate(route);
    }
  }

  private buildTabRoute(tabRoute: string, absoluteRoute = false): string {
    if (absoluteRoute) {
      return this.navigationService.buildRoute(this.currentModuleId, tabRoute);
    }

    const currentUrl = this.currentUrl().split('?')[0];
    const segments = currentUrl.split('/').filter(Boolean);
    const afterAuthIndex = segments.indexOf('afterAuth');

    if (afterAuthIndex === -1) {
      return this.navigationService.buildRoute(this.currentModuleId, tabRoute);
    }

    const nextSegment = segments[afterAuthIndex + 2];

    if (this.currentModuleHeaderKeys) {
      if (nextSegment && this.currentModuleHeaderKeys.includes(nextSegment)) {
        return this.navigationService.buildRoute(this.currentModuleId, `${nextSegment}/${tabRoute}`);
      }
      return this.navigationService.buildRoute(this.currentModuleId, tabRoute);
    }

    if (this.currentModuleId === 'refit_dashboard') {
      return this.navigationService.buildRoute(this.currentModuleId, tabRoute);
    }

    if (nextSegment && nextSegment !== 'overview' && nextSegment !== 'actions' &&
      nextSegment !== 'configuration' && nextSegment !== 'reports' && nextSegment !== 'insights') {
      return this.navigationService.buildRoute(this.currentModuleId, `${nextSegment}/${tabRoute}`);
    }
    if (this.currentModuleId === 'ship-returns') {
      const activeChild = nextSegment && nextSegment !== 'overview' ? nextSegment : 'srar';
      if (tabRoute.startsWith(activeChild + '/')) {
        return this.navigationService.buildRoute(this.currentModuleId, tabRoute);
      }
      return this.navigationService.buildRoute(this.currentModuleId, `${activeChild}/${tabRoute}`);
    }


    return this.navigationService.buildRoute(this.currentModuleId, tabRoute);
  }

  buildDropdownRoute(route: string, absoluteRoute = false): string {
    return this.buildTabRoute(route, absoluteRoute);
  }

  openDropdown(tabKey: string): void {
    this.hoveredTab = tabKey;
  }

  closeDropdown(): void {
    this.hoveredTab = null;
  }

  navigate(route: string): void {
    this.closeMobileMenu();
    this.router.navigateByUrl(route);
  }

  tabRoute(tabKey: HeaderTabKey): string {
    const route = this.headerTabs[tabKey]?.route;
    if (!route) return "";
    return this.buildTabRoute(route, this.headerTabs[tabKey]?.absoluteRoute);
  }

  tabLabel(tabKey: HeaderTabKey): string {
    return this.headerTabs[tabKey]?.label ?? DEFAULT_TAB_LABELS[tabKey];
  }

  isActive(route: string): boolean {
    if (!route) return false;
    const urlWithoutQuery = this.currentUrl().split('?')[0];

    if (urlWithoutQuery === route || urlWithoutQuery.startsWith(route + "/")) {
      return true;
    }

    if (route.endsWith('/dashboard') && route.slice(0, -10) === urlWithoutQuery) {
      return true;
    }

    return false;
  }

  isTabActive(tabKey: HeaderTabKey): boolean {
    if (this.isActive(this.tabRoute(tabKey))) return true;
    const children = this.headerTabs[tabKey]?.children ?? [];
    return children.some((child) => child.route && this.isActive(this.buildTabRoute(child.route, child.absoluteRoute)));
  }

  hasDropdownChildren(tabKey: HeaderTabKey): boolean {
    return !!this.headerTabs[tabKey]?.children?.length;
  }

  @HostListener("document:click", ["$event"])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const clickedPopup = this.popupRef?.nativeElement.contains(target);
    const clickedMailBtn = this.mailBtn?.nativeElement.contains(target);
    const clickedNotificationBtn = this.notificationBtn?.nativeElement.contains(target);
    const clickedProfileBtn = this.profileBtn?.nativeElement.contains(target);

    if (!clickedPopup && !clickedMailBtn && !clickedNotificationBtn && !clickedProfileBtn) {
      this.showMailPopup = false;
    }

    if (this.mobileMenuOpen) {
      const clickedToggle = this.mobileToggleBtn?.nativeElement.contains(target);
      const clickedNav = this.navContainer?.nativeElement.contains(target);
      if (!clickedToggle && !clickedNav) {
        this.closeMobileMenu();
      }
    }
  }

  ngOnInit(): void {
    this.updateHeader(this.router.url);
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.currentUrl.set(event.urlAfterRedirects);
        this.updateHeader(event.urlAfterRedirects);
        this.cdr.markForCheck();
      });
  }

  private updateHeader(url: string = this.currentUrl()): void {
    const module = this.navigationService.getCurrentModule(url);
    if (!module) {
      this.pageTitle = "";
      this.currentModuleId = "";
      this.currentModuleHeaderKeys = null;
      this.headerTabs = {};
      this.tabOrder = this.HeaderTabKeys;
      return;
    }

    this.currentModuleId = module.id;
    this.currentModuleHeaderKeys = module.headers
      ? module.headerNestedKeys ?? Object.keys(module.headers)
      : null;
    const activeHeaderKey = this.navigationService.getActiveHeaderKey(module, url);
    this.tabOrder = (activeHeaderKey ? module.headerTabOrders?.[activeHeaderKey] : undefined) ?? this.HeaderTabKeys;
    this.pageTitle = module.title;
    if (this.currentModuleId === 'ship-returns' || this.currentModuleId === 'refit_dashboard') {
      this.headerTabs = this.navigationService.getAccessibleHeader(module, url);
      return
    }
    this.headerTabs = this.navigationService.getAccessibleHeader(module, this.router.url);

  }

  logout(): void {
    this.authService.logout();
  }
}
