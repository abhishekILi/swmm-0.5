import {
  ApplicationConfig,
  inject,
  provideBrowserGlobalErrorListeners,
  provideEnvironmentInitializer,
  provideZoneChangeDetection
} from '@angular/core';
import { TooltipService } from './shared/directives/tooltip.service';

import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { provideAnimations } from '@angular/platform-browser/animations';
/* import  ECHARTS for the speedometar graph */
import { provideEchartsCore } from 'ngx-echarts';

import * as echarts from 'echarts/core';

import {
  GaugeChart,
  BarChart,
  LineChart,
  PieChart
} from 'echarts/charts';

import {
  TooltipComponent,
  TitleComponent,
  GridComponent,
  LegendComponent
} from 'echarts/components';

import {
  CanvasRenderer
} from 'echarts/renderers';
import { provideHttpClient, withInterceptors, withXhr } from '@angular/common/http';
import {
  authInterceptor,
  feedbackInterceptor,
  loaderInterceptor,
  refreshTokenInterceptor,
} from './Core/services/interceptor/interceptor';
import {
  provideLucideConfig,
  provideLucideIcons,
  LucideArchive, LucideArrowLeft, LucideArrowRight, LucideArrowUpRight,
  LucideBell, LucideCake, LucideCalendar, LucideCalendarCheck, LucideCheck,
  LucideChevronDown, LucideChevronRight, LucideChevronUp, LucideMailOpen, LucideExternalLink,
  LucideChevronsLeft, LucideChevronsRight, LucideCircleAlert, LucideCircleCheckBig, LucideCircleX,
  LucideClipboardList, LucideClipboardCheck, LucideClipboard, LucideClock, LucideDownload, LucideEye,
  LucideFile, LucideFileText, LucideFilter, LucideFlag, LucideFunnel, LucideHistory,
  LucideInbox, LucideInfo, LucideLayers, LucideLayoutGrid, LucideLightbulb,
  LucideList, LucideLock, LucideLogOut, LucideMail, LucideMapPin, LucideMenu,
  LucideMessageSquareText, LucideMoon, LucidePanelRight, LucidePlus, LucidePrinter,
  LucideRefreshCw, LucideRepeat, LucideRotateCcw, LucideRotateCw, LucideSearch, LucideSend,
  LucideSheet, LucideSquarePen, LucideSun, LucideTableProperties, LucideTrash,
  LucideWifiOff, LucideX,
  LucideBookOpen, LucideBox, LucideBoxes, LucideChartColumn, LucideCircleHelp,
  LucideHouse, LucideLayoutDashboard, LucideShieldCheck, LucideUser, LucideUsers,
  LucideWrench,
  LucideImage, LucideZap, LucideNetwork,
  LucideChartLine, LucideIdCard, LucideScanEye, LucideCalendarSync, LucideShieldAlert,
  LucideSettings,
  LucidePhone, LucidePhoneCall,
  LucideShip, LucideAnchor, LucideNavigation,
  LucideEyeOff, LucideTriangleAlert, LucideUpload,
  LucideFolderOpen, LucideFolderClosed, LucideFileSpreadsheet,
  LucidePencil, LucideChevronLeft, LucideTrash2, LucideCopy, LucideChevronLast,
  LucideReply, LucideReplyAll, LucideForward, LucideEllipsis, LucideGrid2x2, LucideLink, LucideUnlink,
  LucideSquareCheckBig,
  LucidePackage,
  LucideFactory,
  LucideTruck,
  LucideAward,
  LucideChartPie,
  LucideChartBar,
  LucideListTree,
  LucideCloudUpload,
  LucideBold, LucideItalic, LucideUnderline, LucideStrikethrough,
  LucideListOrdered, LucideEraser, LucideBrain,
  LucideShare2, LucideTags,
  LucideArrowUpDown, LucideFlame, LucidePlane, LucideRadio, LucideSatellite,
  LucideRadar, LucideDatabase, LucideBuilding2,
  LucideSave, LucideCheckCheck, LucideDroplet, LucideCpu, LucideGauge, LucideActivity, LucideSliders,
  LucideShoppingCart, LucideGlobe,
  LucideMessageCircleMore,
  LucideMessageSquareMore,
  LucideMinus,LucideRoute, LucideMessageSquare,
  LucideBan,
} from '@lucide/angular';

