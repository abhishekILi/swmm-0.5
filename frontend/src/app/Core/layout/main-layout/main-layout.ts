import { Component, ElementRef, ViewChild, OnInit, AfterViewInit, inject, signal, computed, ChangeDetectionStrategy } from '@angular/core';

import {
  Router,
  RouterOutlet,
  NavigationEnd
} from '@angular/router';

import { filter } from 'rxjs/operators';

import { Sidebar } from '../../../Core/component/sidebar/sidebar';
import { Header } from '../../../Core/component/header/header';
import { Breadcrum } from '../../../Core/component/breadcrum/breadcrum';
import { Footer } from '../../../Core/component/footer/footer';
import { ThemeService } from '../../../Core/services/theme/theme.service';
import { InventoryTabNav } from '../../../Pages/inventory/shared/inventory-tab-nav/inventory-tab-nav';
import { InventoryTabItem } from '../../../Pages/inventory/shared/models/inventory-nav.model';
import { SHIP_INVENTORY_OBS_TABS } from '../../../Pages/inventory/ship-inventory-obs/ship-inventory-obs.nav';
import { SHORE_INVENTORY_MO_TABS } from '../../../Pages/inventory/shore-inventory-mo/shore-inventory-mo.nav';
import { SHORE_INVENTORY_WED_TABS } from '../../../Pages/inventory/shore-inventory-wed/shore-inventory-wed.nav';
import { SHIP_CREW_TABS } from '../../../Pages/ship-crew/ship-crew.nav';

// Every module that owns its own top nav (in place of the shared app header)
// registers its base route + tab config here.
const INVENTORY_MODULE_TABS: { base: string; tabs: InventoryTabItem[]; title?: string }[] = [
  { base: '/afterAuth/inventory/ship-inventory-obs', tabs: SHIP_INVENTORY_OBS_TABS, title: 'Ship Inventory - OBS' },
  { base: '/afterAuth/inventory/shore-inventory-mo', tabs: SHORE_INVENTORY_MO_TABS, title: 'Shore Inventory - MO' },
  { base: '/afterAuth/inventory/shore-inventory-wed', tabs: SHORE_INVENTORY_WED_TABS, title: 'Shore Inventory - WED' },
  { base: '/afterAuth/Ship_Crew_and_HR', tabs: SHIP_CREW_TABS, title: 'Ship Crew' },
];

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    Header,
    InventoryTabNav,
    Breadcrum,
    RouterOutlet,
    Footer,
    Sidebar
  ],
  templateUrl: './main-layout.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './main-layout.css'
})
export class MainLayout implements OnInit, AfterViewInit {
  readonly router = inject(Router);

  readonly themeService = inject(ThemeService);

  sidebarCollapsed = false;

  // A handful of inventory sub-modules own their own top nav (with the same
  // online/theme/notification/mail/logout cluster) in place of the shared
  // app header — this resolves which config (if any) applies to the URL.
  readonly currentUrl = signal(this.router.url);
  readonly activeInventoryTabs = computed<InventoryTabItem[] | null>(() => {
    const url = this.currentUrl();
    return INVENTORY_MODULE_TABS.find((module) => url.startsWith(module.base))?.tabs ?? null;
  });
  readonly activeInventoryTitle = computed<string | undefined>(() => {
    const url = this.currentUrl();
    return INVENTORY_MODULE_TABS.find((module) => url.startsWith(module.base))?.title;
  });

  @ViewChild('contentArea')
  contentArea!: ElementRef<HTMLElement>;

  ngOnInit(): void {
    // Restore theme preference from localStorage
    this.themeService.initTheme();
    this.checkSidebarState(this.router.url);
  }

  ngAfterViewInit(): void {
    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd)
      )
      .subscribe((event: NavigationEnd) => {
        this.currentUrl.set(event.urlAfterRedirects || event.url);
        this.checkSidebarState(event.urlAfterRedirects || event.url);

        setTimeout(() => {
          if (this.contentArea?.nativeElement) {
            this.contentArea.nativeElement.scrollTo({
              top: 0,
              left: 0,
              behavior: 'auto'
            });
          }
        }, 0);

      });
  }

  private checkSidebarState(url: string): void {
    // Only open the sidebar if the route includes 'overview'
    this.sidebarCollapsed = !url.includes('overview');
  }
}