/* REGISTER */
echarts.use([
  GaugeChart,
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  CanvasRenderer
]);

ModuleRegistry.registerModules([
  AllCommunityModule
]);

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withXhr(),
      withInterceptors([
        authInterceptor,
        loaderInterceptor,
        feedbackInterceptor,
        refreshTokenInterceptor
      ])
    ),
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({
      eventCoalescing: true
    }),

    provideRouter(routes),


    provideEchartsCore({
      echarts
    }),

    provideAnimations(),
    provideLucideConfig({
      size: 20,
      strokeWidth: 2,
      color: 'currentColor',
    }),

    provideLucideIcons(
      LucideArchive, LucideArrowLeft, LucideArrowRight, LucideArrowUpRight,
      LucideBell, LucideCake, LucideCalendar, LucideCalendarCheck, LucideCheck,
      LucideChevronDown, LucideChevronRight, LucideChevronUp, LucideMailOpen, LucideExternalLink,
      LucideChevronsLeft, LucideChevronsRight, LucideCircleAlert, LucideCircleCheckBig, LucideCircleX,
      LucideClipboardList, LucideClipboardCheck, LucideClipboard, LucideClock, LucideDownload, LucideEye,
      LucideFile, LucideFileText, LucideFilter, LucideFlag, LucideFunnel, LucideHistory,
      LucideInbox, LucideInfo, LucideLayers, LucideLayoutGrid, LucideLightbulb,
      LucideList, LucideLock, LucideLogOut, LucideMail, LucideMapPin, LucideMenu,
      LucideMessageSquareText, LucideMoon, LucidePanelRight, LucidePlus, LucidePrinter,
      LucideRefreshCw, LucideRepeat, LucideRotateCcw, LucideRotateCw, LucideSearch, LucideSend,
      LucideSheet, LucideSquarePen, LucideSun, LucideTableProperties, LucideTrash,
      LucideWifiOff, LucideX,
      LucideBookOpen, LucideBox, LucideBoxes, LucideChartColumn, LucideCircleHelp,
      LucideHouse, LucideLayoutDashboard, LucideShieldCheck, LucideUser, LucideUsers,
      LucideWrench, LucideRoute,
      LucideImage, LucideZap, LucideNetwork,
      LucideChartLine, LucideIdCard, LucideScanEye, LucideCalendarSync, LucideShieldAlert,
      LucideSettings,
      LucidePhone, LucidePhoneCall,
      LucideShip, LucideAnchor, LucideNavigation,
      LucideEyeOff, LucideTriangleAlert, LucideUpload,
      LucideFolderOpen, LucideFolderClosed, LucideFileSpreadsheet,
      LucidePencil, LucideChevronLeft, LucideTrash2, LucideCopy, LucideChevronLast,
      LucideReply, LucideReplyAll, LucideForward, LucideEllipsis, LucideGrid2x2, LucideLink, LucideUnlink, LucideSquareCheckBig, LucidePackage, LucideFactory,
      LucideTruck,
      LucideAward, LucideChartPie, LucideChartBar,
      LucideListTree, LucideCloudUpload,
      LucideBold, LucideItalic, LucideUnderline, LucideStrikethrough,
      LucideListOrdered, LucideEraser, LucideBrain,
      LucideShare2, LucideTags,
      LucideArrowUpDown, LucideFlame, LucidePlane, LucideRadio, LucideSatellite,
      LucideRadar, LucideDatabase, LucideBuilding2,
      LucideSave, LucideCheckCheck, LucideDroplet, LucideCpu, LucideGauge, LucideActivity, LucideSliders,
      LucideShoppingCart, LucideGlobe, LucideMinus, LucideMessageCircleMore, LucideMessageSquareMore, LucideRoute, LucideMessageSquare,
      LucideBan,
    ),

    provideEnvironmentInitializer(() => inject(TooltipService).init()),

  ]

};
