import { Component, ChangeDetectionStrategy, signal, computed, OnInit, AfterViewChecked, ElementRef, Renderer2, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { RouterModule, ActivatedRoute, Router } from "@angular/router";
import { ColDef, GridReadyEvent, GridApi, ICellRendererParams, CellCallbackParams } from "ag-grid-community";
import { IconComponent } from "../../../../shared/components/icon/icon.component";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { PanelCard } from "../../../../shared/components/panel-card/panel-card";
import { SelectInput, DropdownOption } from "../../../../shared/components/select-input/select-input";
import { InputField } from "../../../../shared/components/input-field/input-field";
import { TextareaInput } from "../../../../shared/components/textarea-input/textarea-input";
import { ModalComponent } from "../../../../shared/components/modal/modal.component";
import { SrarService, SrarRecord, SrarCarryForward, SrarApiResponse, ExportSrarResponse } from "../../../../Core/services/srar/srar.service";
import { AppService } from "../../../../Core/services/app/app.service";
export function getRandom4DigitNumber(): number {
  const array = new Uint32Array(1);
  crypto.getRandomValues(array);
  return 1000 + (array[0] % 9000);
}

export type OpsValue = number | string | null | undefined;
export type StringNullable = string | null | undefined;

export interface SrarSubTab {
  id: number;
  title: string;
  shortTitle: string;
  icon: string;
}

export type FormItemValue = string | number | boolean | File[] | null | undefined;


export interface EquipmentItem {
  [key: string]: FormItemValue;
  id?: number;
  name: string;
  nomenclature?: string;
  eqptCode?: string;
  prevHours: number | string;
  monthlyHours?: string;
  cumulativeHours?: string;
  duringMonthHours?: number;
  duringMonthMinutes?: number;
  totalHours?: string;
  subDept?: string;
  serNo?: string;
}

export interface BoilerSteamingItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  locOnBoard: string;
  serNo: string;
  hrsSteamedDuringMonth: string;
  hrsSteamedSinceComm: string;
  hrsAbove80: string;
  lastEstOlgDate: string;
  hrsSteamedSinceLastOlg: string;
  hrsSteamedAtLastOlg: string;
  lastEstOlgDate2: string;
  hrsSteamedSinceLastOlg2: string;
  hrsSteamedAtLastOlg2: string;
  lastRetubingDate: string;
  hrsSteamedSinceLastRetubing: string;
  hrsSteamedAtLastRetubing: string;
  lastHydraulicTestDate: string;
  nextInspectionDate: string;
  lifeAssessedMonths: string;
}

export interface BoilerAlkalinityItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  locOnBoard: string;
  serNo: string;
  salinityLastWeek: string;
  chlorideDuringMonth: string;
  excessSalinity: string;
  alkalinityN: string;
  phYarr: string;
  tdsMax750: string;
  phosphate1060: string;
  phosphate0: string;
  alkalinityMax: string;
  alkPpm: string;
  alkalinityPercent: string;
  phJvn: string;
  tdsMax750Jvn: string;
  phosphate1060Jvn: string;
  alkalinityPercentCommon: string;
}

export interface ActivityItem {
  [key: string]: FormItemValue;
  id?: number;
  dateRange: string;
  shipState: string;
  shipLocation: string;
  activityType: string;
  activityDetail: string;
  remarks: string;
}

export interface TorsionMeterItem {
  [key: string]: FormItemValue;
  id?: number;
  srNo: number;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  opsNonOps: string;
  torsionMeterRdg: string;
  maxRpmAchieved: string;
  nonOpsSince: string;
  lastCalibrationOn: string;
  nextCalibrationDue: string;
}

export interface IccpItem {
  [key: string]: FormItemValue;
  id?: number;
  srNo?: number;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  opsNonOps: string;
  nonOpsSince: string;
}

export interface H2SSensorItem {
  [key: string]: FormItemValue;
  id?: number;
  srNo?: number;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  opsNonOps: string;
  nonOpsSince: string;
  lastCalibratedOn: string;
  nextCalibration: string;
}

export interface StpItem {
  [key: string]: FormItemValue;
  id?: number;
  srNo?: number;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  status: string;
  effluentTestDate: string;
  remarks: string;
}

export interface MagazineItem {
  [key: string]: FormItemValue;
  id?: number;
  srNo?: number;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  status: string;
  lastTrialsTaken?: string;
  nextTrialsDue?: string;
}

export interface TestKitItem {
  [key: string]: FormItemValue;
  id?: number;
  description: string;
  opsNonOps: string;
  nonOpsSince1: string;
  calibrationDate: string;
  nextCalibrationDueDate: string;
  nonOpsSince2?: string;
}

export interface CentrifugeItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  serNo: string;
  locOnBoard: string;
  opsNonOps: string;
  nonOpsSince: string;
  lastCalibratedOn: string;
  nextCalibration: string;
}

export interface SafetyDeviceItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptSerNo?: string;
  eqptCode: string;
  locOnBoard: string;
  sdcConductedBy: string;
  dateOfSdc: string;
  sfcGmsKWh: string;
  lastSfcTrialDate: string;
  displacementDuringSfc: string;
  status: string;
}

export interface InjectorFipItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  fipInMonth: string;
  rhSinceInstallation: string;
  prevRhSinceInstallation?: string;
  isRegimeMismatch?: boolean;
  hrsBelow30: string;
  hrs30to50: string;
  hrs50to70: string;
  hrs70to100: string;
  lubOilConsCurrentMonth: string;
  dateOfInjectorCalibration: string;
  occasionsReplacement: string;
  inOutWhichReplaced: string;
  fuelConsumptionTons: string;
  remarks: string;
}

export interface ReplacementItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  eqptSrNumber: string;
  dateOfReplacement: string;
  subAssemblyUnitName: string;
  reasonOfReplacement: string;
  lifeSinceInstallation?: string;
  lastCalibratedOn?: string;
  nextCalibration?: string;
  remarks: string;
  tabValue?: string;
}

export interface RoutineItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  eqptSrNumber: string;
  date: string;
  descriptionForRoutine: string;
  undertakenByWhom: string;
  tabValue?: string;
}

export interface FptMainEngineSpecificItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  serNo: string;
  fuelRackDbl: string;
  fciThrottleMarking: string;
  lastEhmTrialsDate: string;
  pitch: string;
  maxRpm: string;
  ratedPower: string;
  maxAchievedPower: string;
  remarks: string;
}

export interface FptDieselGeneratorLoadItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  location: string;
  eqptSerNo: string;
  date: string;
  occasionReason: string;
  ratedLoad: string;
  maxLoadAchieved: string;
  conductedBy: string;
  lastEhmTrialsDate: string;
  remarks: string;
}

export interface GasTurbineExploitationItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  serNo: string;
  totalRhInMonth: string;
  rhEngine1: string;
  rhEngine2: string;
  totalRhSi: string;
  prevTotalRhSi?: string;
  prevRhRegime1Si?: string;
  prevRhRegime2Si?: string;
  prevRhRegime3Si?: string;
  isRegimeMismatch?: boolean;
  status: string;
  nonOpsSince: string;
  lastCalibrationDate: string;
  lastEhmTrialDate: string;
  lastFptDate: string;
  fuelExploitation: string;
  rhRegime1InMonth: string;
  rhRegime2InMonth: string;
  rhRegime3InMonth: string;
  gslEngine1_1_0to1_25: string;
  rhRegime1Si: string;
  rhRegime2Si: string;
  rhRegime3Si: string;
  gslEngine2_1_0to1_25: string;
  unscheduledEngagement: string;
  noOfOccasion: string;
  noOfRepOrders: string;
  gslChemQty: string;
}

export interface GtReductionGearItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  eqptSerNo: string;
  totalRhInMonth: string;
  totalRhsi: string;
  prevTotalRhsi?: string;
  hoRegimeBelow0_25: string;
  hoRegimeBelow0_25Si: string;
  prevHoRegimeBelow0_25Si?: string;
  hoRegime0_25to0_5: string;
  hoRegime0_25to0_5Si: string;
  prevHoRegime0_25to0_5Si?: string;
  hoRegime0_5to0_75: string;
  hoRegime0_5to0_75Si: string;
  prevHoRegime0_5to0_75Si?: string;
  isRegimeMismatch?: boolean;
  slidingHours0_25: string;
  slidingHours0_25Si: string;
  serviceLife: string;
  serviceLifeSi: string;
  routineRegime1: string;
  routineRegime1Si: string;
  routineRegime2: string;
  routineRegime2Si: string;
  routineRegime3: string;
  routineRegime3Si: string;
  routineRegime4: string;
  routineRegime4Si: string;
}

export interface GtgExploitationItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  serNo: string;
  rhInSea: string;
  rhInHarbour: string;
  totalRhInMonth: string;
  totalRhsi: string;
  noOfColdStarts: number;
  noOfColdStartsSi?: number;
  noOfHotStarts: number;
  noOfHotStartsSi?: number;
  noOfBatteryHotStarts: number;
  noOfBatteryHotStartsSi?: number;
  noOfBatteryColdStarts: number;
  noOfBatteryColdStartsSi?: number;
  lastChemClgDateReason: string;
}

export interface GtgReductionGearItem {
  [key: string]: FormItemValue;
  id?: number;
  eqptName: string;
  nomenclature: string;
  eqptCode: string;
  locOnBoard: string;
  serNo: string;
  rgRunningHours: string;
  noOfHotStarts: number;
  noOfColdStarts: number;
  rhInHarbour: string;
  rhInSea: string;
  inMonthsSi: string;
}

export interface LubItem {
  [key: string]: FormItemValue;
  name: string;
  quantity: number;
  unit: string;
}

export interface RhExtensionItem {
  [key: string]: FormItemValue;
  eqptShipName?: string;
  eqptName: string;
  location: string;
  nomenclature?: string;
  serNo: string;
  onRoutine: string;
  rhDuringTrial: string;
  trialConductedBy: string;
  authorityLetter: File[] | null;
  authorityLetterRef?: string;
  rhdi?: string;
  rhExtensionGranted: string;
  rhLeftExpiry: string;
}

export interface RunningParameters {
  [key: string]: FormItemValue;
  baselineSinceCommHours?: number;
  baselineSinceCommMinutes?: number;
  baselineSinceCommDistance?: number;
  duringMonthHours: number;
  duringMonthMinutes: number;
  duringMonthDistance: string;
  sinceCommHours: string;
  sinceCommDistance: string;
  maxSpeedDuringMonth: string;
  maxSpeedDurationHours: number;
  maxSpeedDurationMinutes: number;
  maxSpeedDate: string;
  maxShaftRpm: string;
}

export interface LookupItem {
  id?: number;
  name: string;
}

interface SrarEquipmentLookupRow {
  id?: number | string;
  name?: string;
  nomenclature?: string;
  srar_txt?: string;
  srar_type?: string;
  equipment_desc?: string;
  equipment_category_code?: string;
}

interface SrarCmmsSyncResponse {
  status?: boolean | string;
  message?: string;
  [key: string]: unknown;
}

interface HttpErrorLike {
  error?: { message?: string };
  message?: string;
}

@Component({
  selector: "app-srar-transaction",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    IconComponent,
    DataGrid,
    PanelCard,
    SelectInput,
    InputField,
    TextareaInput,
    ModalComponent
  ],
  templateUrl: "./srar-transaction.component.html",
  styleUrls: ["./srar-transaction.component.css"],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SrarTransactionComponent implements OnInit, AfterViewChecked {
  private readonly srarService = inject(SrarService);
  private readonly appService = inject(AppService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly hostElement = inject(ElementRef<HTMLElement>);
  private readonly renderer = inject(Renderer2);

  srarId: number | null = null;
  activeSubTab = signal<number>(1);
  selectedMonth = signal<string>("August");
  selectedYear = signal<number>(2026);
  shipId: number | null = null;
  carryForward: SrarCarryForward = {
    fuel_balance_last_month: 0,
    avcat_balance_last_month: 0,
    injector_fip: [],
    gas_turbine: [],
    reduction_gear: []
  };
  isCmmsSynced = computed(() => {
    const match = this.findExistingRecordForSelection();
    return Boolean(match?.cmms_sync_status ?? match?.cmmsSyncStatus ?? false);
  });
  showDetails = signal<boolean>(false);
  showEoDetailsModal = signal<boolean>(false);
  isExporting = signal<boolean>(false);
  private gridApi: GridApi | null = null;

  private setExportingState(exporting: boolean): void {
    this.isExporting.set(exporting);

    if (typeof document !== "undefined") {
      const exportButtons = document.querySelectorAll(".grid-action-export");
      exportButtons.forEach((btn) => {
        if (exporting) {
          btn.setAttribute("disabled", "disabled");
          btn.classList.add("disabled");
          btn.setAttribute("title", "Exporting SRAR...");
        } else {
          btn.removeAttribute("disabled");
          btn.classList.remove("disabled");
          btn.setAttribute("title", "Export SRAR");
        }
      });
    }

    if (this.gridApi) {
      this.gridApi.refreshCells({ force: true });
    }
  }

  eoDetails = {
    writerContactNo: "",
    rank: "",
    name: "",
    personalNo: "",
    contactNo: "",
    sendToCo: false
  };

  months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  years = [2024, 2025, 2026, 2027, 2028, 2029, 2030];

  get monthOptions(): DropdownOption[] {
    return this.months.map(m => ({ label: m, value: m }));
  }

  get yearOptions(): DropdownOption[] {
    return this.years.map(y => ({ label: String(y), value: y }));
  }

  transactionSubTabs: SrarSubTab[] = [
    { id: 1, title: "1. Ship Running Details", shortTitle: "1. Running Details", icon: "activity" },
    { id: 2, title: "2. Boiler Steaming Detail", shortTitle: "2. Boiler Steaming", icon: "flame" },
    { id: 3, title: "3. Ship Activity", shortTitle: "3. Ship Activity", icon: "navigation" },
    { id: 4, title: "4. Fuel / AVCAT / Torsionmeter", shortTitle: "4. Fuel & Torsion", icon: "droplet" },
    { id: 5, title: "5. ICCP / H2S Sensor / STP / MFFS", shortTitle: "5. Sensors & STP", icon: "shield-check" },
    { id: 6, title: "6. Test Kits / Centrifuge", shortTitle: "6. Test Kits", icon: "droplet" },
    { id: 7, title: "7. Diesel Engine & SDC", shortTitle: "7. Diesel Engine", icon: "cpu" },
    { id: 8, title: "8. DGUF", shortTitle: "8. DGUF", icon: "chart-bar" },
    { id: 9, title: "9. Full Power Trials", shortTitle: "9. Full Power", icon: "gauge" },
    { id: 10, title: "10. GT / RG Exploitation", shortTitle: "10. GT / RG", icon: "zap" },
    { id: 11, title: "11. GTG Exploitation", shortTitle: "11. GTG", icon: "zap" },
    { id: 12, title: "12. Lubricant Consumption", shortTitle: "12. Lubricant", icon: "box" },
    { id: 13, title: "13. R/H Extension", shortTitle: "13. R/H Extension", icon: "clock" },
    { id: 14, title: "14. EO Remark", shortTitle: "14. EO Remark", icon: "file-text" },
    { id: 15, title: "15. Final Page", shortTitle: "15. Final Page", icon: "circle-check-big" },
  ];

  records = signal<SrarRecord[]>([]);

  columnDefs: ColDef[] = [
    {
      headerName: "S.No",
      valueGetter: "node.rowIndex + 1",
      flex: 1,
      minWidth: 80,
      sortable: true,
      filter: true,
      cellRenderer: (params: ICellRendererParams) => {
        return `<span class="font-semibold text-white/90">${params.value}</span>`;
      },
    },
    {
      headerName: "SRAR No.",
      field: "srarNo",
      flex: 1.8,
      minWidth: 160,
      sortable: true,
      filter: true,
      cellRenderer: (params: ICellRendererParams) => {
        return `<span class="dart-no-code">${params.value}</span>`;
      },
    },
    {
      headerName: "Year",
      field: "year",
      flex: 1.5,
      minWidth: 100,
      sortable: true,
      filter: true,
      cellRenderer: (params: ICellRendererParams) => {
        return `<span class="font-semibold text-white">${params.value}</span>`;
      },
    },
    {
      headerName: "Month",
      field: "month",
      flex: 1.5,
      minWidth: 120,
      sortable: true,
      filter: true,
      cellRenderer: (params: ICellRendererParams) => {
        return `<span class="font-semibold text-white">${params.value}</span>`;
      },
    },
    {
      headerName: "Status",
      field: "approvalStatus",
      flex: 1.8,
      minWidth: 140,
      sortable: true,
      filter: true,
      cellRenderer: (params: ICellRendererParams) => {
        const val = params.value;
        let status = "Draft";
        if (typeof val === "string") {
          status = val;
        } else if (typeof val === "object" && val !== null) {
          status = String(val.label || val.name || val.value || "Draft");
        }
        let badgeClass = "badge-secondary";
        if (status === "Approved") badgeClass = "badge-success";
        else if (status === "In Review") badgeClass = "badge-warning";
        else if (status === "Pending") badgeClass = "badge-info";
        return `<span class="status-pill ${badgeClass}">${status}</span>`;
      },
    },
    {
      headerName: "Action",
      flex: 2,
      minWidth: 220,
      sortable: false,
      filter: false,
      cellRenderer: (params: ICellRendererParams) => {
        const row = params.data as SrarRecord | undefined;
        const isSynced = Boolean(row?.cmms_sync_status ?? row?.cmmsSyncStatus ?? false);
        const disabledAttr = isSynced ? 'disabled="disabled"' : '';
        const syncClass = isSynced ? 'grid-action-pill grid-action-sync disabled' : 'grid-action-pill grid-action-sync';
        const syncTitle = isSynced ? 'Synced with CMMS' : 'Sync With CMMS';

        const isExporting = this.isExporting();
        const exportDisabledAttr = isExporting ? 'disabled="disabled"' : '';
        const exportClass = isExporting ? 'grid-action-pill grid-action-export disabled' : 'grid-action-pill grid-action-export';
        const exportTitle = isExporting ? 'Exporting SRAR...' : 'Export SRAR';

        return `
          <div class="flex items-center gap-2">
            <button class="${syncClass}" title="${syncTitle}" ${disabledAttr}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
                <path d="M3 3v5h5"></path>
                <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
                <path d="M16 16h5v5"></path>
              </svg>
            </button>
            <button class="${exportClass}" title="${exportTitle}" ${exportDisabledAttr}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="9" y1="12" x2="15" y2="12"></line>
                <line x1="9" y1="16" x2="15" y2="16"></line>
              </svg>
            </button>
            <button class="grid-action-pill grid-action-edit" title="Edit SRAR">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.375 2.625a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4Z"></path>
              </svg>
            </button>
          </div>
        `;
      },
    },
  ];

  // --- Step 1 Models ---
  runningParameters: RunningParameters = {
    baselineSinceCommHours: 100,
    baselineSinceCommMinutes: 0,
    baselineSinceCommDistance: 250,
    duringMonthHours: 1,
    duringMonthMinutes: 10,
    duringMonthDistance: "123.00",
    sinceCommHours: "101:10",
    sinceCommDistance: "373.00",
    maxSpeedDuringMonth: "28.5",
    maxSpeedDurationHours: 4,
    maxSpeedDurationMinutes: 30,
    maxSpeedDate: "2026-08-02",
    maxShaftRpm: "245"
  };

  equipments: EquipmentItem[] = [
    { name: "Gas Turbine Generator #1", nomenclature: "Gas Turbine Generator", eqptCode: "GTG-01", subDept: "Electrical", serNo: "GTG-8812", prevHours: "1240:15", monthlyHours: "45:30", cumulativeHours: "1285:45" },
    { name: "Main Propulsion Diesel #1", nomenclature: "Main Propulsion Diesel", eqptCode: "MPD-01", subDept: "Engineering", serNo: "MPD-4410", prevHours: "3200:10", monthlyHours: "115:00", cumulativeHours: "3315:10" },
    { name: "Auxiliary Boiler Feed Pump", nomenclature: "Aux Boiler Feed Pump", eqptCode: "ABFP-01", subDept: "Engineering", serNo: "ABP-1022", prevHours: "980:40", monthlyHours: "20:00", cumulativeHours: "1000:40" },
    { name: "Main Engine Port", nomenclature: "Main Engine", eqptCode: "ME-PORT", subDept: "Engineering", serNo: "ME-01-P", prevHours: "3180:55", monthlyHours: "115:00", cumulativeHours: "3295:55" }
  ];

  defaultEquipments: EquipmentItem[] = [
    { id: 1, name: "Gas Turbine Generator #1", nomenclature: "Gas Turbine Generator", eqptCode: "GTG-01", subDept: "Electrical", serNo: "GTG-8812", prevHours: "1240:15", monthlyHours: "45:30", cumulativeHours: "1285:45" },
    { id: 2, name: "Main Propulsion Diesel #1", nomenclature: "Main Propulsion Diesel", eqptCode: "MPD-01", subDept: "Engineering", serNo: "MPD-4410", prevHours: "3200:10", monthlyHours: "115:00", cumulativeHours: "3315:10" },
    { id: 3, name: "Auxiliary Boiler Feed Pump", nomenclature: "Aux Boiler Feed Pump", eqptCode: "ABFP-01", subDept: "Engineering", serNo: "ABP-1022", prevHours: "980:40", monthlyHours: "20:00", cumulativeHours: "1000:40" },
    { id: 4, name: "Main Engine Port", nomenclature: "Main Engine", eqptCode: "ME-PORT", subDept: "Engineering", serNo: "ME-01-P", prevHours: "3180:55", monthlyHours: "115:00", cumulativeHours: "3295:55" },
    { id: 5, name: "MAIN GAS TURBINE", nomenclature: "Gas Turbine Main Engine", eqptCode: "GT-ME-01", subDept: "Engineering", serNo: "GT-SN-1001", prevHours: "1500:00", monthlyHours: "0:00", cumulativeHours: "1500:00" },
    { id: 6, name: "FUEL TRANSFER PUMP", nomenclature: "Fuel Oil Transfer Pump", eqptCode: "FOTP-01", subDept: "Engineering", serNo: "INV-SN-0001", prevHours: "450:30", monthlyHours: "0:00", cumulativeHours: "450:30" },
    { id: 7, name: "HYDRAULIC POWER PACK", nomenclature: "Hydraulic Power Pack Unit", eqptCode: "HPP-01", subDept: "Engineering", serNo: "INV-SN-0002", prevHours: "820:15", monthlyHours: "0:00", cumulativeHours: "820:15" },
    { id: 8, name: "MISSILE INTERFACE UNIT", nomenclature: "Missile System Interface", eqptCode: "MIU-01", subDept: "Engineering", serNo: "INV-SN-0003", prevHours: "1100:00", monthlyHours: "0:00", cumulativeHours: "1100:00" },
    { id: 9, name: "SERVO MOTOR UNIT", nomenclature: "Servo Control Motor Unit", eqptCode: "SMU-01", subDept: "Engineering", serNo: "INV-SN-0004", prevHours: "340:20", monthlyHours: "0:00", cumulativeHours: "340:20" },
    { id: 10, name: "PRESSURE TEST KIT", nomenclature: "Lube Oil Pressure Test Kit", eqptCode: "PTK-01", subDept: "Engineering", serNo: "INV-SN-0005", prevHours: "120:00", monthlyHours: "0:00", cumulativeHours: "120:00" }
  ];

  // --- Step 2 Models ---
  boilerSteamingData: BoilerSteamingItem[] = [
    {
      eqptName: "Auxiliary Boiler Port",
      nomenclature: "Aux Boiler",
      locOnBoard: "Boiler Room",
      serNo: "AB-992-P",
      hrsSteamedDuringMonth: "10:00",
      hrsSteamedSinceComm: "1240:15",
      hrsAbove80: "2:15",
      lastEstOlgDate: "2025-05-12",
      hrsSteamedSinceLastOlg: "45:30",
      hrsSteamedAtLastOlg: "1194:45",
      lastEstOlgDate2: "2025-05-12",
      hrsSteamedSinceLastOlg2: "45:30",
      hrsSteamedAtLastOlg2: "1194:45",
      lastRetubingDate: "2024-01-01",
      hrsSteamedSinceLastRetubing: "450:20",
      hrsSteamedAtLastRetubing: "790:00",
      lastHydraulicTestDate: "2025-04-10",
      nextInspectionDate: "2026-04-10",
      lifeAssessedMonths: "12"
    }
  ];

  alkalinityData: BoilerAlkalinityItem[] = [
    {
      eqptName: "Auxiliary Boiler Port",
      nomenclature: "Aux Boiler",
      locOnBoard: "Boiler Room",
      serNo: "AB-992-P",
      salinityLastWeek: "15.2",
      chlorideDuringMonth: "12.4",
      excessSalinity: "0.0",
      alkalinityN: "0.045",
      phYarr: "9.2",
      tdsMax750: "120.0",
      phosphate1060: "35.0",
      phosphate0: "0.0",
      alkalinityMax: "150.0",
      alkPpm: "22.0",
      alkalinityPercent: "0.12",
      phJvn: "8.8",
      tdsMax750Jvn: "110.0",
      phosphate1060Jvn: "28.0",
      alkalinityPercentCommon: "0.10"
    }
  ];

  // --- Step 3 Models ---
  activityFromDate = "";
  activityToDate = "";

  private _shipState = "";
  get shipState(): string {
    return this._shipState;
  }
  set shipState(val: string) {
    this._shipState = val;
    this.onShipStateChange(val);
  }

  private _shipLocation = "";
  get shipLocation(): string {
    return this._shipLocation;
  }
  set shipLocation(val: string) {
    this._shipLocation = val;
  }

  private _activityType = "";
  get activityType(): string {
    return this._activityType;
  }
  set activityType(val: string) {
    this._activityType = val;
    this.onActivityTypeChange(val);
  }

  activityDetail = "";
  activityRemarks = "";
  activityDisabledRanges: { from: string; to: string; }[] = [];

  shipStates: string[] = [
    "Material Ready",
    "Material Not Ready",
    "Ship Not Commissioned"
  ];
  shipLocations: string[] = [
    "At Sea",
    "Alongside Home Port",
    "Alongside Away From Home Port"
  ];
  activityTypes: string[] = [
    "Anchorage",
    "Independent Excercises",
    "Operational Excercises",
    "Operational Sea Training",
    "Sea Trials",
    "Special Duty",
    "Ship Not Commissioned"
  ];
  activityDetails: string[] = [
    "NA",
    "IDEF",
    "Tropex",
    "Operational Deployment",
    "Refit - Sea Trials",
    "OSD",
    "POG",
    "HADR"
  ];

  get shipStateOptions(): DropdownOption[] {
    return this.shipStates.map(st => ({ label: st, value: st }));
  }

  get shipLocationOptions(): DropdownOption[] {
    if (!this.shipState) return [];
    if (this.shipState === "Ship Not Commissioned") {
      return [{ label: "Alongside Home Port", value: "Alongside Home Port" }];
    }
    return this.shipLocations.map(loc => ({ label: loc, value: loc }));
  }

  get activityTypeOptions(): DropdownOption[] {
    if (!this.shipLocation) return [];
    if (this.shipState === "Ship Not Commissioned") {
      return [{ label: "Ship Not Commissioned", value: "Ship Not Commissioned" }];
    }
    return this.activityTypes
      .filter(act => act !== "Ship Not Commissioned")
      .map(act => ({ label: act, value: act }));
  }

  get activityDetailOptions(): DropdownOption[] {
    if (this.shipState === "Ship Not Commissioned") {
      return [{ label: "NA", value: "NA" }];
    }

    const type = (this.activityType || "").trim();
    if (!type) {
      return [];
    }

    const lowerType = type.toLowerCase();
    let allowedDetails: string[] = [];

    if (lowerType === "anchorage") {
      allowedDetails = ["NA"];
    } else if (lowerType.includes("independent")) {
      allowedDetails = ["IDEF"];
    } else if (lowerType.includes("operational excercises") || lowerType.includes("operational exercises")) {
      allowedDetails = ["Tropex", "Operational Deployment"];
    } else if (lowerType.includes("operational sea training")) {
      allowedDetails = ["NA"];
    } else if (lowerType.includes("sea trials")) {
      allowedDetails = ["Refit - Sea Trials"];
    } else if (lowerType.includes("special duty")) {
      allowedDetails = ["OSD", "POG", "HADR"];
    } else if (lowerType.includes("ship not commissioned")) {
      allowedDetails = ["NA"];
    } else {
      return this.activityDetails.map(det => ({ label: det, value: det }));
    }

    return allowedDetails.map(det => ({ label: det, value: det }));
  }

  public onShipStateChange(val: string): void {
    if (val === "Ship Not Commissioned") {
      this._shipLocation = "Alongside Home Port";
      this._activityType = "Ship Not Commissioned";
      this.activityDetail = "NA";
    } else if (this._activityType === "Ship Not Commissioned") {
      this._activityType = "";
      this.activityDetail = "";
    }
  }

  public onActivityTypeChange(val: string): void {
    const type = (val || "").trim().toLowerCase();
    if (type === "anchorage") {
      this.activityDetail = "NA";
    } else if (type.includes("independent")) {
      this.activityDetail = "IDEF";
    } else if (type.includes("operational sea training")) {
      this.activityDetail = "NA";
    } else if (type.includes("sea trials")) {
      this.activityDetail = "Refit - Sea Trials";
    } else if (type.includes("ship not commissioned")) {
      this.activityDetail = "NA";
    } else if (type.includes("operational excercises") || type.includes("operational exercises")) {
      const valid = ["Tropex", "Operational Deployment"];
      if (!valid.includes(this.activityDetail)) {
        this.activityDetail = "Tropex";
      }
    } else if (type.includes("special duty")) {
      const valid = ["OSD", "POG", "HADR"];
      if (!valid.includes(this.activityDetail)) {
        this.activityDetail = "OSD";
      }
    }
  }

  activities: ActivityItem[] = [
    {
      dateRange: "2026-06-01 to 2026-06-05",
      shipState: "At Sea",
      shipLocation: "Area Alpha",
      activityType: "Operational",
      activityDetail: "EEZ Patrol",
      remarks: "Routine patrol completed successfully."
    }
  ];

  // --- Step 4 Models ---
  fuelConsumption = {
    bfLastMonth: "120.5",
    received: "450.0",
    consHarbor: "15.2",
    consAnchorage: "10.5",
    consSea: "85.4",
    totalCons: "111.10",
    defueled: "0.0",
    balLeftOnboard: "459.40"
  };

  avcatStatus = {
    bfLastMonth: "1200.0",
    received: "5000.0",
    givenToAc: "800.0",
    usedForTrials: "200.0",
    totalCons: "1000.00",
    defueled: "0.0",
    balLeftOnboard: "5200.00"
  };

  torsionMeterData: TorsionMeterItem[] = [
    {
      srNo: 1,
      nomenclature: "Torsion Meter Port",
      eqptCode: "TM-01-P",
      locOnBoard: "Shaft Tunnel Port",
      opsNonOps: "Ops",
      torsionMeterRdg: "124.5",
      maxRpmAchieved: "250",
      nonOpsSince: "",
      lastCalibrationOn: "2025-01-12",
      nextCalibrationDue: "2026-01-12"
    },
    {
      srNo: 2,
      nomenclature: "Torsion Meter Stbd",
      eqptCode: "TM-02-S",
      locOnBoard: "Shaft Tunnel Stbd",
      opsNonOps: "Ops",
      torsionMeterRdg: "128.2",
      maxRpmAchieved: "252",
      nonOpsSince: "",
      lastCalibrationOn: "2025-01-12",
      nextCalibrationDue: "2026-01-12"
    }
  ];

  // --- Step 5 Models ---
  iccpData: IccpItem[] = [
    {
      srNo: 1,
      nomenclature: "ICCP System Port",
      eqptCode: "ICCP-01-P",
      locOnBoard: "Aft Compartment Port",
      opsNonOps: "Ops",
      nonOpsSince: ""
    },
    {
      srNo: 2,
      nomenclature: "ICCP System Stbd",
      eqptCode: "ICCP-02-S",
      locOnBoard: "Aft Compartment Stbd",
      opsNonOps: "Ops",
      nonOpsSince: ""
    }
  ];

  h2sSensorData: H2SSensorItem[] = [
    {
      srNo: 1,
      nomenclature: "H2S Sensor Compartment 1",
      eqptCode: "H2S-01",
      locOnBoard: "Forward Bilge Space",
      opsNonOps: "Ops",
      nonOpsSince: "",
      lastCalibratedOn: "2025-03-15",
      nextCalibration: "2026-03-15"
    },
    {
      srNo: 2,
      nomenclature: "H2S Sensor Compartment 2",
      eqptCode: "H2S-02",
      locOnBoard: "Aft Bilge Space",
      opsNonOps: "Ops",
      nonOpsSince: "",
      lastCalibratedOn: "2025-03-18",
      nextCalibration: "2026-03-18"
    }
  ];

  stpData: StpItem[] = [
    {
      srNo: 1,
      nomenclature: "Sewage Treatment Plant",
      eqptCode: "STP-01",
      locOnBoard: "Auxiliary Machinery Room No. 2",
      status: "SAT",
      effluentTestDate: "2026-06-10",
      remarks: "Effluent parameters within limits."
    }
  ];

  mffsData: MagazineItem[] = [
    {
      srNo: 1,
      nomenclature: "Magazine Sprinkling System Forward",
      eqptCode: "MFFS-01",
      locOnBoard: "Mag No. 1 Forward",
      status: "SAT",
      lastTrialsTaken: "",
      nextTrialsDue: ""
    },
    {
      srNo: 2,
      nomenclature: "Magazine Sprinkling System Aft",
      eqptCode: "MFFS-02",
      locOnBoard: "Mag No. 2 Aft",
      status: "SAT",
      lastTrialsTaken: "",
      nextTrialsDue: ""
    }
  ];

  // --- Step 6 Models ---
  lubOilCoolantTestKits: TestKitItem[] = [
    {
      description: "Water in Oil Test Kit",
      opsNonOps: "Ops",
      nonOpsSince1: "",
      calibrationDate: "2025-01-10",
      nextCalibrationDueDate: "2026-01-10",
      nonOpsSince2: ""
    },
    {
      description: "TBN Test Kit",
      opsNonOps: "Ops",
      nonOpsSince1: "",
      calibrationDate: "2025-01-12",
      nextCalibrationDueDate: "2026-01-12",
      nonOpsSince2: ""
    }
  ];

  lubOilFuelCentrifuge: CentrifugeItem[] = [
    {
      eqptName: "Lub Oil Purifier No. 1",
      nomenclature: "Purifier",
      eqptCode: "PUR-01",
      serNo: "P-9912",
      locOnBoard: "Purifier Room",
      opsNonOps: "Ops",
      nonOpsSince: "",
      lastCalibratedOn: "2025-02-14",
      nextCalibration: "2026-02-14"
    }
  ];

  // --- Step 7 Models ---
  safetyDeviceChecks: SafetyDeviceItem[] = [
    {
      eqptName: "Main Engine Port",
      nomenclature: "Main Engine",
      eqptSerNo: "ME-9912-P",
      eqptCode: "ME-01-P",
      locOnBoard: "Engine Room Port",
      sdcConductedBy: "Ship Staff",
      dateOfSdc: "2026-05-15",
      sfcGmsKWh: "195.4",
      lastSfcTrialDate: "2026-05-10",
      displacementDuringSfc: "3200",
      status: "SAT"
    }
  ];

  injectorFipCalibration: InjectorFipItem[] = [
    {
      eqptName: "Main Engine Port",
      nomenclature: "Main Engine",
      eqptCode: "ME-01-P",
      locOnBoard: "Engine Room Port",
      fipInMonth: "120:30",
      rhSinceInstallation: "1200:45",
      hrsBelow30: "45",
      hrs30to50: "120",
      hrs50to70: "350",
      hrs70to100: "685",
      lubOilConsCurrentMonth: "250",
      dateOfInjectorCalibration: "2026-02-12",
      occasionsReplacement: "1",
      inOutWhichReplaced: "In",
      fuelConsumptionTons: "15.4",
      remarks: "Performance satisfactory."
    }
  ];

  replacementMajorAssemblies: ReplacementItem[] = [
    {
      eqptName: "Diesel Alternator No. 1",
      eqptSrNumber: "DA-1234",
      dateOfReplacement: "2026-03-05",
      subAssemblyUnitName: "Turbocharger",
      reasonOfReplacement: "Routine",
      lifeSinceInstallation: "12",
      lastCalibratedOn: "2025-01-12",
      nextCalibration: "2026-01-12",
      remarks: ""
    }
  ];

  routinesUndertaken: RoutineItem[] = [
    {
      eqptName: "Main Engine Port",
      eqptSrNumber: "ME-9912-P",
      date: "2026-05-20",
      descriptionForRoutine: "Annual Inspection - Annual overhaul of fuel injectors",
      undertakenByWhom: "OEM"
    }
  ];

  // --- Step 8 Models (DGUF) ---
  dgufGeneratorData = [
    {
      srNo: 1,
      eqptCode: "DG-01",
      eqptName: "Diesel Generator No. 1",
      locOnBoard: "Auxiliary Machinery Room No. 1",
      daNo: "DA-1",
      rhSeaAnchorage: "120:15",
      rhHarbour: "45:30",
      totalRhMonth: "165:45"
    },
    {
      srNo: 2,
      eqptCode: "DG-02",
      eqptName: "Diesel Generator No. 2",
      locOnBoard: "Auxiliary Machinery Room No. 2",
      daNo: "DA-2",
      rhSeaAnchorage: "98:40",
      rhHarbour: "60:00",
      totalRhMonth: "158:40"
    }
  ];

  dgufRunningHoursData = {
    totalRhSea: "218:55",
    hrsUnderway: "120:15",
    anchorage: "98:40",
    drifting: "0:00",
    hrsInHarbour: "105:30",
    hrsShoreSupply: "80:00",
    coldMoves: 2,
    comments: "Shore supply available, minor downtime for maintenance on 12th Jun."
  };

  dgufLimitingValues = {
    limitingValueSea: "0.85",
    actualDgufSea: "0.80",
    reasonExceedingSea: "",
    limitingValueHarbour: "0.50",
    actualDgufHarbour: "0.45",
    reasonExceedingHarbour: ""
  };

  dgufSeaReasonOptions: DropdownOption[] = [
    { label: "Operational Requirement", value: "1" },
    { label: "Unable to maintain power supply in single DG", value: "2" },
    { label: "To meet additional load", value: "3" },
    { label: "Within limit", value: "4" },
    { label: "Any other", value: "5" }
  ];

  dgufHarbourReasonOptions: DropdownOption[] = [
    { label: "Shore supply not available", value: "1" },
    { label: "Ship is at 3rd or 4th berthing position", value: "2" },
    { label: "Sea and Action checks", value: "3" },
    { label: "Machinery / Weapon Trials", value: "4" },
    { label: "Shore DG not available (for ANC ships)", value: "5" },
    { label: "Ship is at foreign port", value: "6" },
    { label: "Shore supply fluctuation", value: "7" },
    { label: "Duty ready ship", value: "8" },
    { label: "Cold Move", value: "9" },
    { label: "Within limit", value: "10" },
    { label: "Any other", value: "11" }
  ];

  // --- Step 9 Models (Full Power Trials) ---
  fptMainEngineGeneral = {
    lastFptDate: "2026-05-15",
    displacement: "3200",
    maxSpeed: "28.5",
    occasionReason: "Routine quarterly trial",
    draughtFwd: "4.8",
    draughtAft: "5.2",
    conductedBy: "Ship Staff",
    torsionMotorReading: "145.2",
    seaState: "State 3",
    remarks: "All parameters normal. Full power achieved."
  };

  // Populated live from CMMS (Ch_Master_Full_Power_Conducted_By) — see loadConductedByOptions()
  fptConductedByOptions: DropdownOption[] = [];

  seaStateOptions: DropdownOption[] = [
    { label: "1", value: "1" },
    { label: "2", value: "2" },
    { label: "3", value: "3" },
    { label: "4", value: "4" },
    { label: "5", value: "5" }
  ];

  fptMainEngineSpecific: FptMainEngineSpecificItem[] = [
    {
      eqptName: "Main Engine Port",
      nomenclature: "Main Engine",
      eqptCode: "ME-01-P",
      locOnBoard: "Engine Room Port",
      serNo: "ME-9912-P",
      fuelRackDbl: "95",
      fciThrottleMarking: "85",
      lastEhmTrialsDate: "2026-05-10",
      pitch: "100%",
      maxRpm: "280",
      ratedPower: "8000",
      maxAchievedPower: "7850",
      remarks: "Satisfactory performance."
    },
    {
      eqptName: "Main Engine Stbd",
      nomenclature: "Main Engine",
      eqptCode: "ME-02-S",
      locOnBoard: "Engine Room Stbd",
      serNo: "ME-9912-S",
      fuelRackDbl: "96",
      fciThrottleMarking: "85",
      lastEhmTrialsDate: "2026-05-10",
      pitch: "100%",
      maxRpm: "282",
      ratedPower: "8000",
      maxAchievedPower: "7900",
      remarks: "Satisfactory performance."
    }
  ];

  fptDieselGeneratorLoad: FptDieselGeneratorLoadItem[] = [
    {
      eqptName: "Diesel Generator No. 1",
      nomenclature: "Diesel Generator",
      eqptCode: "DG-01",
      location: "Auxiliary Machinery Room No. 1",
      eqptSerNo: "DA-1234",
      date: "2026-05-16",
      occasionReason: "Load trial after routine maintenance",
      ratedLoad: "750",
      maxLoadAchieved: "720",
      conductedBy: "Ship Staff",
      lastEhmTrialsDate: "2026-05-10",
      remarks: "Load trial completed successfully."
    }
  ];

  // --- Step 10 Models (Gas Turbine / RG Exploitation) ---
  gasTurbineExploitation: GasTurbineExploitationItem[] = [
    {
      eqptName: "Gas Turbine Port",
      nomenclature: "Gas Turbine",
      eqptCode: "GT-01-P",
      locOnBoard: "Engine Room Port",
      serNo: "GT-9912-P",
      totalRhInMonth: "120:30",
      rhEngine1: "65:30",
      rhEngine2: "55:00",
      totalRhSi: "120:30",
      status: "Ops",
      nonOpsSince: "",
      lastCalibrationDate: "2026-02-12",
      lastEhmTrialDate: "2026-05-10",
      lastFptDate: "2026-05-15",
      fuelExploitation: "15.4",
      rhRegime1InMonth: "20:00",
      rhRegime2InMonth: "30:00",
      rhRegime3InMonth: "10:00",
      gslEngine1_1_0to1_25: "5:30",
      rhRegime1Si: "15:00",
      rhRegime2Si: "25:00",
      rhRegime3Si: "12:00",
      gslEngine2_1_0to1_25: "3:00",
      unscheduledEngagement: "None",
      noOfOccasion: "0",
      noOfRepOrders: "0",
      gslChemQty: "0.0"
    }
  ];

  gtReductionGear: GtReductionGearItem[] = [
    {
      eqptName: "Reduction Gear Port",
      nomenclature: "Reduction Gear",
      eqptCode: "RG-01-P",
      locOnBoard: "Engine Room Port",
      eqptSerNo: "RG-9912-P",
      totalRhInMonth: "120:30",
      totalRhsi: "120:30",
      hoRegimeBelow0_25: "10:00",
      hoRegimeBelow0_25Si: "10:00",
      hoRegime0_25to0_5: "40:00",
      hoRegime0_25to0_5Si: "40:00",
      hoRegime0_5to0_75: "70:30",
      hoRegime0_5to0_75Si: "70:30",
      slidingHours0_25: "2:30",
      slidingHours0_25Si: "2:30",
      serviceLife: "1200:45",
      serviceLifeSi: "1200:45",
      routineRegime1: "12:15",
      routineRegime1Si: "12:15",
      routineRegime2: "45:30",
      routineRegime2Si: "45:30",
      routineRegime3: "62:45",
      routineRegime3Si: "62:45",
      routineRegime4: "0:00",
      routineRegime4Si: "0:00"
    }
  ];

  gtReplacementMajorAssemblies: ReplacementItem[] = [
    {
      eqptName: "Gas Turbine Port",
      eqptSrNumber: "GT-9912-P",
      dateOfReplacement: "2026-04-12",
      subAssemblyUnitName: "Fuel Pump",
      reasonOfReplacement: "Defect",
      lifeSinceInstallation: "18",
      remarks: "Replaced due to low pressure output."
    }
  ];

  gtRoutinesUndertaken: RoutineItem[] = [
    {
      eqptName: "Gas Turbine Port",
      eqptSrNumber: "GT-9912-P",
      date: "2026-05-18",
      descriptionForRoutine: "Annual routine - Annual inspection of fuel valves",
      undertakenByWhom: "Ship Staff"
    }
  ];

  // --- Step 11 Models (GTG Exploitation) ---
  gtgExploitationData: GtgExploitationItem[] = [
    {
      eqptName: "GTG No. 1",
      nomenclature: "Gas Turbine Generator",
      eqptCode: "GTG-01",
      locOnBoard: "GTG Room 1",
      serNo: "GTG-1234",
      rhInSea: "38:40",
      rhInHarbour: "60:00",
      totalRhInMonth: "98:40",
      totalRhsi: "99:50",
      noOfColdStarts: 2,
      noOfColdStartsSi: 2,
      noOfHotStarts: 5,
      noOfHotStartsSi: 5,
      noOfBatteryHotStarts: 4,
      noOfBatteryHotStartsSi: 4,
      noOfBatteryColdStarts: 1,
      noOfBatteryColdStartsSi: 1,
      lastChemClgDateReason: "2026-05-10"
    }
  ];

  gtgReductionGear: GtgReductionGearItem[] = [
    {
      eqptName: "GTG Reduction Gear 1",
      nomenclature: "GTG Reduction Gear",
      eqptCode: "GTG-RG-01",
      locOnBoard: "GTG Room 1",
      serNo: "GTG-RG-1234",
      rgRunningHours: "98:40",
      noOfHotStarts: 5,
      noOfColdStarts: 2,
      rhInHarbour: "60:00",
      rhInSea: "38:40",
      inMonthsSi: "98.6"
    }
  ];

  gtgReplacementMajorAssemblies: ReplacementItem[] = [
    {
      eqptName: "GTG No. 1",
      eqptSrNumber: "GTG-1234",
      dateOfReplacement: "2026-03-05",
      subAssemblyUnitName: "Starter Motor",
      reasonOfReplacement: "Defect",
      lifeSinceInstallation: "24",
      remarks: "Burned out, replaced with spare."
    }
  ];

  gtgRoutinesUndertaken: RoutineItem[] = [
    {
      eqptName: "GTG No. 1",
      eqptSrNumber: "GTG-1234",
      date: "2026-05-12",
      descriptionForRoutine: "Calibration of safety valves",
      undertakenByWhom: "OEM"
    }
  ];

  // --- Step 12 Models (Lubricants) ---
  lubricantData: LubItem[] = [
    { name: "O-156", quantity: 250, unit: "Litre" },
    { name: "OMD-113", quantity: 120, unit: "Litre" }
  ];

  lubricantUnits: string[] = [];

  get lubricantUnitOptions(): DropdownOption[] {
    return this.lubricantUnits.map(u => ({ label: u, value: u }));
  }

  // --- Step 13 Models (RH Extension) ---
  mainEngineRHExtensions: RhExtensionItem[] = [
    {
      eqptShipName: "Main Engine Port",
      eqptName: "Main Engine",
      location: "Engine Room Port",
      serNo: "ME-9912-P",
      onRoutine: "1000 Hours",
      rhDuringTrial: "980:15",
      trialConductedBy: "SS",
      authorityLetter: null,
      authorityLetterRef: "",
      rhdi: "Satisfactory",
      rhExtensionGranted: "100",
      rhLeftExpiry: "20"
    }
  ];

  dieselAlternatorRHExtensions: RhExtensionItem[] = [
    {
      eqptName: "Diesel Generator No. 1",
      location: "Auxiliary Machinery Room No. 1",
      nomenclature: "Diesel Generator",
      serNo: "DA-1234",
      onRoutine: "500 Hours",
      rhDuringTrial: "490:30",
      trialConductedBy: "SS",
      authorityLetter: null,
      authorityLetterRef: "",
      rhExtensionGranted: "50",
      rhLeftExpiry: "10"
    }
  ];

  // --- Step 14 Models (EO Remark / EEF) ---
  eefData: {
    hoursUnderway: string;
    designed: number | null;
    reasonExceeding: string;
    shipRemarks: string;
  } = {
      hoursUnderway: "120:15",
      designed: 1.60,
      reasonExceeding: "Within Limit / SAT",
      shipRemarks: "All systems operational during EEZ patrol."
    };

  eefReasons: string[] = [];

  get eefReasonOptions(): DropdownOption[] {
    return this.eefReasons.map(r => ({ label: r, value: r }));
  }

  // --- Popup Modals State ---
  showAddEquipmentModal = false;
  showAddRoutineModal = false;
  showAddMajorAssemblyModal = false;

  newEquipmentType = {
    selectEquipment: "",
    systemEquipment: "",
    date: "",
    qty: "",
    remarks: ""
  };

  newRoutine = {
    equipment: "",
    routineName: "",
    description: "",
    date: "",
    undertakenBy: ""
  };

  newMajorAssembly = {
    equipment: "",
    date: "",
    unit: "",
    reason: "",
    remarks: ""
  };

  equipmentOptions: DropdownOption[] = [
    { label: "Main Engine Port", value: "Main Engine Port" },
    { label: "Main Engine Stbd", value: "Main Engine Stbd" },
    { label: "Diesel Alternator No. 1", value: "Diesel Alternator No. 1" },
    { label: "Diesel Alternator No. 2", value: "Diesel Alternator No. 2" }
  ];

  get routineEquipmentOptions(): DropdownOption[] {
    if (this.activeSubTab() === 10) {
      return [
        { label: "Gas Turbine Port", value: "Gas Turbine Port" },
        { label: "Gas Turbine Stbd", value: "Gas Turbine Stbd" },
        { label: "Reduction Gear Port", value: "Reduction Gear Port" },
        { label: "Reduction Gear Stbd", value: "Reduction Gear Stbd" }
      ];
    } else if (this.activeSubTab() === 11) {
      return [
        { label: "GTG No. 1", value: "GTG No. 1" },
        { label: "GTG No. 2", value: "GTG No. 2" },
        { label: "GTG Reduction Gear 1", value: "GTG Reduction Gear 1" },
        { label: "GTG Reduction Gear 2", value: "GTG Reduction Gear 2" }
      ];
    } else {
      return [
        { label: "Main Engine Port", value: "Main Engine Port" },
        { label: "Main Engine Stbd", value: "Main Engine Stbd" },
        { label: "Diesel Alternator No. 1", value: "Diesel Alternator No. 1" },
        { label: "Diesel Alternator No. 2", value: "Diesel Alternator No. 2" }
      ];
    }
  }

  get majorAssemblyEquipmentOptions(): DropdownOption[] {
    if (this.activeSubTab() === 10) {
      return [
        { label: "Gas Turbine Port", value: "Gas Turbine Port" },
        { label: "Gas Turbine Stbd", value: "Gas Turbine Stbd" },
        { label: "Reduction Gear Port", value: "Reduction Gear Port" },
        { label: "Reduction Gear Stbd", value: "Reduction Gear Stbd" }
      ];
    } else if (this.activeSubTab() === 11) {
      return [
        { label: "GTG No. 1", value: "GTG No. 1" },
        { label: "GTG No. 2", value: "GTG No. 2" },
        { label: "GTG Reduction Gear 1", value: "GTG Reduction Gear 1" },
        { label: "GTG Reduction Gear 2", value: "GTG Reduction Gear 2" }
      ];
    }
    return [];
  }

  routineNameOptions: DropdownOption[] = [
    { label: "Annual Routine", value: "Annual Routine" },
    { label: "SR Routine", value: "SR Routine" },
    { label: "MR Routine", value: "MR Routine" }
  ];

  routineUndertakenByOptions: DropdownOption[] = [
    { label: "Ship staff", value: "Ship staff" },
    { label: "Trial team", value: "Trial team" },
    { label: "OEM", value: "OEM" }
  ];

  ngOnInit() {
    this.syncSafetyAndFipEquipments();
    this.loadDashboard();
    this.route.queryParams.subscribe((params) => {
      // console.log("🚀 ~ SrarTransactionComponent ~ ngOnInit ~ params:", params)
      if (params["step"]) {
        this.activeSubTab.set(Number(params["step"]) || 15);
      }
      if (params["id"]) {
        this.srarId = +params["id"];
        this.loadReportDetails(this.srarId);
      } else {
        this.loadCarryForwardData();
      }
    });
    this.loadMetadata();
    this.updateDisabledRanges();
    this.loadConductedByOptions();
    this.loadEefDesignedValue();
    this.loadCmmsLubricants();
  }

  // CMMS-backed "Conducted By"/"Trial Conducted By" options, shared across every
  // occurrence of this field in the SRAR forms (SDC, FPT Main Engine, FPT Diesel
  // Alternators, RH Extension).
  loadConductedByOptions(): void {
    this.srarService.getConductedByOptions().subscribe({
      next: (data) => {
        this.fptConductedByOptions = data.map(item => ({ label: item.label, value: item.value }));
      }
    });
  }

  // CMMS-backed lubricant picker (name + unit) for the Add Lubricant modal.
  cmmsLubricantOptions: DropdownOption[] = [];
  cmmsLubricants: { id: string; label: string; value: string; name: string; unit: string; type: string }[] = [];
  loadCmmsLubricants(): void {
    this.srarService.getCmmsLubricants().subscribe({
      next: (data) => {
        this.cmmsLubricants = data;
        this.cmmsLubricantOptions = data.map(item => ({ label: item.label, value: item.value }));
      }
    });
  }

  // CMMS-backed "Designed EEF" value for the ship's class — replaces the previously
  // hardcoded frontend constant. Read-only: it's a ship-class spec value, not
  // something entered per month.
  loadEefDesignedValue(): void {
    this.srarService.getEefDesignedValue().subscribe({
      next: (data) => {
        if (data.designed_eef !== null && data.designed_eef !== undefined) {
          this.eefData.designed = data.designed_eef;
        }
      }
    });
  }

  onSelectedMonthChange(value: string): void {
    this.selectedMonth.set(value);
    if (!this.srarId) {
      this.loadCarryForwardData();
    }
  }

  onSelectedYearChange(value: number): void {
    this.selectedYear.set(value);
    if (!this.srarId) {
      this.loadCarryForwardData();
    }
  }

  // Fetches carry-forward values (fuel/AVCAT balance, R/H since installation) from the
  // previous month's SRAR and seeds this month's defaults from them. Only applies to a
  // brand-new (unsaved) report — an existing report's own saved values always win.
  loadCarryForwardData(): void {
    const month = this.getMonthNumber(this.selectedMonth());
    const year = this.selectedYear();
    this.srarService.getCarryForward(this.shipId, month, year).subscribe({
      next: (data) => {
        this.carryForward = data;
        this.fuelConsumption.bfLastMonth = String(data.fuel_balance_last_month ?? 0);
        this.avcatStatus.bfLastMonth = String(data.avcat_balance_last_month ?? 0);
        this.calculateFuelConsumption();
        this.calculateAvcatStatus();
        this.applyInjectorFipCarryForward();
        this.applyGasTurbineCarryForward();
        this.applyReductionGearCarryForward();
      }
    });
  }

  // Matches a carry-forward row to this month's equipment row the same way the rest of
  // this component already cross-references equipment across tabs: by eqpt_code, falling
  // back to eqpt_name (there is no ShipEquipment id available client-side to match on).
  private findCarryForwardByEquipment<T extends { eqpt_code: string | null; eqpt_name: string | null }>(
    list: T[] | undefined, eqptCode: string | undefined | null, eqptName: string | undefined | null
  ): T | undefined {
    if (!list?.length) return undefined;
    const code = String(eqptCode || "").trim().toLowerCase();
    const name = String(eqptName || "").trim().toLowerCase();
    if (code) {
      const byCode = list.find(row => String(row.eqpt_code || "").trim().toLowerCase() === code);
      if (byCode) return byCode;
    }
    if (name) {
      return list.find(row => String(row.eqpt_name || "").trim().toLowerCase() === name);
    }
    return undefined;
  }

  loadDashboard() {
    this.srarService.getDashboard().subscribe({
      next: (data: SrarRecord[]) => {
        const records = Array.isArray(data) ? data : [];
        const formatted: SrarRecord[] = records.map((item) => {
          const raw = item as unknown as Record<string, unknown>;
          return {
            id: String(item["id"] || ""),
            srarNo: String(item["srarNo"] || `SRAR/${item["year"] || 2026}/${String(item["month"] || 8).padStart(2, "0")}/${String(item["id"]).padStart(3, "0")}`),
            shipName: String(item["shipName"] || ""),
            month: String(item["month"] || "August"),
            year: Number(item["year"] || 2026),
            submissionDate: String(item["submissionDate"] || new Date().toISOString().split("T")[0]),
            approvalStatus: item["approvalStatus"] ? "Sent to CO" : "Draft",
            engineerOfficer: String(item["engineerOfficer"] || "N/A"),
            cmms_sync_status: Boolean(raw["cmms_sync_status"] ?? raw["cmmsSyncStatus"] ?? false),
            cmmsSyncStatus: Boolean(raw["cmms_sync_status"] ?? raw["cmmsSyncStatus"] ?? false)
          };
        });
        this.records.set(formatted);
      },
      error: (err: unknown) => {
        console.error("Failed to load SRAR dashboard:", err);
        this.records.set([]);
      }
    });
  }
  syncWithCMMS(row?: SrarRecord) {
    const month = String(row?.month_name ?? row?.month ?? this.selectedMonth());
    const year = Number(row?.year ?? this.selectedYear());

    this.srarService.syncSrarWithCmms(month, year).subscribe({
      next: (res: SrarCmmsSyncResponse) => {
        if (res && res.status !== false) {
          const msg = res.message || `SRAR sync completed for ${month} ${year}.`;
          this.appService.openAlert("Success", msg, () => {
            this.loadDashboard();
            this.loadMasterEquipmentsFromBackend();
          });
        } else {
          const errorMsg = res?.message || "Sync failed with CMMS.";
          this.appService.openAlert("Error", errorMsg);
        }
      },
      error: (err: HttpErrorLike) => {
        const errorMsg = err?.error?.message || err?.message || "Unable to connect to CMMS API.";
        this.appService.openAlert("Error", errorMsg);
      }
    });
  }

  exportSrarReport(row?: SrarRecord): void {
    const headerId = row?.id;
    if (!headerId) {
      this.appService.openAlert("Error", "Unable to export: SRAR report id is missing.");
      return;
    }

    this.setExportingState(true);
    this.srarService.exportSrarReport(headerId).subscribe({
      next: (res: ExportSrarResponse) => {
        const downloadUrl = res?.download_url;
        if (!downloadUrl) {
          this.setExportingState(false);
          const queuedMsg = res?.message || "SRAR report export has been queued for processing.";
          this.appService.openAlert("Success", queuedMsg);
          return;
        }

        const filename = res?.filename || `SRAR_${row?.year ?? ""}_${row?.month ?? ""}.json`;
        this.srarService.downloadFileBlob(downloadUrl).subscribe({
          next: (blob: Blob) => {
            this.triggerBlobDownload(blob, filename);
            this.setExportingState(false);
          },
          error: (err: HttpErrorLike) => {
            this.setExportingState(false);
            const errorMsg = err?.error?.message || err?.message || "Unable to download the exported SRAR report.";
            this.appService.openAlert("Error", errorMsg);
          }
        });
      },
      error: (err: HttpErrorLike) => {
        this.setExportingState(false);
        const errorMsg = err?.error?.message || err?.message || "Unable to export the SRAR report.";
        this.appService.openAlert("Error", errorMsg);
      }
    });
  }

  private triggerBlobDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  satUnsatOptions: DropdownOption[] = [
    { label: "SAT", value: "SAT" },
    { label: "UNSAT", value: "UNSAT" }
  ];

  parseTimeToMinutes(val: string | number | undefined | null): number {
    if (!val) return 0;
    if (typeof val === "number") return val * 60;
    const str = String(val).trim();
    if (!str.includes(":")) {
      const num = Number.parseFloat(str);
      return Number.isNaN(num) ? 0 : Math.round(num * 60);
    }
    const [h, m] = str.split(":").map(x => Number.parseInt(x, 10) || 0);
    return (h * 60) + m;
  }

  formatMinutesToHHMM(minutes: number): string {
    if (Number.isNaN(minutes) || minutes < 0) return "0:00";
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    return `${h}:${String(m).padStart(2, "0")}`;
  }

  addHHMMTime(t1: string | undefined, t2: string | undefined): string {
    const m1 = this.parseTimeToMinutes(t1 || "0:00");
    const m2 = this.parseTimeToMinutes(t2 || "0:00");
    return this.formatMinutesToHHMM(m1 + m2);
  }

  validateDieselLoadRegimeSum(item: InjectorFipItem): boolean {
    const fipMins = this.parseTimeToMinutes(item.fipInMonth || "0:00");
    const b30 = this.parseTimeToMinutes(item.hrsBelow30 || "0");
    const b3050 = this.parseTimeToMinutes(item.hrs30to50 || "0");
    const b5070 = this.parseTimeToMinutes(item.hrs50to70 || "0");
    const b70100 = this.parseTimeToMinutes(item.hrs70to100 || "0");
    const sum = b30 + b3050 + b5070 + b70100;
    item.isRegimeMismatch = fipMins !== sum;
    return !item.isRegimeMismatch;
  }

  onDgufAnchorageOrDriftingChange(): void {
    this.recalculateDgufSeaHarbourSplit();
  }

  onGtRhInMonthChange(gt: GasTurbineExploitationItem): void {
    gt.totalRhSi = this.addHHMMTime(gt.prevTotalRhSi || "0:00", gt.totalRhInMonth || "0:00");
    gt.rhRegime1Si = this.addHHMMTime(gt.prevRhRegime1Si || "0:00", gt.rhRegime1InMonth || "0:00");
    gt.rhRegime2Si = this.addHHMMTime(gt.prevRhRegime2Si || "0:00", gt.rhRegime2InMonth || "0:00");
    gt.rhRegime3Si = this.addHHMMTime(gt.prevRhRegime3Si || "0:00", gt.rhRegime3InMonth || "0:00");
    this.validateGtLoadRegimeSum(gt);
  }

  validateGtLoadRegimeSum(gt: GasTurbineExploitationItem): boolean {
    const totalMins = this.parseTimeToMinutes(gt.totalRhInMonth || "0:00");
    const r1 = this.parseTimeToMinutes(gt.rhRegime1InMonth || "0:00");
    const r2 = this.parseTimeToMinutes(gt.rhRegime2InMonth || "0:00");
    const r3 = this.parseTimeToMinutes(gt.rhRegime3InMonth || "0:00");
    const sum = r1 + r2 + r3;
    gt.isRegimeMismatch = totalMins !== sum;
    return !gt.isRegimeMismatch;
  }

  // Sets each Gas Turbine row's carry-forward SI baselines from the previous month's
  // SRAR (matched by eqpt_code/eqpt_name) and recomputes this month's displayed SI values.
  applyGasTurbineCarryForward(): void {
    for (const gt of this.gasTurbineExploitation) {
      const prev = this.findCarryForwardByEquipment(
        this.carryForward.gas_turbine, gt.eqptCode, gt.eqptName
      );
      gt.prevTotalRhSi = String(prev?.total_rh_si ?? "0:00");
      gt.prevRhRegime1Si = String(prev?.rh_regime_1_si ?? "0:00");
      gt.prevRhRegime2Si = String(prev?.rh_regime_2_si ?? "0:00");
      gt.prevRhRegime3Si = String(prev?.rh_regime_3_si ?? "0:00");
      this.onGtRhInMonthChange(gt);
    }
  }

  onRgRhInMonthChange(rg: GtReductionGearItem): void {
    rg.totalRhsi = this.addHHMMTime(rg.prevTotalRhsi || "0:00", rg.totalRhInMonth || "0:00");
    rg.hoRegimeBelow0_25Si = this.addHHMMTime(rg.prevHoRegimeBelow0_25Si || "0:00", rg.hoRegimeBelow0_25 || "0:00");
    rg.hoRegime0_25to0_5Si = this.addHHMMTime(rg.prevHoRegime0_25to0_5Si || "0:00", rg.hoRegime0_25to0_5 || "0:00");
    rg.hoRegime0_5to0_75Si = this.addHHMMTime(rg.prevHoRegime0_5to0_75Si || "0:00", rg.hoRegime0_5to0_75 || "0:00");
    this.validateRgLoadRegimeSum(rg);
  }

  validateRgLoadRegimeSum(rg: GtReductionGearItem): boolean {
    const totalMins = this.parseTimeToMinutes(rg.totalRhInMonth || "0:00");
    const r1 = this.parseTimeToMinutes(rg.hoRegimeBelow0_25 || "0:00");
    const r2 = this.parseTimeToMinutes(rg.hoRegime0_25to0_5 || "0:00");
    const r3 = this.parseTimeToMinutes(rg.hoRegime0_5to0_75 || "0:00");
    rg.isRegimeMismatch = totalMins !== (r1 + r2 + r3);
    return !rg.isRegimeMismatch;
  }

  // Sets each Reduction Gear row's carry-forward SI baselines from the previous month's
  // SRAR (matched by eqpt_code/eqpt_name) and recomputes this month's displayed SI values.
  applyReductionGearCarryForward(): void {
    for (const rg of this.gtReductionGear) {
      const prev = this.findCarryForwardByEquipment(
        this.carryForward.reduction_gear, rg.eqptCode, rg.eqptName
      );
      rg.prevTotalRhsi = String(prev?.total_rh_si ?? "0:00");
      rg.prevHoRegimeBelow0_25Si = String(prev?.total_rh_regime1_si ?? "0:00");
      rg.prevHoRegime0_25to0_5Si = String(prev?.total_rh_regime2_si ?? "0:00");
      rg.prevHoRegime0_5to0_75Si = String(prev?.total_rh_regime3_si ?? "0:00");
      this.onRgRhInMonthChange(rg);
    }
  }


  loadMetadata() {
    this.srarService.getShipStates().subscribe({
      next: (data) => {
        if (data && data.length > 0) {
          this.shipStates = data.map((x: LookupItem) => x.name);
        }
      }
    });
    this.srarService.getShipLocations().subscribe({
      next: (data) => {
        if (data && data.length > 0) {
          this.shipLocations = data.map((x: LookupItem) => x.name);
        }
      }
    });
    this.srarService.getActivityTypes().subscribe({
      next: (data: LookupItem[]) => {
        if (data && data.length > 0) {
          this.activityTypes = data.map((x: LookupItem) => x.name);
        }
      }
    });
    this.srarService.getActivityDetails().subscribe({
      next: (data) => {
        if (data && data.length > 0) {
          this.activityDetails = data.map((x: LookupItem) => x.name);
        }
      }
    });
    this.srarService.getLubricantUnits().subscribe({
      next: (data) => {
        if (data && data.length > 0) {
          this.lubricantUnits = data.map((x: LookupItem) => x.name);
        }
      }
    });
    this.srarService.getEefReasons().subscribe({
      next: (data) => {
        if (data && data.length > 0) {
          this.eefReasons = data.map((x: LookupItem) => x.name);
        }
      }
    });
  }


  resetFormForNewReport(): void {
    this.srarId = null;
    this.runningParameters = {
      baselineSinceCommHours: 100,
      baselineSinceCommMinutes: 0,
      baselineSinceCommDistance: 250,
      duringMonthHours: 0,
      duringMonthMinutes: 0,
      duringMonthDistance: "0.00",
      sinceCommHours: "100:00",
      sinceCommDistance: "250.00",
      maxSpeedDuringMonth: "",
      maxSpeedDurationHours: 0,
      maxSpeedDurationMinutes: 0,
      maxSpeedDate: "",
      maxShaftRpm: ""
    };
    this.dgufRunningHoursData = {
      totalRhSea: "00:00",
      hrsUnderway: "00:00",
      anchorage: "00:00",
      drifting: "00:00",
      hrsInHarbour: "00:00",
      hrsShoreSupply: "00:00",
      coldMoves: 0,
      comments: ""
    };
    this.recalculateDgufSeaHarbourSplit();
    this.eoDetails = {
      name: "",
      rank: "",
      personalNo: "",
      contactNo: "",
      writerContactNo: "",
      sendToCo: false
    };
    this.activities = [];
    this.fuelConsumption = {
      bfLastMonth: "0",
      received: "0",
      consHarbor: "0",
      consAnchorage: "0",
      consSea: "0",
      totalCons: "0",
      defueled: "0",
      balLeftOnboard: "0"
    };
    this.avcatStatus = {
      bfLastMonth: "0",
      received: "0",
      givenToAc: "0",
      usedForTrials: "0",
      totalCons: "0",
      defueled: "0",
      balLeftOnboard: "0"
    };
    this.eefData = {
      hoursUnderway: "0:00",
      designed: null,
      reasonExceeding: "",
      shipRemarks: ""
    };

    // Initialize equipments synchronously from default baseline
    this.equipments = this.defaultEquipments.map(d => ({ ...d }));
    this.equipments.forEach(eq => this.calculateEquipmentCumulative(eq));

    this.loadMasterEquipmentsFromBackend();
    this.loadCarryForwardData();
  }

  // Load master equipment list dynamically from backend for Tab 1, merging safely without overwriting prevHours
  loadMasterEquipmentsFromBackend() {
    this.srarService.getEquipments().subscribe({
      next: (eqList: SrarEquipmentLookupRow[]) => {
        if (!eqList || !Array.isArray(eqList) || eqList.length === 0) return;

        // 1. Tab 1: Running Parameters Equipment List (configured in SRAR Master Records)
        this.equipments = eqList.map((item, idx) => {
          const nome = String(item.nomenclature || item.name || item.srar_txt || item.equipment_desc || `Equipment ${idx + 1}`);
          const cat = String(item.srar_type || item.equipment_category_code || "Engineering");
          return {
            id: Number(item.id || idx + 1),
            name: nome,
            nomenclature: nome,
            eqptCode: cat,
            subDept: "Engineering",
            serNo: `SN-${item.id || idx + 1}`,
            prevHours: "100:00",
            monthlyHours: "0:00",
            cumulativeHours: "100:00"
          };
        });

        const matches = (item: SrarEquipmentLookupRow, codes: string[], kw: string[]) => {
          const cat = (item.srar_type || item.equipment_category_code || "").toUpperCase();
          const desc = (item.srar_txt || item.nomenclature || item.name || item.equipment_desc || "").toLowerCase();
          return codes.includes(cat) || kw.some(k => desc.includes(k.toLowerCase()));
        };

        // 2. Tab 2: Boilers (Only if Boiler is added in SRAR Master Records)
        const boilers = eqList.filter(item => matches(item, ["BLR", "BOILER"], ["boiler"]));
        if (boilers.length > 0) {
          this.boilerSteamingData = boilers.map(b => {
            const nome = b.srar_txt || b.nomenclature || b.equipment_desc || "Auxiliary Boiler";
            return {
              eqptName: nome,
              nomenclature: nome,
              locOnBoard: "Boiler Room",
              serNo: `BLR-${b.id}`,
              hrsSteamedDuringMonth: "0:00",
              hrsSteamedSinceComm: "100:00",
              hrsAbove80: "0:00",
              lastEstOlgDate: "", hrsSteamedSinceLastOlg: "", hrsSteamedAtLastOlg: "",
              lastEstOlgDate2: "", hrsSteamedSinceLastOlg2: "", hrsSteamedAtLastOlg2: "",
              lastRetubingDate: "", hrsSteamedSinceLastRetubing: "", hrsSteamedAtLastRetubing: "",
              lastHydraulicTestDate: "", nextInspectionDate: "", lifeAssessedMonths: ""
            };
          });
        }

        // 3. Tab 4: Torsionmeter (Only if Torsionmeter is added in SRAR Master Records)
        const torsions = eqList.filter(item => matches(item, ["TM"], ["torsion"]));
        if (torsions.length > 0) {
          this.torsionMeterData = torsions.map((t, idx) => {
            const nome = t.srar_txt || t.nomenclature || t.equipment_desc || "Torsion Meter";
            return {
              srNo: idx + 1,
              nomenclature: nome,
              eqptCode: `TM-0${idx + 1}`,
              locOnBoard: "Shaft Tunnel",
              opsNonOps: "Ops",
              torsionMeterRdg: "0.0",
              maxRpmAchieved: "0",
              nonOpsSince: "",
              lastCalibrationOn: "",
              nextCalibrationDue: ""
            };
          });
        }

        // 4. Tab 5: ICCP, H2S, STP, MFFS (Only if present in SRAR Master Records)
        const iccps = eqList.filter(item => matches(item, ["ICCP"], ["iccp"]));
        if (iccps.length > 0) {
          this.iccpData = iccps.map((ic, idx) => ({
            srNo: idx + 1, nomenclature: ic.srar_txt || ic.nomenclature || "ICCP System", eqptCode: `ICCP-0${idx + 1}`,
            locOnBoard: "Aft Compartment", opsNonOps: "Ops", nonOpsSince: ""
          }));
        }

        const h2s = eqList.filter(item => matches(item, ["H2S"], ["h2s", "sensor"]));
        if (h2s.length > 0) {
          this.h2sSensorData = h2s.map((h, idx) => ({
            srNo: idx + 1, nomenclature: h.srar_txt || h.nomenclature || "H2S Sensor", eqptCode: `H2S-0${idx + 1}`,
            locOnBoard: "Bilge Space", opsNonOps: "Ops", nonOpsSince: "", lastCalibratedOn: "", nextCalibration: ""
          }));
        }

        const stps = eqList.filter(item => matches(item, ["STP"], ["sewage", "stp"]));
        if (stps.length > 0) {
          this.stpData = stps.map((s, idx) => ({
            srNo: idx + 1, nomenclature: s.srar_txt || s.nomenclature || "Sewage Treatment Plant", eqptCode: `STP-0${idx + 1}`,
            locOnBoard: "AMR No. 2", status: "SAT", effluentTestDate: "", remarks: ""
          }));
        }

        const mffs = eqList.filter(item => matches(item, ["MFFS"], ["magazine", "sprinkling", "mffs"]));
        if (mffs.length > 0) {
          this.mffsData = mffs.map((m, idx) => ({
            srNo: idx + 1, nomenclature: m.srar_txt || m.nomenclature || "Magazine Sprinkling System", eqptCode: `MFFS-0${idx + 1}`,
            locOnBoard: "Magazine Space", status: "SAT", lastTrialsTaken: "", nextTrialsDue: ""
          }));
        }

        // 5. Tab 6: Centrifuge (Only if present in SRAR Master Records)
        const cfgs = eqList.filter(item => matches(item, ["CFG"], ["centrifuge", "purifier"]));
        if (cfgs.length > 0) {
          this.lubOilFuelCentrifuge = cfgs.map(c => {
            const nome = c.srar_txt || c.nomenclature || c.equipment_desc || "Purifier";
            return {
              eqptName: nome, nomenclature: nome, eqptCode: `PUR-01`, serNo: `P-${c.id}`,
              locOnBoard: "Purifier Room", opsNonOps: "Ops", nonOpsSince: "", lastCalibratedOn: "", nextCalibration: ""
            };
          });
        }

        // 6. Tab 8: DGUF & Diesel Generators (Only if present in SRAR Master Records)
        const dgs = eqList.filter(item => matches(item, ["DA", "DG", "PGE"], ["diesel", "generator", "alternator"]));
        if (dgs.length > 0) {
          this.dgufGeneratorData = dgs.map((d, idx) => {
            const nome = d.srar_txt || d.nomenclature || d.equipment_desc || `Diesel Generator No. ${idx + 1}`;
            return {
              srNo: idx + 1,
              eqptCode: `DG-0${idx + 1}`,
              eqptName: nome,
              locOnBoard: `AMR No. ${idx + 1}`,
              daNo: `DA-${idx + 1}`,
              rhSeaAnchorage: "0:00",
              rhHarbour: "0:00",
              totalRhMonth: "0:00"
            };
          });
        }

        // 7. Tab 10: GT & RG (Only if present in SRAR Master Records)
        const gts = eqList.filter(item => matches(item, ["GT"], ["gas turbine"]));
        if (gts.length > 0) {
          this.gasTurbineExploitation = gts.map(g => {
            const nome = g.srar_txt || g.nomenclature || g.equipment_desc || "Gas Turbine";
            return {
              eqptName: nome, nomenclature: nome, eqptCode: `GT-01`, locOnBoard: "Engine Room",
              serNo: `GT-${g.id}`, totalRhInMonth: "0:00", rhEngine1: "0:00", rhEngine2: "0:00", totalRhSi: "0:00",
              status: "Ops", nonOpsSince: "", lastCalibrationDate: "", lastEhmTrialDate: "", lastFptDate: "", fuelExploitation: "0.0",
              rhRegime1InMonth: "0:00", rhRegime2InMonth: "0:00", rhRegime3InMonth: "0:00", gslEngine1_1_0to1_25: "0:00",
              rhRegime1Si: "0:00", rhRegime2Si: "0:00", rhRegime3Si: "0:00", gslEngine2_1_0to1_25: "0:00",
              unscheduledEngagement: "None", noOfOccasion: "0", noOfRepOrders: "0", gslChemQty: "0.0"
            };
          });
        }

        const rgs = eqList.filter(item => matches(item, ["RG", "RG(GT)"], ["reduction gear"]));
        if (rgs.length > 0) {
          this.gtReductionGear = rgs.map((r, idx) => {
            const nome = r.srar_txt || r.nomenclature || r.equipment_desc || "Reduction Gear";
            return {
              eqptName: nome, nomenclature: nome, eqptCode: `RG-0${idx + 1}`, locOnBoard: "Engine Room",
              eqptSerNo: `RG-${r.id}`, totalRhInMonth: "0:00", totalRhsi: "0:00",
              hoRegimeBelow0_25: "0:00", hoRegimeBelow0_25Si: "0:00",
              hoRegime0_25to0_5: "0:00", hoRegime0_25to0_5Si: "0:00",
              hoRegime0_5to0_75: "0:00", hoRegime0_5to0_75Si: "0:00",
              slidingHours0_25: "0:00", slidingHours0_25Si: "0:00",
              serviceLife: "0:00", serviceLifeSi: "0:00",
              routineRegime1: "0:00", routineRegime1Si: "0:00",
              routineRegime2: "0:00", routineRegime2Si: "0:00",
              routineRegime3: "0:00", routineRegime3Si: "0:00",
              routineRegime4: "0:00", routineRegime4Si: "0:00"
            };
          });
        }

        // Tab 9: Full Power Trials - Main Engine (Equipment Wise) & Diesel Alternators
        const mainEngines = eqList.filter(item => matches(item, ["ME"], ["main engine"]));
        if (mainEngines.length > 0) {
          this.fptMainEngineSpecific = mainEngines.map((m, idx) => {
            const nome = m.srar_txt || m.nomenclature || m.equipment_desc || "Main Engine";
            return {
              eqptName: nome, nomenclature: nome, eqptCode: `ME-0${idx + 1}`, locOnBoard: "Engine Room",
              serNo: `ME-${m.id}`, fuelRackDbl: "0", fciThrottleMarking: "0", lastEhmTrialsDate: "",
              pitch: "0", maxRpm: "0", ratedPower: "0", maxAchievedPower: "0", remarks: ""
            };
          });
        }

        if (dgs.length > 0) {
          this.fptDieselGeneratorLoad = dgs.map((d, idx) => {
            const nome = d.srar_txt || d.nomenclature || d.equipment_desc || `Diesel Alternator No. ${idx + 1}`;
            return {
              eqptName: nome, nomenclature: nome, eqptCode: `DA-0${idx + 1}`, location: `AMR No. ${idx + 1}`,
              eqptSerNo: `DA-${d.id}`, date: "", occasionReason: "", ratedLoad: "0", maxLoadAchieved: "0",
              conductedBy: "", lastEhmTrialsDate: "", remarks: ""
            };
          });
        }

        // 8. Tab 11: GTG (Only if present in SRAR Master Records)
        const gtgs = eqList.filter(item => matches(item, ["GTG"], ["gtg", "gas turbine generator"]));
        if (gtgs.length > 0) {
          this.gtgExploitationData = gtgs.map(g => {
            const nome = g.srar_txt || g.nomenclature || g.equipment_desc || "GTG";
            return {
              eqptName: nome, nomenclature: nome, eqptCode: `GTG-01`, locOnBoard: "GTG Room",
              serNo: `GTG-${g.id}`, rhInSea: "0:00", rhInHarbour: "0:00", totalRhInMonth: "0:00", totalRhsi: "0:00",
              noOfColdStarts: 0, noOfColdStartsSi: 0, noOfHotStarts: 0, noOfHotStartsSi: 0,
              noOfBatteryHotStarts: 0, noOfBatteryHotStartsSi: 0, noOfBatteryColdStarts: 0, noOfBatteryColdStartsSi: 0,
              lastChemClgDateReason: ""
            };
          });
        }

        if (!this.srarId) {
          this.applyInjectorFipCarryForward();
          this.applyGasTurbineCarryForward();
          this.applyReductionGearCarryForward();
        }
      },
      error: (err: unknown) => console.error("Failed to load configured SRAR Master Records:", err)
    });
  }

  onFillDetails(): void {
    const existingRecord = this.findExistingRecordForSelection();
    if (existingRecord?.id) {
      this.srarId = Number(existingRecord.id);
      this.loadReportDetails(this.srarId);
    } else {
      this.resetFormForNewReport();
    }
    this.activeSubTab.set(1);
    this.showDetails.set(true);
  }

  backToSelect(): void {
    this.showDetails.set(false);
  }

  onGridReady(event: GridReadyEvent): void {
    this.gridApi = event.api;
    if (event?.api) {
      event.api.paginationGetPageSize();
    }
  }

  onCellClicked(event: CellCallbackParams): void {
    if (event.colDef?.headerName === "Action") {
      const domEvent = (event as Record<string, unknown>)['event'] as MouseEvent | undefined;
      const target = domEvent?.target as HTMLElement | null;

      const syncBtn = target?.closest('.grid-action-sync') as HTMLButtonElement | null;
      if (syncBtn) {
        const row = event.data as SrarRecord | undefined;
        const isSynced = Boolean(row?.cmms_sync_status ?? row?.cmmsSyncStatus ?? false);
        if (isSynced || syncBtn.hasAttribute('disabled') || syncBtn.classList.contains('disabled')) {
          return;
        }
        this.syncWithCMMS(row);
        return;
      }

      const exportBtn = target?.closest('.grid-action-export') as HTMLButtonElement | null;
      if (exportBtn) {
        if (this.isExporting() || exportBtn.hasAttribute('disabled') || exportBtn.classList.contains('disabled')) {
          return;
        }
        const row = event.data as SrarRecord | undefined;
        this.exportSrarReport(row);
        return;
      }

      this.onFillDetails();
    }
  }

  setSubTab(subTabId: number) {
    this.activeSubTab.set(subTabId);
  }

  saveAndNext() {
    if (this.activeSubTab() < 15) {
      this.activeSubTab.set(this.activeSubTab() + 1);
    } else if (this.activeSubTab() === 15) {
      this.submitSRARWithValidation();
    }
  }

  saveDraftProgress(callback?: (success: boolean) => void) {
    const currentStep = this.activeSubTab();
    const errorMsg = this.getStepValidationError(currentStep);

    if (errorMsg) {
      this.appService.openAlert(
        "Validation Error",
        `Cannot save Step ${currentStep}: ${errorMsg}`
      );
      if (callback) callback(false);
      return;
    }

    this.saveReportPayload(false, (success) => {
      if (success) {
        this.appService.openAlert("Success", "Draft Progress Saved Successfully", () => {
          // this.loadDashboard();
        });
      }
      if (callback) callback(success);
    });
  }

  submitSRARWithValidation() {
    const invalidSteps: number[] = [];
    for (let s = 1; s <= 14; s++) {
      if (!this.isStepValid(s)) {
        invalidSteps.push(s);
      }
    }

    if (invalidSteps.length > 0) {
      const stepStr = invalidSteps.join(", ");
      this.appService.openAlert(
        "Incomplete Report",
        `Please complete mandatory fields in Step(s) [${stepStr}] before submitting to CO.`,
        () => {
          this.activeSubTab.set(invalidSteps[0]);
        }
      );
      return;
    }

    this.toggleEoDetailsModal(true);
  }

  toggleEoDetailsModal(show: boolean) {
    this.showEoDetailsModal.set(show);
  }

  isEoDetailsValid(): boolean {
    return !!(
      this.eoDetails.writerContactNo?.trim() &&
      this.eoDetails.rank?.trim() &&
      this.eoDetails.name?.trim() &&
      this.eoDetails.personalNo?.trim() &&
      this.eoDetails.contactNo?.trim()
    );
  }

  submitSRARFromModal() {
    if (!this.isEoDetailsValid()) {
      this.appService.openAlert("Validation Error", "Please fill in all required EO Details fields before sending.");
      return;
    }
    this.toggleEoDetailsModal(false);
    this.saveReportPayload(true, (success) => {
      if (success) {
        this.appService.openAlert("Success", "SRAR Report Finalized and Submitted to CO successfully", () => {
          this.showDetails.set(false);
          this.loadDashboard();
          this.activeSubTab.set(1);
        });
      }
    });
  }

  nextSubTab() {
    if (this.activeSubTab() < 15) {
      this.activeSubTab.set(this.activeSubTab() + 1);
    }
  }

  prevSubTab() {
    if (this.activeSubTab() > 1) {
      this.activeSubTab.set(this.activeSubTab() - 1);
    }
  }

  // --- Field Validation & Sanitization Helpers ---
  allowOnlyNumbers(event: KeyboardEvent): boolean {
    const charCode = event.which ? event.which : event.keyCode;
    if ([8, 9, 13, 27, 46, 37, 38, 39, 40].includes(charCode)) {
      return true;
    }
    if ((charCode >= 48 && charCode <= 57) || (charCode >= 96 && charCode <= 105)) {
      return true;
    }
    event.preventDefault();
    return false;
  }

  allowOnlyDecimals(event: KeyboardEvent, currentValue: string | number): boolean {
    const charCode = event.which ? event.which : event.keyCode;
    if ([8, 9, 13, 27, 46, 37, 38, 39, 40].includes(charCode)) {
      return true;
    }
    if ((charCode === 190 || charCode === 110) && !String(currentValue || "").includes(".")) {
      return true;
    }
    if ((charCode >= 48 && charCode <= 57) || (charCode >= 96 && charCode <= 105)) {
      return true;
    }
    event.preventDefault();
    return false;
  }

  sanitizeNumericField(obj: Record<string, unknown>, key: string, isDecimal = false): void {
    if (!obj || !key) return;
    const val = String(obj[key] || "");
    if (isDecimal) {
      let cleaned = val.replace(/[^0-9.]/g, "");
      const parts = cleaned.split(".");
      if (parts.length > 2) {
        cleaned = parts[0] + "." + parts.slice(1).join("");
      }
      obj[key] = cleaned;
    } else {
      obj[key] = val.replace(/\D/g, "");

    }
  }

  // --- Calculation & Normalization Helpers ---
  get selectedMonthStartDate(): string {
    const monthNo = this.getMonthNumber(this.selectedMonth());
    const year = Number(this.selectedYear()) || new Date().getFullYear();
    return `${year}-${String(monthNo).padStart(2, "0")}-01`;
  }

  get selectedMonthEndDate(): string {
    const monthNo = this.getMonthNumber(this.selectedMonth());
    const year = Number(this.selectedYear()) || new Date().getFullYear();
    const lastDay = new Date(year, monthNo, 0).getDate();
    return `${year}-${String(monthNo).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
  }

  ngAfterViewChecked(): void {
    this.standardizeSrarDateInputs();
  }

  private standardizeSrarDateInputs(): void {
    const minDate = this.selectedMonthStartDate;
    const maxDate = this.selectedMonthEndDate;
    const host = this.hostElement.nativeElement as HTMLElement;
    const dateInputs = host.querySelectorAll('input[type="date"]') as NodeListOf<HTMLInputElement>;
    dateInputs.forEach((input: HTMLInputElement) => {
      this.renderer.setAttribute(input, "min", minDate);
      this.renderer.setAttribute(input, "max", maxDate);

      if (!input.dataset["srarDateGuard"]) {
        this.renderer.listen(input, "change", () => this.validateSrarDateInput(input));
        input.dataset["srarDateGuard"] = "true";
      }
      this.validateSrarDateInput(input, false);
    });
  }

  private validateSrarDateInput(input: HTMLInputElement, showAlert = true): void {
    const value = input.value;
    if (!value) return;

    const minDate = this.selectedMonthStartDate;
    const maxDate = this.selectedMonthEndDate;
    if (value >= minDate && value <= maxDate) return;

    input.value = "";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    if (showAlert) {
      this.appService.openAlert(
        "Validation Warning",
        `Date must be within ${this.selectedMonth()} ${this.selectedYear()}.`
      );
    }
  }

  getMaxHoursForSelectedMonth(): { maxHours: number; days: number; monthName: string; year: number } {
    const rawMonth = this.selectedMonth();
    const year = Number(this.selectedYear()) || new Date().getFullYear();
    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];

    let monthNum = 8;
    if (typeof rawMonth === "number") {
      monthNum = rawMonth;
    } else {
      const parsed = parseInt(String(rawMonth), 10);
      if (!isNaN(parsed) && parsed >= 1 && parsed <= 12) {
        monthNum = parsed;
      } else {
        const foundIndex = monthNames.findIndex(
          m => m.toLowerCase().startsWith(String(rawMonth).toLowerCase())
        );
        if (foundIndex !== -1) monthNum = foundIndex + 1;
      }
    }

    const days = new Date(year, monthNum, 0).getDate();
    const maxHours = days * 24;
    const monthName = monthNames[monthNum - 1] || "Selected Month";

    return { maxHours, days, monthName, year };
  }

  normalizeHoursMinutes(obj: Record<string, FormItemValue> | RunningParameters, hrsProp: string, minProp: string) {
    let hrs = Number.parseInt(String(obj[hrsProp] || 0), 10) || 0;
    let mins = Number.parseInt(String(obj[minProp] || 0), 10) || 0;
    if (mins >= 60) {
      const extraHrs = Math.floor(mins / 60);
      mins = mins % 60;
      hrs += extraHrs;
      obj[hrsProp] = hrs;
      obj[minProp] = mins;
    }

    const { maxHours, days, monthName, year } = this.getMaxHoursForSelectedMonth();
    if (hrs > maxHours) {
      this.appService.openAlert(
        "Validation Warning",
        `Entered hours (${hrs} hrs) exceed maximum allowed limit of ${maxHours} hours for ${monthName} ${year} (${days} days). Value reset to ${maxHours} hrs.`
      );
      obj[hrsProp] = maxHours;
    }

    if ((obj as unknown) === this.runningParameters) {
      this.updateSinceComm();
    }
  }

  updateSinceComm() {
    const rh = this.runningParameters;
    const baseHrs = Number.parseInt(String(rh.baselineSinceCommHours || 0), 10) || 0;
    const baseMins = Number.parseInt(String(rh.baselineSinceCommMinutes || 0), 10) || 0;
    const baseDist = Number.parseFloat(String(rh.baselineSinceCommDistance || 0)) || 0;

    const monthHrs = Number.parseInt(String(rh.duringMonthHours || 0), 10) || 0;
    const monthMins = Number.parseInt(String(rh.duringMonthMinutes || 0), 10) || 0;
    const monthDist = Number.parseFloat(String(rh.duringMonthDistance || 0)) || 0;

    let totalMins = baseMins + monthMins;
    const totalHrs = baseHrs + monthHrs + Math.floor(totalMins / 60);
    totalMins = totalMins % 60;

    rh.sinceCommHours = `${totalHrs}:${String(totalMins).padStart(2, "0")}`;

    const totalDist = baseDist + monthDist;
    rh.sinceCommDistance = totalDist.toFixed(2);

    const monthlyUnderway = `${monthHrs}:${String(monthMins).padStart(2, "0")}`;
    this.dgufRunningHoursData.hrsUnderway = monthlyUnderway;
    this.recalculateDgufSeaHarbourSplit();
    this.eefData.hoursUnderway = monthlyUnderway;
  }

  onStatusChange(row: Record<string, unknown>) {
    const status = String(row["opsNonOps"] || row["status"] || "");
    if (status === "Ops" || status === "Operational" || status === "SAT") {
      row["nonOpsSince"] = "";
    }
    if (status === "Non-Ops" || status === "Not Held") {
      if ("lastCalibrationOn" in row) row["lastCalibrationOn"] = "";
      if ("nextCalibrationDue" in row) row["nextCalibrationDue"] = "";
      if ("lastCalibratedOn" in row) row["lastCalibratedOn"] = "";
      if ("nextCalibration" in row) row["nextCalibration"] = "";
      if ("calibrationDate" in row) row["calibrationDate"] = "";
      if ("nextCalibrationDueDate" in row) row["nextCalibrationDueDate"] = "";
    }
  }

  calculateEquipmentCumulative(eq: EquipmentItem) {
    if (!eq.monthlyHours) eq.monthlyHours = "0:00";
    if (!eq.prevHours) eq.prevHours = "0:00";

    this.normalizeHHMM(eq, "monthlyHours");

    const prevParts = String(eq.prevHours).split(":");
    const monthParts = String(eq.monthlyHours).split(":");

    const prevHrs = Number.parseInt(prevParts[0], 10) || 0;
    const prevMins = Number.parseInt(prevParts[1], 10) || 0;

    const monthHrs = Number.parseInt(monthParts[0], 10) || 0;
    const monthMins = Number.parseInt(monthParts[1], 10) || 0;

    let totalMins = prevMins + monthMins;
    const totalHrs = prevHrs + monthHrs + Math.floor(totalMins / 60);
    totalMins = totalMins % 60;

    eq.cumulativeHours = `${totalHrs}:${String(totalMins).padStart(2, "0")}`;
  }

  calculateFuelConsumption() {
    const fc = this.fuelConsumption;
    const harbor = Number.parseFloat(fc.consHarbor as string) || 0;
    const anchorage = Number.parseFloat(fc.consAnchorage as string) || 0;
    const sea = Number.parseFloat(fc.consSea as string) || 0;
    const totalCons = harbor + anchorage + sea;
    fc.totalCons = totalCons.toFixed(2);

    const bf = Number.parseFloat(fc.bfLastMonth as string) || 0;
    const rec = Number.parseFloat(fc.received as string) || 0;
    const defueled = Number.parseFloat(fc.defueled as string) || 0;
    const bal = (bf + rec) - defueled - totalCons;
    fc.balLeftOnboard = bal.toFixed(2);
  }

  calculateAvcatStatus() {
    const ac = this.avcatStatus;
    const givenToAc = Number.parseFloat(ac.givenToAc as string) || 0;
    const usedForTrials = Number.parseFloat(ac.usedForTrials as string) || 0;
    const totalCons = givenToAc + usedForTrials;
    ac.totalCons = totalCons.toFixed(2);

    const bf = Number.parseFloat(ac.bfLastMonth as string) || 0;
    const rec = Number.parseFloat(ac.received as string) || 0;
    const defueled = Number.parseFloat(ac.defueled as string) || 0;
    const bal = (bf + rec) - defueled - totalCons;
    ac.balLeftOnboard = bal.toFixed(2);
  }

  normalizeHHMM(obj: Record<string, FormItemValue>, prop: string) {
    const val = obj[prop];
    if (val && typeof val === "string") {
      const parts = val.includes(":") ? val.split(":") : [val, "0"];
      if (parts.length !== 2) return;

      let hrs = Number.parseInt(parts[0], 10) || 0;
      let mins = Number.parseInt(parts[1], 10) || 0;
      if (mins >= 60) {
        const extraHrs = Math.floor(mins / 60);
        mins = mins % 60;
        hrs += extraHrs;
      }

      const { maxHours, days, monthName, year } = this.getMaxHoursForSelectedMonth();
      if (hrs > maxHours) {
        this.appService.openAlert(
          "Validation Warning",
          `Entered hours (${hrs} hrs) exceed maximum allowed limit of ${maxHours} hours for ${monthName} ${year} (${days} days). Value reset to ${maxHours}:${String(mins).padStart(2, "0")}.`
        );
        hrs = maxHours;
      }

      obj[prop] = `${hrs}:${String(mins).padStart(2, "0")}`;
    }
  }

  isFipRhZero(val: string): boolean {
    if (!val) return false;
    return val === "0" || val === "00:00";
  }

  onFipRhChange(row: InjectorFipItem) {
    this.normalizeHHMM(row, "fipInMonth");
    const prevSI = row.prevRhSinceInstallation || "00:00";
    if (this.isFipRhZero(row.fipInMonth)) {
      row.rhSinceInstallation = prevSI;
      row.hrsBelow30 = "0";
      row.hrs30to50 = "0";
      row.hrs50to70 = "0";
      row.hrs70to100 = "0";
      row.lubOilConsCurrentMonth = "00:00";
      row.occasionsReplacement = "0";
      row.inOutWhichReplaced = "0";
      row.fuelConsumptionTons = "0";
      row.remarks = "";
    } else {
      row.rhSinceInstallation = this.addHHMMTime(prevSI, row.fipInMonth);
    }
    this.validateDieselLoadRegimeSum(row);
    this.syncFipRhToDgufTotals();
    this.validateDgufAndFipMatch();
  }

  // Sets each Injector FIP row's carry-forward baseline (R/H Since Installation as of last
  // month) and recomputes this month's displayed value against whatever R/H in Month is
  // already filled in, matched to the previous month's row by eqpt_code/eqpt_name.
  applyInjectorFipCarryForward(): void {
    for (const row of this.injectorFipCalibration) {
      const prev = this.findCarryForwardByEquipment(
        this.carryForward.injector_fip, row.eqptCode, row.eqptName
      );
      row.prevRhSinceInstallation = String(prev?.running_hours_since_installation || "00:00");
      if (!this.isFipRhZero(row.fipInMonth)) {
        row.rhSinceInstallation = this.addHHMMTime(row.prevRhSinceInstallation, row.fipInMonth);
      } else {
        row.rhSinceInstallation = row.prevRhSinceInstallation;
      }
    }
  }

  hhmmToMins(val: string): number {
    if (!val) return 0;
    if (!val.includes(":")) return (parseInt(val, 10) || 0) * 60;
    const parts = val.split(":");
    return (parseInt(parts[0], 10) || 0) * 60 + (parseInt(parts[1], 10) || 0);
  }

  minsToHHMM(mins: number): string {
    if (!mins || isNaN(mins) || mins < 0) return "00:00";
    const h = Math.floor(mins / 60);
    const m = Math.floor(mins % 60);
    return `${h}:${m.toString().padStart(2, "0")}`;
  }

  calculateGtgRh(row: GtgExploitationItem) {
    this.normalizeHHMM(row, "rhInHarbour");
    this.normalizeHHMM(row, "rhInSea");

    const harbourMins = this.hhmmToMins(row.rhInHarbour);
    const seaMins = this.hhmmToMins(row.rhInSea);
    const totalMonthMins = harbourMins + seaMins;

    row.totalRhInMonth = this.minsToHHMM(totalMonthMins);

    const rpMins = (this.runningParameters?.duringMonthHours || 0) * 60 + (this.runningParameters?.duringMonthMinutes || 0);
    row.totalRhsi = this.minsToHHMM(totalMonthMins + rpMins);
  }

  // Single source of truth for the DGUF Sea/Harbour split:
  // (A) Total RH Sea = (B) Hours Underway + (C) Anchorage + (D) Drifting
  // (E) Hours in Harbour = max hours in the selected month − (C) Anchorage − (D) Drifting
  // Anchorage/Drifting are direct user entry in the Sea & Harbour table; Hours Underway
  // comes from Tab 1's running parameters; Total RH Sea and Hours in Harbour are computed.
  recalculateDgufSeaHarbourSplit(): void {
    this.dgufRunningHoursData.hrsUnderway = `${Number(this.runningParameters?.duringMonthHours || 0)}:${String(Number(this.runningParameters?.duringMonthMinutes || 0)).padStart(2, "0")}`;
    this.normalizeHHMM(this.dgufRunningHoursData, "hrsUnderway");
    this.normalizeHHMM(this.dgufRunningHoursData, "anchorage");
    this.normalizeHHMM(this.dgufRunningHoursData, "drifting");

    const { maxHours } = this.getMaxHoursForSelectedMonth();
    const maxMins = maxHours * 60;
    const underwayMins = this.hhmmToMins(this.dgufRunningHoursData.hrsUnderway);
    const anchorageMins = this.hhmmToMins(this.dgufRunningHoursData.anchorage);
    const driftingMins = this.hhmmToMins(this.dgufRunningHoursData.drifting);

    this.dgufRunningHoursData.totalRhSea = this.minsToHHMM(underwayMins + anchorageMins + driftingMins);

    const harbourMins = Math.max(0, maxMins - anchorageMins - driftingMins);
    this.dgufRunningHoursData.hrsInHarbour = this.minsToHHMM(harbourMins);

    if (this.hhmmToMins(this.dgufRunningHoursData.hrsShoreSupply) > harbourMins) {
      this.dgufRunningHoursData.hrsShoreSupply = this.dgufRunningHoursData.hrsInHarbour;
    }

    this.calculateActualDguf();
  }

  syncSafetyAndFipEquipments() {
    this.syncDgufGeneratorsToFip();

    const fipByName = new Map(this.injectorFipCalibration.map(row => [row.eqptName, row]));
    const sdcByName = new Map(this.safetyDeviceChecks.map(row => [row.eqptName, row]));
    const equipmentNames = Array.from(new Set([
      ...this.injectorFipCalibration.map(row => row.eqptName),
      ...this.safetyDeviceChecks.map(row => row.eqptName)
    ]));

    for (const eqptName of equipmentNames) {
      const fip = fipByName.get(eqptName);
      const sdc = sdcByName.get(eqptName);

      if (fip && !sdc) {
        this.safetyDeviceChecks.push({
          eqptName: fip.eqptName,
          nomenclature: fip.nomenclature,
          eqptSerNo: "",
          eqptCode: fip.eqptCode,
          locOnBoard: fip.locOnBoard,
          sdcConductedBy: "Ship Staff",
          dateOfSdc: "",
          sfcGmsKWh: "",
          lastSfcTrialDate: "",
          displacementDuringSfc: "",
          status: "SAT"
        });
      }

      if (sdc && !fip) {
        this.injectorFipCalibration.push({
          eqptName: sdc.eqptName,
          nomenclature: sdc.nomenclature,
          eqptCode: sdc.eqptCode,
          locOnBoard: sdc.locOnBoard,
          fipInMonth: "00:00",
          rhSinceInstallation: "00:00",
          hrsBelow30: "0",
          hrs30to50: "0",
          hrs50to70: "0",
          hrs70to100: "0",
          lubOilConsCurrentMonth: "00:00",
          dateOfInjectorCalibration: "",
          occasionsReplacement: "0",
          inOutWhichReplaced: "",
          fuelConsumptionTons: "0",
          remarks: ""
        });
      }
    }
  }

  isDieselGeneratorFip(row: InjectorFipItem): boolean {
    const name = String(row.eqptName || "").toLowerCase();
    const nomenclature = String(row.nomenclature || "").toLowerCase();
    const code = String(row.eqptCode || "").toLowerCase();
    return name.includes("diesel generator") ||
      name.includes("diesel alternator") ||
      nomenclature.includes("diesel generator") ||
      nomenclature.includes("diesel alternator") ||
      code.startsWith("dg-") ||
      code.startsWith("da-");
  }

  syncDgufGeneratorsToFip() {
    const fipByCode = new Map(this.injectorFipCalibration.map(row => [String(row.eqptCode || "").toLowerCase(), row]));
    const fipByName = new Map(this.injectorFipCalibration.map(row => [String(row.eqptName || "").toLowerCase(), row]));

    for (const dg of this.dgufGeneratorData) {
      const code = String(dg.eqptCode || dg.daNo || "").toLowerCase();
      const name = String(dg.eqptName || dg.daNo || "").toLowerCase();
      const existing = fipByCode.get(code) || fipByName.get(name);

      if (existing) {
        existing.eqptName = dg.eqptName;
        existing.nomenclature = "Diesel Generator";
        existing.eqptCode = dg.eqptCode || dg.daNo;
        existing.locOnBoard = dg.locOnBoard;
        continue;
      }

      this.injectorFipCalibration.push({
        eqptName: dg.eqptName,
        nomenclature: "Diesel Generator",
        eqptCode: dg.eqptCode || dg.daNo,
        locOnBoard: dg.locOnBoard,
        fipInMonth: "00:00",
        rhSinceInstallation: "00:00",
        hrsBelow30: "0",
        hrs30to50: "0",
        hrs50to70: "0",
        hrs70to100: "0",
        lubOilConsCurrentMonth: "00:00",
        dateOfInjectorCalibration: "",
        occasionsReplacement: "0",
        inOutWhichReplaced: "",
        fuelConsumptionTons: "0",
        remarks: ""
      });
    }
    this.syncFipRhToDgufTotals();
  }

  syncFipRhToDgufTotals() {
    const fipByCode = new Map(this.injectorFipCalibration.map(row => [String(row.eqptCode || "").toLowerCase(), row]));
    const fipByName = new Map(this.injectorFipCalibration.map(row => [String(row.eqptName || "").toLowerCase(), row]));

    for (const dg of this.dgufGeneratorData) {
      const code = String(dg.eqptCode || dg.daNo || "").toLowerCase();
      const name = String(dg.eqptName || dg.daNo || "").toLowerCase();
      const fip = fipByCode.get(code) || fipByName.get(name);
      dg.totalRhMonth = fip?.fipInMonth || "00:00";
    }
  }

  onDgufEquipmentRhChange() {
    this.recalculateDgufGeneratorTotals();
    this.validateDgufRowTotals();
    this.validateDgufAndFipMatch();
  }

  recalculateDgufGeneratorTotals() {
    for (const eq of this.dgufGeneratorData) {
      this.normalizeHHMM(eq, "rhSeaAnchorage");
      this.normalizeHHMM(eq, "rhHarbour");
    }
    this.syncFipRhToDgufTotals();
  }

  get dgufEquipmentTotals() {
    const totals = this.dgufGeneratorData.reduce(
      (acc, eq) => {
        acc.seaAnchorageMins += this.hhmmToMins(eq.rhSeaAnchorage);
        acc.harbourMins += this.hhmmToMins(eq.rhHarbour);
        acc.totalMonthMins += this.hhmmToMins(eq.totalRhMonth);
        return acc;
      },
      { seaAnchorageMins: 0, harbourMins: 0, totalMonthMins: 0 }
    );

    return {
      seaAnchorage: this.minsToHHMM(totals.seaAnchorageMins),
      harbour: this.minsToHHMM(totals.harbourMins),
      totalMonth: this.minsToHHMM(totals.totalMonthMins)
    };
  }

  // (E) Hours in Harbour is now computed from maxHoursInMonth − Anchorage − Drifting
  // (see recalculateDgufSeaHarbourSplit); this only validates Shore Supply against it.
  validateDgufShoreSupply() {
    this.normalizeHHMM(this.dgufRunningHoursData, "hrsShoreSupply");

    const harbourMins = this.hhmmToMins(this.dgufRunningHoursData.hrsInHarbour);
    const currentShoreMins = this.hhmmToMins(this.dgufRunningHoursData.hrsShoreSupply);
    if (currentShoreMins > harbourMins) {
      this.appService.openAlert("Error", "Hours shore supply cannot be more than Number of Hours in Harbour.");
      this.dgufRunningHoursData.hrsShoreSupply = this.dgufRunningHoursData.hrsInHarbour;
    }
  }

  calculateActualDguf() {
    const totalSeaMins = this.hhmmToMins(this.dgufRunningHoursData.totalRhSea);
    let sumEquipSeaMins = 0;
    let sumEquipHarbourMins = 0;

    for (const eq of this.dgufGeneratorData) {
      sumEquipSeaMins += this.hhmmToMins(eq.rhSeaAnchorage);
      sumEquipHarbourMins += this.hhmmToMins(eq.rhHarbour);
    }

    if (totalSeaMins > 0) {
      this.dgufLimitingValues.actualDgufSea = (sumEquipSeaMins / totalSeaMins).toFixed(2);
    } else {
      this.dgufLimitingValues.actualDgufSea = "0.00";
    }

    const totalHarbourMins = this.hhmmToMins(this.dgufRunningHoursData.hrsInHarbour);
    if (totalHarbourMins > 0) {
      this.dgufLimitingValues.actualDgufHarbour = (sumEquipHarbourMins / totalHarbourMins).toFixed(2);
    } else {
      this.dgufLimitingValues.actualDgufHarbour = "0.00";
    }

  }

  validateDgufAndFipMatch() {
    if (this.activeSubTab() !== 8) return;

    this.recalculateDgufGeneratorTotals();
    let sumDgufMins = 0;
    for (const eq of this.dgufGeneratorData) {
      if (eq.totalRhMonth) sumDgufMins += this.hhmmToMins(eq.totalRhMonth);
    }

    let sumFipMins = 0;
    for (const fip of this.injectorFipCalibration) {
      if (this.isDieselGeneratorFip(fip) && fip.fipInMonth) {
        sumFipMins += this.hhmmToMins(fip.fipInMonth);
      }
    }

    if (sumDgufMins > 0 || sumFipMins > 0) {
      if (sumDgufMins !== sumFipMins) {
        this.appService.openAlert("Warning", "Total R/H in Month for DGUF does not match the Total R/H in Month for Injector FIP Calibration.");
      }
    }
  }

  validateDgufRowTotals() {
    if (this.activeSubTab() !== 8) return;

    const mismatchedRows = this.dgufGeneratorData.filter((eq) => {
      const expectedMins = this.hhmmToMins(eq.rhSeaAnchorage) + this.hhmmToMins(eq.rhHarbour);
      return this.hhmmToMins(eq.totalRhMonth) !== expectedMins;
    });

    if (mismatchedRows.length > 0) {
      const names = mismatchedRows.map(eq => eq.daNo || eq.eqptName).join(", ");
      this.appService.openAlert(
        "Warning",
        `DGUF Total RH Month must match RH Sea / Anchorage + RH Harbour for: ${names}.`
      );
    }
  }

  get calculatedEEF(): number {
    const hours = this.parseHHMMToHours(this.eefData.hoursUnderway);
    if (hours > 0) {
      return parseFloat((180.45 / hours).toFixed(2));
    }
    return 0.00;
  }

  parseHHMMToHours(value: string): number {
    if (!value) return 0;
    const parts = value.split(":");
    const h = parseInt(parts[0], 10) || 0;
    const m = parseInt(parts[1], 10) || 0;
    return h + (m / 60);
  }

  updateDisabledRanges() {
    this.activityDisabledRanges = this.activities.map(a => {
      const parts = a.dateRange.split(" to ");
      return {
        from: parts[0] || "",
        to: parts[1] || ""
      };
    });
  }

  isDateOverlap(fromDateStr: string, toDateStr: string): boolean {
    if (!fromDateStr || !toDateStr) return false;
    const newFrom = new Date(fromDateStr).getTime();
    const newTo = new Date(toDateStr).getTime();

    for (const act of this.activities) {
      if (!act["dateRange"]) continue;
      const parts = String(act["dateRange"]).split(" to ");
      if (parts.length < 2) continue;
      const existingFrom = new Date(parts[0]).getTime();
      const existingTo = new Date(parts[1]).getTime();

      if (newFrom <= existingTo && newTo >= existingFrom) {
        return true;
      }
    }
    return false;
  }

  addActivity() {
    if (this.activityFromDate && this.activityToDate && this.shipState && this.shipLocation && this.activityType && this.activityDetail) {
      if (new Date(this.activityFromDate) > new Date(this.activityToDate)) {
        this.appService.openAlert("Warning", "From Date cannot be after To Date.");
        return;
      }

      if (this.isDateOverlap(this.activityFromDate, this.activityToDate)) {
        this.appService.openAlert("Warning", "The selected date range overlaps with an already added activity in this month. Please choose a different date range.");
        return;
      }

      this.activities.push({
        dateRange: `${this.activityFromDate} to ${this.activityToDate}`,
        shipState: this.shipState,
        shipLocation: this.shipLocation,
        activityType: this.activityType,
        activityDetail: this.activityDetail,
        remarks: this.activityRemarks || "N/A"
      });
      this.activityFromDate = "";
      this.activityToDate = "";
      this.shipState = "";
      this.shipLocation = "";
      this.activityType = "";
      this.activityDetail = "";
      this.activityRemarks = "";
      this.updateDisabledRanges();
    } else {
      this.appService.openAlert("Warning", "Please fill in all mandatory fields for the ship activity.");
    }
  }

  deleteActivity(index: number) {
    this.activities.splice(index, 1);
    this.updateDisabledRanges();
  }

  // --- Modal Logic ---
  toggleAddEquipmentModal(show: boolean) {
    this.showAddEquipmentModal = show;
    if (show) {
      this.newEquipmentType = {
        selectEquipment: "",
        systemEquipment: "",
        date: "",
        qty: "",
        remarks: ""
      };
    }
  }

  toggleAddRoutineModal(show: boolean) {
    this.showAddRoutineModal = show;
    if (show) {
      this.newRoutine = {
        equipment: "",
        routineName: "",
        description: "",
        date: "",
        undertakenBy: ""
      };
    }
  }

  toggleAddMajorAssemblyModal(show: boolean) {
    this.showAddMajorAssemblyModal = show;
    if (show) {
      this.newMajorAssembly = {
        equipment: "",
        date: "",
        unit: "",
        reason: "",
        remarks: ""
      };
    }
  }

  saveEquipmentType() {
    if (this.newEquipmentType.selectEquipment && this.newEquipmentType.systemEquipment) {
      this.replacementMajorAssemblies.push({
        eqptName: this.newEquipmentType.selectEquipment,
        eqptSrNumber: "DA-" + getRandom4DigitNumber(),
        dateOfReplacement: this.newEquipmentType.date || "2026-06-01",
        subAssemblyUnitName: this.newEquipmentType.systemEquipment,
        reasonOfReplacement: "Routine",
        lifeSinceInstallation: this.newEquipmentType.qty || "12",
        lastCalibratedOn: "2025-01-12",
        nextCalibration: "2026-01-12",
        remarks: this.newEquipmentType.remarks || ""
      });
      this.toggleAddEquipmentModal(false);
    }
  }

  saveRoutine() {
    if (this.newRoutine.equipment && this.newRoutine.routineName) {
      let prefix = "ME-";
      if (this.activeSubTab() === 10) {
        prefix = "GT-";
      } else if (this.activeSubTab() === 11) {
        prefix = "GTG-";
      }

      const routineItem = {
        eqptName: this.newRoutine.equipment,
        eqptSrNumber: prefix + getRandom4DigitNumber(),
        date: this.newRoutine.date || "2026-06-01",
        descriptionForRoutine: `${this.newRoutine.routineName} - ${this.newRoutine.description || ""}`,
        undertakenByWhom: this.newRoutine.undertakenBy || "Ship Staff"
      };

      if (this.activeSubTab() === 10) {
        this.gtRoutinesUndertaken.push(routineItem);
      } else if (this.activeSubTab() === 11) {
        this.gtgRoutinesUndertaken.push(routineItem);
      } else {
        this.routinesUndertaken.push(routineItem);
      }
      this.toggleAddRoutineModal(false);
    }
  }

  deleteRoutine(index: number) {
    if (this.activeSubTab() === 10) {
      this.gtRoutinesUndertaken.splice(index, 1);
    } else if (this.activeSubTab() === 11) {
      this.gtgRoutinesUndertaken.splice(index, 1);
    } else {
      this.routinesUndertaken.splice(index, 1);
    }
  }

  saveMajorAssembly() {
    if (this.newMajorAssembly.equipment) {
      const prefix = this.activeSubTab() === 10 ? "GT-" : "GTG-";
      const item = {
        eqptName: this.newMajorAssembly.equipment,
        eqptSrNumber: prefix + getRandom4DigitNumber(),
        dateOfReplacement: this.newMajorAssembly.date || "2026-06-01",
        subAssemblyUnitName: this.newMajorAssembly.unit || "N/A",
        reasonOfReplacement: this.newMajorAssembly.reason || "Routine",
        lifeSinceInstallation: "12",
        remarks: this.newMajorAssembly.remarks || ""
      };

      if (this.activeSubTab() === 10) {
        this.gtReplacementMajorAssemblies.push(item);
      } else if (this.activeSubTab() === 11) {
        this.gtgReplacementMajorAssemblies.push(item);
      }
      this.toggleAddMajorAssemblyModal(false);
    }
  }

  deleteMajorAssembly(index: number) {
    if (this.activeSubTab() === 10) {
      this.gtReplacementMajorAssemblies.splice(index, 1);
    } else if (this.activeSubTab() === 11) {
      this.gtgReplacementMajorAssemblies.splice(index, 1);
    }
  }

  showAddLubricantModal = signal(false);
  newLubricant: { lubricantId: string; name: string; quantity: number; unit: string } = {
    lubricantId: "", name: "", quantity: 0, unit: ""
  };

  addLubricant() {
    this.newLubricant = { lubricantId: "", name: "", quantity: 0, unit: "" };
    this.showAddLubricantModal.set(true);
  }

  closeAddLubricantModal() {
    this.showAddLubricantModal.set(false);
  }

  onCmmsLubricantSelected(lubricantId: string) {
    this.newLubricant.lubricantId = lubricantId;
    const match = this.cmmsLubricants.find(l => l.value === lubricantId);
    if (match) {
      this.newLubricant.name = match.name;
      this.newLubricant.unit = match.unit || "";
    }
  }

  confirmAddLubricant() {
    if (!this.newLubricant.name) {
      this.appService.openAlert("Validation", "Please select a lubricant.");
      return;
    }
    this.lubricantData.push({
      name: this.newLubricant.name,
      quantity: Math.trunc(this.newLubricant.quantity) || 0,
      unit: this.newLubricant.unit
    });
    this.showAddLubricantModal.set(false);
  }

  deleteLubricant(index: number) {
    this.lubricantData.splice(index, 1);
  }

  // Whether the ship was underway at all this month (Hours Underway in Step 1 / Running
  // Parameters is non-zero). When it wasn't, the ship stayed alongside all month and the
  // operational tabs (fuel, DGUF, etc.) have nothing meaningful to report, so they're not
  // enforced as mandatory. When it was, those tabs are required before final submission.
  isShipUnderwayThisMonth(): boolean {
    const hrs = Number.parseInt(String(this.runningParameters.duringMonthHours || 0), 10) || 0;
    const mins = Number.parseInt(String(this.runningParameters.duringMonthMinutes || 0), 10) || 0;
    return hrs > 0 || mins > 0;
  }

  private validateStep1Error(): string | null {
    if (!this.isShipUnderwayThisMonth()) {
      return null;
    }

    const dist = Number.parseFloat(String(this.runningParameters.duringMonthDistance || 0)) || 0;
    const speed = Number.parseFloat(String(this.runningParameters.maxSpeedDuringMonth || 0)) || 0;
    const durHrs = Number.parseInt(String(this.runningParameters.maxSpeedDurationHours || 0), 10) || 0;
    const durMins = Number.parseInt(String(this.runningParameters.maxSpeedDurationMinutes || 0), 10) || 0;
    const speedDate = String(this.runningParameters.maxSpeedDate || "").trim();
    const shaftRpm = String(this.runningParameters.maxShaftRpm || "").trim();

    if (dist <= 0) return "Distance Run is mandatory when Hours Underway is non-zero.";
    if (speed <= 0) return "Max Speed is mandatory when Hours Underway is non-zero.";
    if (durHrs <= 0 && durMins <= 0) return "Max Speed Duration is mandatory when Hours Underway is non-zero.";
    if (!speedDate) return "Max Speed Date is mandatory when Hours Underway is non-zero.";
    if (!shaftRpm) return "Max Shaft RPM is mandatory when Hours Underway is non-zero.";

    return null;
  }

  getStepValidationError(step: number): string | null {
    if (step === 1) return this.validateStep1Error();

    const underway = this.isShipUnderwayThisMonth();
    if (!underway) {
      return null;
    }

    if (step === 2 && (!this.boilerSteamingData || this.boilerSteamingData.length === 0)) {
      return "Boiler Steaming details must be filled when Hours Underway is non-zero.";
    }
    if (step === 3 && (!this.activities || this.activities.length === 0)) {
      return "At least 1 Ship Activity entry must be added when Hours Underway is non-zero.";
    }
    if (step === 4 && (!this.fuelConsumption.bfLastMonth || !this.fuelConsumption.received || !this.fuelConsumption.totalCons || !this.fuelConsumption.balLeftOnboard)) {
      return "All mandatory Fuel Consumption fields must be filled when Hours Underway is non-zero.";
    }
    if (step === 8 && (!this.dgufGeneratorData || this.dgufGeneratorData.length === 0) && this.parseTimeToMinutes(this.dgufRunningHoursData.totalRhSea) <= 0) {
      return "DGUF details must be filled when Hours Underway is non-zero.";
    }
    return null;
  }

  isStepValid(step: number): boolean {
    return this.getStepValidationError(step) === null;
  }

  findExistingRecordForSelection(): SrarRecord | undefined {
    const selectedMonthNo = this.getMonthNumber(this.selectedMonth());
    const selectedYearNo = Number(this.selectedYear());
    return this.records().find((record) => (
      this.getMonthNumber(record.month) === selectedMonthNo &&
      Number(record.year) === selectedYearNo
    ));
  }

  // --- Backend DTO Mapping & Load / Save API Logic ---
  mapOpsToBackend(val: StringNullable): number | null {
    if (!val) return null;
    const lower = val.toLowerCase().trim();
    if (lower === "ops" || lower === "op" || lower === "1") return 1;
    if (lower === "non ops" || lower === "non op" || lower === "non-ops" || lower === "non-op" || lower === "2") return 2;
    if (lower === "not held" || lower === "not-held" || lower === "3") return 3;
    return 1;
  }

  mapOpsToFrontend(val: OpsValue): string {
    if (val == null) return "Ops";
    const num = Number(val);
    if (num === 1) return "Ops";
    if (num === 2) return "Non-Ops";
    if (num === 3) return "Not Held";
    return "Ops";
  }

  mapConductedByToBackend(val: StringNullable): number {
    const v = (val || "").trim().toUpperCase();
    if (v === "TRIAL TEAM") return 1;
    if (v === "SHIP STAFF" || v === "SS") return 2;
    if (v === "DTTT") return 3;
    if (v === "MTU") return 4;
    if (v === "CTT") return 5;
    if (v === "GTTT") return 6;
    if (v === "CATT") return 7;
    if (v === "CBIU") return 8;
    if (v === "OEM") return 9;
    if (v === "MSETT") return 10;
    return 2;
  }

  mapConductedByToFrontend(val: OpsValue): string {
    if (val == null) return "Ship Staff";
    const num = Number(val);
    if (num === 1) return "Trial Team";
    if (num === 2) return "Ship Staff";
    if (num === 3) return "DTTT";
    if (num === 4) return "MTU";
    if (num === 5) return "CTT";
    if (num === 6) return "GTTT";
    if (num === 7) return "CATT";
    if (num === 8) return "CBIU";
    if (num === 9) return "OEM";
    if (num === 10) return "MSETT";
    return "Ship Staff";
  }

  mapStatusToBackend(val: string | null | undefined): number {
    const v = (val || "").toUpperCase().trim();
    if (v === "SAT" || v === "OPS" || v === "SATISFACTORY") return 1;
    return 2;
  }

  mapStatusToFrontend(val: number | string | null | undefined): string {
    if (val == null) return "SAT";
    const num = Number(val);
    return num === 1 ? "SAT" : "Unsat";
  }

  formatDateToYYYYMMDD(dateStr: string | null | undefined): string | null {
    if (!dateStr || typeof dateStr !== "string") return null;
    const normalized = dateStr.trim().replace(/[\s/]+/g, "-");
    const parts = normalized.split("-");
    if (parts.length !== 3) return null;
    if (parts[0].length === 4) return dateStr;
    const day = parseInt(parts[0], 10);
    let month = 0;
    let year = parseInt(parts[2], 10);
    if (year < 100) year += 2000;
    const monthPart = parts[1].toLowerCase();
    const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    const monthIndex = months.findIndex((m) => monthPart.startsWith(m));
    if (monthIndex !== -1) month = monthIndex + 1;
    else month = parseInt(parts[1], 10);
    if (isNaN(day) || isNaN(month) || isNaN(year)) return null;
    return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  // Backend SAT/Unsat choice fields (STP.effluent_status, Magazine.status) serialize as
  // their stored integer (1/2), not the display label — normalize back to "SAT"/"UNSAT"
  // for the dropdowns, while still accepting an already-textual value.
  satUnsatChoiceToLabel(value: unknown): string {
    const str = String(value ?? "").trim().toLowerCase();
    if (str === "1" || str === "sat" || str === "satisfactory") return "SAT";
    if (str === "2" || str === "unsat" || str === "unsatisfactory") return "UNSAT";
    return "SAT";
  }

  loadReportDetails(id: number) {
    this.srarService.getReportDetails(id).subscribe({
      // eslint-disable-next-line sonarjs/cognitive-complexity
      next: (data) => {
        if (data && data["header"]) {
          const h = data["header"] as Record<string, unknown>;
          const duringHrs = parseInt(String(h["hours_underway_month_hr"] || 0), 10) || 0;
          const duringMins = parseInt(String(h["hours_underway_month_min"] || 0), 10) || 0;
          this.runningParameters = {
            baselineSinceCommHours: 100,
            baselineSinceCommMinutes: 0,
            baselineSinceCommDistance: 250,
            duringMonthHours: duringHrs,
            duringMonthMinutes: duringMins,
            duringMonthDistance: String(h["distance_run_month"] || ""),
            sinceCommHours: "",
            sinceCommDistance: "",
            maxSpeedDuringMonth: String(h["max_speed"] || ""),
            maxSpeedDurationHours: (h["max_duration_hr"] as number) || 0,
            maxSpeedDurationMinutes: (h["max_duration_min"] as number) || 0,
            maxSpeedDate: (h["max_speed_date"] as string) || "",
            maxShaftRpm: String(h["max_shaft_rpm"] || "")
          };
          this.updateSinceComm();
        }
        const stpRows = data?.["tab_5_stp"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(stpRows) && stpRows.length > 0) {
          this.stpData = stpRows.map((row, index) => ({
            srNo: index + 1,
            nomenclature: String(row["nomenclature"] || `STP-0${index + 1}`),
            eqptCode: String(row["eqpt_code"] || `STP-0${index + 1}`),
            locOnBoard: String(row["loc_on_board"] || ""),
            status: this.satUnsatChoiceToLabel(row["effluent_status"]),
            effluentTestDate: String(row["effluent_test_date"] || ""),
            remarks: String(row["remarks"] || "")
          }));
        }
        const magazineRows = data?.["tab_5_magazine"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(magazineRows) && magazineRows.length > 0) {
          this.mffsData = magazineRows.map((row, index) => ({
            srNo: index + 1,
            nomenclature: String(row["nomenclature"] || `MFFS-0${index + 1}`),
            eqptCode: String(row["eqpt_code"] || `MFFS-0${index + 1}`),
            locOnBoard: String(row["loc_on_board"] || ""),
            status: this.satUnsatChoiceToLabel(row["status"]),
            lastTrialsTaken: String(row["last_trials_taken"] || ""),
            nextTrialsDue: String(row["next_trials_due"] || "")
          }));
        }
        const fptRows = data?.["tab_9_fpt_me"] as Record<string, unknown>[] | undefined;
        const fpt = Array.isArray(fptRows) ? fptRows[0] : undefined;
        if (fpt) {
          this.fptMainEngineGeneral = {
            lastFptDate: String(fpt["date"] || ""),
            displacement: String(fpt["displacement"] || ""),
            maxSpeed: String(fpt["max_speed"] || ""),
            occasionReason: String(fpt["occasion_reason"] || ""),
            draughtFwd: String(fpt["draught_fwd"] || ""),
            draughtAft: String(fpt["draught_aft"] || ""),
            conductedBy: String(fpt["conducted_by"] || ""),
            torsionMotorReading: String(fpt["torsion_meter_reading"] || ""),
            seaState: String(fpt["sea_state"] || ""),
            remarks: String(fpt["pending_dr_activities_reason"] || "")
          };
        }
        const fptEquipmentRows = data?.["tab_9_fpt_eq"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(fptEquipmentRows) && fptEquipmentRows.length > 0) {
          this.fptMainEngineSpecific = fptEquipmentRows.map((row) => ({
            eqptName: String(row["eqpt_name"] || ""),
            nomenclature: String(row["nomenclature"] || ""),
            eqptCode: String(row["eqpt_code"] || ""),
            locOnBoard: String(row["loc_on_board"] || ""),
            serNo: String(row["serial_no"] || ""),
            fuelRackDbl: String(row["fuel_rack_dbr_max"] || ""),
            fciThrottleMarking: String(row["marking_max"] || ""),
            lastEhmTrialsDate: String(row["undertaken_on"] || ""),
            pitch: String(row["pitch"] || ""),
            maxRpm: String(row["max_rpm"] || ""),
            ratedPower: String(row["rated_power"] || ""),
            maxAchievedPower: String(row["max_achieved_power"] || ""),
            remarks: String(row["remarks"] || "")
          }));
        }
        const fptDaRows = data?.["tab_9_fpt_da"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(fptDaRows) && fptDaRows.length > 0) {
          this.fptDieselGeneratorLoad = fptDaRows.map((row) => ({
            eqptName: String(row["eqpt_name"] || ""),
            nomenclature: String(row["nomenclature"] || ""),
            eqptCode: String(row["eqpt_code"] || ""),
            location: String(row["loc_on_board"] || ""),
            eqptSerNo: String(row["serial_no"] || ""),
            date: String(row["date"] || ""),
            occasionReason: String(row["occasion"] || ""),
            ratedLoad: String(row["rated_load"] || ""),
            maxLoadAchieved: String(row["max_load_achieved"] || ""),
            conductedBy: String(row["conducted_by"] || ""),
            lastEhmTrialsDate: String(row["last_ehm_trials_undertaken_on"] || ""),
            remarks: String(row["remarks"] || "")
          }));
        }
        const dgufRows = data?.["tab_8_dguf"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(dgufRows) && dgufRows.length > 0) {
          this.dgufGeneratorData = dgufRows.map((row, index) => ({
            srNo: index + 1,
            eqptCode: String(row["serial_no"] || row["eqptCode"] || ""),
            eqptName: String(row["eqptName"] || row["equipment_name"] || `Diesel Generator No. ${index + 1}`),
            locOnBoard: String(row["locOnBoard"] || row["location"] || ""),
            daNo: String(row["da_number"] || row["daNo"] || `DA-${index + 1}`),
            rhSeaAnchorage: String(row["rh_at_sea_and_anchorage"] || "00:00"),
            rhHarbour: String(row["rh_at_port"] || "00:00"),
            totalRhMonth: String(row["total_rh_in_month"] || "00:00")
          }));
        }
        const dgufRh = data?.["tab_8_dguf_running_hours"] as Record<string, unknown> | null | undefined;
        if (dgufRh) {
          this.dgufRunningHoursData = {
            totalRhSea: String(dgufRh["total_rh_at_sea"] || "00:00"),
            hrsUnderway: String(dgufRh["hours_underway"] || "00:00"),
            anchorage: String(dgufRh["anchorage"] || "00:00"),
            drifting: String(dgufRh["drifting"] || "00:00"),
            hrsInHarbour: String(dgufRh["no_of_hours_in_harbour"] || "00:00"),
            hrsShoreSupply: String(dgufRh["hours_shore_supply_avl_when_alongs"] || "00:00"),
            coldMoves: Number(dgufRh["no_of_cold_moves_in_harbour"] || 0),
            comments: String(dgufRh["cmts_wrt_to_non_avl_shore_supply"] || "")
          };
        }
        const gtRows = data?.["tab_10_gas_turbine"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(gtRows) && gtRows.length > 0) {
          this.gasTurbineExploitation = gtRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            nomenclature: String(row["nomenclature"] || ""),
            eqptCode: String(row["eqpt_code"] || ""),
            locOnBoard: String(row["loc_on_board"] || ""),
            serNo: String(row["serial_no"] || ""),
            totalRhInMonth: String(row["total_rh_in_month"] || ""),
            totalRhSi: String(row["total_rh_si"] || ""),
            rhRegime1InMonth: String(row["rh_regime_1_in_mth"] || ""),
            rhRegime1Si: String(row["rh_regime_1_si"] || ""),
            rhRegime2InMonth: String(row["rh_regime_2_in_mth"] || ""),
            rhRegime2Si: String(row["rh_regime_2_si"] || ""),
            rhRegime3InMonth: String(row["rh_regime_3_in_mth"] || ""),
            rhRegime3Si: String(row["rh_regime_3_si"] || ""),
            noOfOccasion: String(row["no_of_cold_starts_in_month"] || ""),
            noOfRepOrders: String(row["no_of_cold_starts_si"] || ""),
            unscheduledEngagement: String(row["no_of_hot_starts_in_month"] || ""),
            fuelExploitation: String(row["no_of_hot_starts_si"] || ""),
            gslChemQty: String(row["no_of_false_starts_in_month"] || ""),
            status: String(row["no_of_false_starts_si"] || ""),
            rhEngine1: String(row["no_of_tech_starts_in_month"] || ""),
            rhEngine2: String(row["no_of_tech_starts_si"] || ""),
            lastCalibrationDate: String(row["no_of_astern_engagements_in_mth"] || ""),
            lastEhmTrialDate: String(row["no_of_astern_engagements_count"] || ""),
            lastFptDate: String(row["no_of_stop_orders_in_mth"] || ""),
            nonOpsSince: "",
            gslEngine1_1_0to1_25: "",
            gslEngine2_1_0to1_25: ""
          }));
        }
        const rgRows = data?.["tab_10_reduction_gear"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(rgRows) && rgRows.length > 0) {
          this.gtReductionGear = rgRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            nomenclature: String(row["nomenclature"] || ""),
            eqptCode: String(row["eqpt_code"] || ""),
            locOnBoard: String(row["loc_on_board"] || ""),
            eqptSerNo: String(row["serial_no"] || ""),
            totalRhInMonth: String(row["total_rh_in_month"] || ""),
            totalRhsi: String(row["total_rh_si"] || ""),
            hoRegimeBelow0_25: String(row["total_rh_regime1_in_month"] || ""),
            hoRegimeBelow0_25Si: String(row["total_rh_regime1_si"] || ""),
            hoRegime0_25to0_5: String(row["total_rh_regime2_in_month"] || ""),
            hoRegime0_25to0_5Si: String(row["total_rh_regime2_si"] || ""),
            hoRegime0_5to0_75: String(row["total_rh_regime3_in_month"] || ""),
            hoRegime0_5to0_75Si: String(row["total_rh_regime3_si"] || ""),
            slidingHours0_25: String(row["trailing_rh_in_month"] || ""),
            slidingHours0_25Si: String(row["trailing_rh_si"] || ""),
            serviceLife: String(row["service_life_in_month"] || ""),
            serviceLifeSi: String(row["service_life_si"] || ""),
            routineRegime1: String(row["no_of_eng_regime1_in_month"] || ""),
            routineRegime1Si: String(row["no_of_eng_regime1_si"] || ""),
            routineRegime2: String(row["no_of_eng_regime2_in_month"] || ""),
            routineRegime2Si: String(row["no_of_eng_regime2_si"] || ""),
            routineRegime3: String(row["no_of_eng_regime3_in_month"] || ""),
            routineRegime3Si: String(row["no_of_eng_regime3_si"] || ""),
            routineRegime4: String(row["no_of_eng_regime4_in_month"] || ""),
            routineRegime4Si: String(row["no_of_eng_regime4_si"] || "")
          }));
        }
        const gtRepRows = data?.["tab_10_replacements"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(gtRepRows)) {
          this.gtReplacementMajorAssemblies = gtRepRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            eqptSrNumber: String(row["eqpt_sr_number"] || row["serial_no"] || ""),
            dateOfReplacement: String(row["date_of_replacement"] || ""),
            subAssemblyUnitName: String(row["unit_sub_units"] || ""),
            reasonOfReplacement: String(row["reason_for_replacement"] || ""),
            lifeSinceInstallation: "",
            remarks: String(row["replacement_remarks"] || "")
          }));
        }
        const gtRoutineRows = data?.["tab_10_srmr"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(gtRoutineRows)) {
          this.gtRoutinesUndertaken = gtRoutineRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            eqptSrNumber: String(row["eqpt_sr_number"] || row["serial_no"] || ""),
            date: String(row["date"] || ""),
            descriptionForRoutine: String(row["description_of_routine"] || ""),
            undertakenByWhom: String(row["undertaken_by_whom"] || "")
          }));
        }
        const gtgRows = data?.["tab_11_gtg"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(gtgRows) && gtgRows.length > 0) {
          this.gtgExploitationData = gtgRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            nomenclature: String(row["nomenclature"] || ""),
            eqptCode: String(row["eqpt_code"] || ""),
            locOnBoard: String(row["loc_on_board"] || ""),
            serNo: String(row["serial_no"] || ""),
            rhInSea: String(row["total_rh_in_sea"] || ""),
            rhInHarbour: String(row["total_rh_in_harbour"] || ""),
            totalRhInMonth: String(row["total_rh_in_month"] || ""),
            totalRhsi: String(row["total_rh_si"] || ""),
            noOfColdStarts: Number(row["no_of_cold_starts_in_month"] || 0),
            noOfColdStartsSi: Number(row["no_of_cold_starts_si"] || 0),
            noOfHotStarts: Number(row["no_of_hot_starts_in_month"] || 0),
            noOfHotStartsSi: Number(row["no_of_hot_starts_si"] || 0),
            noOfBatteryColdStarts: Number(row["no_of_battery_cold_starts_in_month"] || 0),
            noOfBatteryColdStartsSi: Number(row["no_of_battery_cold_starts_si"] || 0),
            noOfBatteryHotStarts: Number(row["no_of_battery_hot_starts_in_month"] || 0),
            noOfBatteryHotStartsSi: Number(row["no_of_battery_hot_starts_si"] || 0),
            lastChemClgDateReason: String(row["date"] || "")
          }));
        }
        const gtgRgRows = data?.["tab_11_gtg_rg"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(gtgRgRows) && gtgRgRows.length > 0) {
          this.gtgReductionGear = gtgRgRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            nomenclature: String(row["nomenclature"] || ""),
            eqptCode: String(row["eqpt_code"] || ""),
            locOnBoard: String(row["loc_on_board"] || ""),
            serNo: String(row["serial_no"] || ""),
            rgRunningHours: String(row["rg_running_hours"] || ""),
            noOfHotStarts: Number(row["no_of_hot_starts"] || 0),
            noOfColdStarts: Number(row["no_of_cold_starts"] || 0),
            rhInHarbour: String(row["rh_in_harbour"] || ""),
            rhInSea: String(row["rh_in_sea"] || ""),
            inMonthsSi: String(row["in_months_si"] || "")
          }));
        }
        const gtgRepRows = data?.["tab_11_gtg_rep"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(gtgRepRows)) {
          this.gtgReplacementMajorAssemblies = gtgRepRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            eqptSrNumber: String(row["eqpt_sr_number"] || row["serial_no"] || ""),
            dateOfReplacement: String(row["date"] || ""),
            subAssemblyUnitName: String(row["unit_sub_units"] || ""),
            reasonOfReplacement: String(row["reason_for_replacement"] || ""),
            lifeSinceInstallation: "",
            remarks: String(row["replacement_remarks"] || "")
          }));
        }
        const gtgRoutineRows = data?.["tab_11_gtg_srmr"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(gtgRoutineRows)) {
          this.gtgRoutinesUndertaken = gtgRoutineRows.map(row => ({
            eqptName: String(row["eqpt_name"] || ""),
            eqptSrNumber: String(row["eqpt_sr_number"] || row["serial_no"] || ""),
            date: String(row["date"] || ""),
            descriptionForRoutine: String(row["description_of_routine"] || ""),
            undertakenByWhom: String(row["undertaken_by_whom"] || "")
          }));
        }
        const rhRows = data?.["tab_13_rh_extensions"] as Record<string, unknown>[] | undefined;
        if (Array.isArray(rhRows) && rhRows.length > 0) {
          const mapRh = (row: Record<string, unknown>): RhExtensionItem => ({
            eqptName: String(row["eqpt_name"] || ""),
            location: String(row["loc_on_board"] || ""),
            nomenclature: String(row["nomenclature"] || ""),
            serNo: String(row["serial_no"] || ""),
            onRoutine: String(row["on_routine_text"] || ""),
            rhDuringTrial: String(row["rh_ext_at_conduct_of_ext_trial"] || ""),
            trialConductedBy: String(row["trial_conducted_by"] || ""),
            authorityLetter: null,
            authorityLetterRef: String(row["authority_letter_for_extension_trial"] || ""),
            rhdi: String(row["total_rh_in_month"] || ""),
            rhExtensionGranted: String(row["rh_extension_granted_upto"] || ""),
            rhLeftExpiry: String(row["rh_left_for_expiry_of_extension"] || "")
          });
          this.mainEngineRHExtensions = rhRows.filter(row => Number(row["equipment_type"] || 1) === 1).map(mapRh);
          this.dieselAlternatorRHExtensions = rhRows.filter(row => Number(row["equipment_type"] || 1) === 2).map(mapRh);
        }
        this.recalculateDgufSeaHarbourSplit();
        this.syncDgufGeneratorsToFip();
      },
      error: (err) => console.error("Failed to load report details:", err)
    });
  }

  getMonthNumber(month: string | number | undefined): number {
    if (typeof month === "number") return month;
    const parsed = parseInt(String(month), 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= 12) return parsed;
    const monthNames = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];
    const shortNames = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    const mStr = String(month || "").toLowerCase().trim();
    let idx = monthNames.indexOf(mStr);
    if (idx === -1) idx = shortNames.indexOf(mStr.slice(0, 3));
    return idx !== -1 ? idx + 1 : (new Date().getMonth() + 1);
  }

  saveReportPayload(isFinalSubmission = false, callback?: (success: boolean) => void) {
    this.syncSafetyAndFipEquipments();
    const payload = {
      header: {
        id: this.srarId,
        ship: null,
        srar_month: this.getMonthNumber(this.selectedMonth()),
        srar_year: parseInt(String(this.selectedYear()), 10) || 2026,
        hours_underway_month_hr: parseInt(String(this.runningParameters.duringMonthHours || 0), 10) || 0,
        hours_underway_month_min: parseInt(String(this.runningParameters.duringMonthMinutes || 0), 10) || 0,
        distance_run_month: parseFloat(String(this.runningParameters.duringMonthDistance || 0)) || 0,
        max_speed: parseFloat(String(this.runningParameters.maxSpeedDuringMonth || 0)) || 0,
        max_shaft_rpm: parseFloat(String(this.runningParameters.maxShaftRpm || 0)) || 0,
        max_speed_date: this.formatDateToYYYYMMDD(this.runningParameters.maxSpeedDate),
        max_speed_duration_hr: parseInt(String(this.runningParameters.maxSpeedDurationHours || 0), 10) || 0,
        max_speed_duration_min: parseInt(String(this.runningParameters.maxSpeedDurationMinutes || 0), 10) || 0,
        is_saved: isFinalSubmission,
        send_to_co: isFinalSubmission ? (this.eoDetails.sendToCo || false) : false,
        eo_name: this.eoDetails.name,
        eo_rank: this.eoDetails.rank,
        eo_personal_no: this.eoDetails.personalNo,
        eo_contact_no: this.eoDetails.contactNo,
        eo_writer_contact_no: this.eoDetails.writerContactNo,
      },
      tab_1_equipment_exploitations: this.equipments.map(e => {
        const item: Record<string, unknown> = {
          nomenclature: e.name || "",
          rhsi_till_current_month: typeof e.prevHours === "number"
            ? Math.floor(e.prevHours)
            : (parseInt(String(e.prevHours || "0").split(":")[0], 10) || 0),
          hrs_for_month_hrs: typeof e.duringMonthHours === "number" ? e.duringMonthHours : 0,
          hrs_for_month_min: typeof e.duringMonthMinutes === "number" ? e.duringMonthMinutes : 0
        };
        if (this.srarId && typeof e.id === "number" && e.id > 1000) {
          item["id"] = e.id;
        }
        return item;
      }),
      tab_2_boiler_data: this.boilerSteamingData.map(b => ({
        ...(this.srarId && b.id ? { id: b.id } : {}),
        name: b.eqptName,
        nomenclature: b.nomenclature,
        loc_on_board: b.locOnBoard,
        serial_no: b.serNo,
        hrs_steamed_in_month: b.hrsSteamedDuringMonth,
        hrs_steamed_since_commissioning: b.hrsSteamedSinceComm,
        hrs_above_20_percent: b.hrsAbove80
      })),
      tab_3_ship_activities: this.activities.map(a => {
        const parts = a.dateRange ? String(a.dateRange).split(" to ") : ["", ""];
        return {
          from_date: parts[0] ? this.formatDateToYYYYMMDD(parts[0]) : null,
          to_date: parts[1] ? this.formatDateToYYYYMMDD(parts[1]) : null,
          ship_state: a.shipState,
          ship_location: a.shipLocation,
          ship_activity_type: a.activityType,
          ship_activity_detail: a.activityDetail,
          remarks: a.remarks
        };
      }),
      tab_4_fuel_consumptions: [{
        b_f_from_last_month: parseFloat(String(this.fuelConsumption.bfLastMonth || 0)) || 0,
        recieved: parseFloat(String(this.fuelConsumption.received || 0)) || 0,
        consumed_in_harbour: parseFloat(String(this.fuelConsumption.consHarbor || 0)) || 0,
        consumed_at_anchorage: parseFloat(String(this.fuelConsumption.consAnchorage || 0)) || 0,
        consumed_at_sea: parseFloat(String(this.fuelConsumption.consSea || 0)) || 0,
        total_consumed: parseFloat(String(this.fuelConsumption.totalCons || 0)) || 0,
        defueled: parseFloat(String(this.fuelConsumption.defueled || 0)) || 0,
        balance_left_on_board: parseFloat(String(this.fuelConsumption.balLeftOnboard || 0)) || 0
      }],
      tab_4_avcat_status: {
        b_f_from_last_month: parseFloat(String(this.avcatStatus.bfLastMonth || 0)) || 0,
        recieved: parseFloat(String(this.avcatStatus.received || 0)) || 0,
        given_to_ac: parseFloat(String(this.avcatStatus.givenToAc || 0)) || 0,
        used_for_trials_drained: parseFloat(String(this.avcatStatus.usedForTrials || 0)) || 0,
        total_consumed: parseFloat(String(this.avcatStatus.totalCons || 0)) || 0,
        defuelded: parseFloat(String(this.avcatStatus.defueled || 0)) || 0,
        balance_left_on_board: parseFloat(String(this.avcatStatus.balLeftOnboard || 0)) || 0
      },
      tab_5_iccp: this.iccpData.map(ic => ({
        nomenclature: ic.nomenclature,
        eqpt_code: ic.eqptCode,
        loc_on_board: ic.locOnBoard,
        ops_non_ops: ic.opsNonOps,
        non_ops_since: this.formatDateToYYYYMMDD(ic.nonOpsSince)
      })),
      tab_5_stp: this.stpData.map(stp => ({
        nomenclature: stp.nomenclature,
        loc_on_board: stp.locOnBoard,
        effluent_status: stp.status,
        effluent_test_date: this.formatDateToYYYYMMDD(stp.effluentTestDate),
        remarks: stp.remarks
      })),
      tab_5_magazine: this.mffsData.map(mffs => ({
        nomenclature: mffs.nomenclature,
        loc_on_board: mffs.locOnBoard,
        status: mffs.status,
        last_trials_taken: this.formatDateToYYYYMMDD(mffs.lastTrialsTaken),
        next_trials_due: this.formatDateToYYYYMMDD(mffs.nextTrialsDue)
      })),
      tab_6_test_kits: this.lubOilCoolantTestKits.map(tk => ({
        description: tk.description,
        ops_non_ops: tk.opsNonOps,
        calibration_date: this.formatDateToYYYYMMDD(tk.calibrationDate),
        next_calibration_due_date: this.formatDateToYYYYMMDD(tk.nextCalibrationDueDate)
      })),
      tab_7_safety_device_checks: this.safetyDeviceChecks.map(sdc => ({
        eqpt_name: sdc.eqptName,
        loc_on_board: sdc.locOnBoard,
        sdc_conducted_by: sdc.sdcConductedBy,
        date_of_sdc: this.formatDateToYYYYMMDD(sdc.dateOfSdc),
        sfc_gms_k_wh: sdc.sfcGmsKWh,
        last_sfc_trial_date: this.formatDateToYYYYMMDD(sdc.lastSfcTrialDate),
        displacement_during_sfc: sdc.displacementDuringSfc,
        status: sdc.status
      })),
      tab_7_calibrations: this.injectorFipCalibration.map(fip => ({
        eqpt_name: fip.eqptName,
        nomenclature: fip.nomenclature,
        eqpt_code: fip.eqptCode,
        loc_on_board: fip.locOnBoard,
        running_hours_months: fip.fipInMonth,
        running_hours_since_installation: fip.rhSinceInstallation,
        hrs_run_below_33_percent: fip.hrsBelow30,
        hrs_run_33_to_50_percent: fip.hrs30to50,
        hrs_run_50_to_70_percent: fip.hrs50to70,
        hrs_run_70_to_100_percent: fip.hrs70to100,
        lub_oil_consumption_in_month: fip.lubOilConsCurrentMonth,
        date_of_inj_fip_calibration: this.formatDateToYYYYMMDD(fip.dateOfInjectorCalibration),
        occasion: fip.occasionsReplacement,
        rh_at_which_replaced: fip.inOutWhichReplaced,
        fuel_consumption_in_month: fip.fuelConsumptionTons,
        remarks: fip.remarks
      })),
      tab_8_dguf: this.dgufGeneratorData.map(dg => ({
        serial_no: dg.eqptCode || dg.daNo,
        da_number: dg.daNo,
        rh_at_sea_and_anchorage: dg.rhSeaAnchorage,
        rh_at_port: dg.rhHarbour,
        total_rh_in_month: dg.totalRhMonth
      })),
      tab_8_dguf_running_hours: {
        total_rh_at_sea: this.dgufRunningHoursData.totalRhSea,
        hours_underway: this.dgufRunningHoursData.hrsUnderway,
        anchorage: this.dgufRunningHoursData.anchorage,
        drifting: this.dgufRunningHoursData.drifting,
        no_of_hours_in_harbour: this.dgufRunningHoursData.hrsInHarbour,
        hours_shore_supply_avl_when_alongs: this.dgufRunningHoursData.hrsShoreSupply,
        no_of_cold_moves_in_harbour: Number(this.dgufRunningHoursData.coldMoves || 0),
        cmts_wrt_to_non_avl_shore_supply: this.dgufRunningHoursData.comments,
        serial_no: "DGUF-RH"
      },
      tab_8_dguf_limits: [{
        limiting_value_sea: Number(this.dgufLimitingValues.limitingValueSea || 0),
        limiting_value_harbour: Number(this.dgufLimitingValues.limitingValueHarbour || 0),
        actual_dguf_sea: Number(this.dgufLimitingValues.actualDgufSea || 0),
        actual_dguf_harbour: Number(this.dgufLimitingValues.actualDgufHarbour || 0),
        exceed_reason_sea: this.dgufLimitingValues.reasonExceedingSea,
        exceed_reason_harbour: this.dgufLimitingValues.reasonExceedingHarbour
      }],
      tab_9_fpt_me: [{
        date: this.formatDateToYYYYMMDD(this.fptMainEngineGeneral.lastFptDate),
        displacement: Number(this.fptMainEngineGeneral.displacement || 0),
        max_speed: Number(this.fptMainEngineGeneral.maxSpeed || 0),
        occasion_reason: this.fptMainEngineGeneral.occasionReason,
        draught_fwd: Number(this.fptMainEngineGeneral.draughtFwd || 0),
        draught_aft: Number(this.fptMainEngineGeneral.draughtAft || 0),
        conducted_by: this.fptMainEngineGeneral.conductedBy,
        torsion_meter_reading: this.fptMainEngineGeneral.torsionMotorReading,
        sea_state: this.fptMainEngineGeneral.seaState,
        pending_dr_activities_reason: this.fptMainEngineGeneral.remarks
      }],
      tab_9_fpt_eq: this.fptMainEngineSpecific.map(me => ({
        eqpt_name: me.eqptName,
        nomenclature: me.nomenclature,
        eqpt_code: me.eqptCode,
        loc_on_board: me.locOnBoard,
        serial_no: me.serNo,
        fuel_rack_dbr_max: Number(me.fuelRackDbl || 0),
        marking_max: Number(me.fciThrottleMarking || 0),
        undertaken_on: this.formatDateToYYYYMMDD(me.lastEhmTrialsDate),
        pitch: me.pitch,
        max_rpm: Number(me.maxRpm || 0),
        rated_power: Number(me.ratedPower || 0),
        max_achieved_power: Number(me.maxAchievedPower || 0),
        remarks: me.remarks
      })),
      tab_9_fpt_da: this.fptDieselGeneratorLoad.map(da => ({
        eqpt_name: da.eqptName,
        nomenclature: da.nomenclature,
        eqpt_code: da.eqptCode,
        loc_on_board: da.location,
        serial_no: da.eqptSerNo,
        date: this.formatDateToYYYYMMDD(da.date),
        occasion: da.occasionReason,
        rated_load: Number(da.ratedLoad || 0),
        max_load_achieved: Number(da.maxLoadAchieved || 0),
        conducted_by: da.conductedBy,
        last_ehm_trials_undertaken_on: this.formatDateToYYYYMMDD(da.lastEhmTrialsDate),
        remarks: da.remarks
      })),
      tab_10_reduction_gear: this.gtReductionGear.map(rg => ({
        eqpt_name: rg.eqptName,
        nomenclature: rg.nomenclature,
        eqpt_code: rg.eqptCode,
        loc_on_board: rg.locOnBoard,
        serial_no: rg.eqptSerNo,
        total_rh_in_month: rg.totalRhInMonth,
        total_rh_si: rg.totalRhsi,
        total_rh_regime1_in_month: rg.hoRegimeBelow0_25,
        total_rh_regime1_si: rg.hoRegimeBelow0_25Si,
        total_rh_regime2_in_month: rg.hoRegime0_25to0_5,
        total_rh_regime2_si: rg.hoRegime0_25to0_5Si,
        total_rh_regime3_in_month: rg.hoRegime0_5to0_75,
        total_rh_regime3_si: rg.hoRegime0_5to0_75Si,
        trailing_rh_in_month: rg.slidingHours0_25,
        trailing_rh_si: rg.slidingHours0_25Si,
        service_life_in_month: rg.serviceLife,
        service_life_si: rg.serviceLifeSi,
        no_of_eng_regime1_in_month: rg.routineRegime1,
        no_of_eng_regime1_si: rg.routineRegime1Si,
        no_of_eng_regime2_in_month: rg.routineRegime2,
        no_of_eng_regime2_si: rg.routineRegime2Si,
        no_of_eng_regime3_in_month: rg.routineRegime3,
        no_of_eng_regime3_si: rg.routineRegime3Si,
        no_of_eng_regime4_in_month: rg.routineRegime4,
        no_of_eng_regime4_si: rg.routineRegime4Si
      })),
      tab_10_gas_turbine: this.gasTurbineExploitation.map(gt => ({
        eqpt_name: gt.eqptName,
        nomenclature: gt.nomenclature,
        eqpt_code: gt.eqptCode,
        loc_on_board: gt.locOnBoard,
        serial_no: gt.serNo,
        total_rh_in_month: Number(gt.totalRhInMonth || 0),
        total_rh_si: Number(gt.totalRhSi || 0),
        rh_regime_1_in_mth: gt.rhRegime1InMonth,
        rh_regime_1_si: Number(gt.rhRegime1Si || 0),
        rh_regime_2_in_mth: gt.rhRegime2InMonth,
        rh_regime_2_si: Number(gt.rhRegime2Si || 0),
        rh_regime_3_in_mth: gt.rhRegime3InMonth,
        rh_regime_3_si: Number(gt.rhRegime3Si || 0),
        no_of_cold_starts_in_month: Number(gt.noOfOccasion || 0),
        no_of_cold_starts_si: Number(gt.noOfRepOrders || 0),
        no_of_hot_starts_in_month: Number(gt.unscheduledEngagement || 0),
        no_of_hot_starts_si: Number(gt.fuelExploitation || 0),
        no_of_false_starts_in_month: Number(gt.gslChemQty || 0),
        no_of_false_starts_si: Number(gt.status || 0),
        no_of_tech_starts_in_month: Number(gt.rhEngine1 || 0),
        no_of_tech_starts_si: Number(gt.rhEngine2 || 0),
        no_of_astern_engagements_in_mth: gt.lastCalibrationDate,
        no_of_astern_engagements_count: Number(gt.lastEhmTrialDate || 0),
        no_of_stop_orders_in_mth: gt.lastFptDate,
        no_of_stop_orders_si: 0
      })),
      tab_10_replacements: this.gtReplacementMajorAssemblies.map(rep => ({
        eqpt_name: rep.eqptName,
        eqpt_sr_number: rep.eqptSrNumber,
        serial_no: rep.eqptSrNumber,
        date_of_replacement: this.formatDateToYYYYMMDD(rep.dateOfReplacement),
        unit_sub_units: rep.subAssemblyUnitName,
        reason_for_replacement: rep.reasonOfReplacement,
        replacement_remarks: rep.remarks,
        tab_value: "GT/RG"
      })),
      tab_10_srmr: this.gtRoutinesUndertaken.map(rt => ({
        eqpt_name: rt.eqptName,
        eqpt_sr_number: rt.eqptSrNumber,
        serial_no: rt.eqptSrNumber,
        date: this.formatDateToYYYYMMDD(rt.date),
        description_of_routine: rt.descriptionForRoutine,
        undertaken_by_whom: rt.undertakenByWhom,
        tab_value: "GT/RG"
      })),
      tab_11_gtg: this.gtgExploitationData.map(gtg => ({
        eqpt_name: gtg.eqptName,
        nomenclature: gtg.nomenclature,
        eqpt_code: gtg.eqptCode,
        loc_on_board: gtg.locOnBoard,
        serial_no: gtg.serNo,
        total_rh_in_harbour: gtg.rhInHarbour,
        total_rh_in_sea: gtg.rhInSea,
        total_rh_in_month: gtg.totalRhInMonth,
        total_rh_si: gtg.totalRhsi,
        no_of_cold_starts_in_month: Number(gtg.noOfColdStarts || 0),
        no_of_cold_starts_si: Number(gtg.noOfColdStartsSi || 0),
        no_of_hot_starts_in_month: Number(gtg.noOfHotStarts || 0),
        no_of_hot_starts_si: Number(gtg.noOfHotStartsSi || 0),
        no_of_battery_cold_starts_in_month: Number(gtg.noOfBatteryColdStarts || 0),
        no_of_battery_cold_starts_si: Number(gtg.noOfBatteryColdStartsSi || 0),
        no_of_battery_hot_starts_in_month: Number(gtg.noOfBatteryHotStarts || 0),
        no_of_battery_hot_starts_si: Number(gtg.noOfBatteryHotStartsSi || 0),
        date: this.formatDateToYYYYMMDD(gtg.lastChemClgDateReason)
      })),
      tab_11_gtg_rg: this.gtgReductionGear.map(rg => ({
        eqpt_name: rg.eqptName,
        nomenclature: rg.nomenclature,
        eqpt_code: rg.eqptCode,
        loc_on_board: rg.locOnBoard,
        serial_no: rg.serNo,
        rg_running_hours: Number(rg.rgRunningHours || 0),
        no_of_hot_starts: Number(rg.noOfHotStarts || 0),
        no_of_cold_starts: Number(rg.noOfColdStarts || 0),
        rh_in_harbour: Number(rg.rhInHarbour || 0),
        rh_in_sea: Number(rg.rhInSea || 0),
        in_months_si: Number(rg.inMonthsSi || 0)
      })),
      tab_11_gtg_rep: this.gtgReplacementMajorAssemblies.map(rep => ({
        eqpt_name: rep.eqptName,
        eqpt_sr_number: rep.eqptSrNumber,
        serial_no: rep.eqptSrNumber,
        date: this.formatDateToYYYYMMDD(rep.dateOfReplacement),
        unit_sub_units: rep.subAssemblyUnitName,
        reason_for_replacement: rep.reasonOfReplacement,
        replacement_remarks: rep.remarks
      })),
      tab_11_gtg_srmr: this.gtgRoutinesUndertaken.map(rt => ({
        eqpt_name: rt.eqptName,
        eqpt_sr_number: rt.eqptSrNumber,
        serial_no: rt.eqptSrNumber,
        date: this.formatDateToYYYYMMDD(rt.date),
        description_of_routine: rt.descriptionForRoutine,
        undertaken_by_whom: rt.undertakenByWhom
      })),
      tab_12_lubricants: this.lubricantData,
      tab_13_rh_extensions: [
        ...this.mainEngineRHExtensions.map((rh: RhExtensionItem) => ({
          eqpt_name: rh.eqptName,
          nomenclature: rh.nomenclature,
          loc_on_board: rh.location,
          serial_no: rh.serNo,
          total_rh_in_month: rh.rhdi,
          on_routine: null,
          on_routine_text: rh.onRoutine,
          rh_ext_at_conduct_of_ext_trial: rh.rhDuringTrial,
          authority_letter_for_extension_trial: rh.authorityLetterRef,
          rh_extension_granted_upto: rh.rhExtensionGranted,
          rh_left_for_expiry_of_extension: rh.rhLeftExpiry,
          equipment_type: 1,
          trial_conducted_by: rh.trialConductedBy
        })),
        ...this.dieselAlternatorRHExtensions.map((rh: RhExtensionItem) => ({
          eqpt_name: rh.eqptName,
          nomenclature: rh.nomenclature,
          loc_on_board: rh.location,
          serial_no: rh.serNo,
          total_rh_in_month: rh.rhdi,
          on_routine: null,
          on_routine_text: rh.onRoutine,
          rh_ext_at_conduct_of_ext_trial: rh.rhDuringTrial,
          authority_letter_for_extension_trial: rh.authorityLetterRef,
          rh_extension_granted_upto: rh.rhExtensionGranted,
          rh_left_for_expiry_of_extension: rh.rhLeftExpiry,
          equipment_type: 2,
          trial_conducted_by: rh.trialConductedBy
        }))
      ],
      tab_14_eef: {
        designed: this.eefData.designed,
        actual: this.calculatedEEF || null,
        reason_for_exceeding: this.eefData.reasonExceeding,
        ship_remarks: this.eefData.shipRemarks
      }
    };

    this.srarService.saveCompositeSrar(payload).subscribe({
      next: (res: SrarApiResponse) => {
        if (res && res["id"]) {
          this.srarId = res["id"] as number;
        }
        this.loadDashboard();
        if (callback) callback(true);
      },
      error: (err: unknown) => {
        console.error("Failed to save report:", err);
        this.appService.openAlert("Error", "Failed to save SRAR Report. Please verify entries and try again.");
        if (callback) callback(false);
      }
    });
  }

  submitSRAR() {
    this.saveReportPayload(true, (success?: boolean) => {
      if (success) {
        this.appService.openAlert("Success", "SRAR Report Finalized and Submitted successfully", () => {
          this.showDetails.set(false);
          this.activeSubTab.set(1);
        });
      }
    });
  }

  getStatusClass(status: string): string {
    switch (status) {
      case "Approved":
        return "badge-success";
      case "In Review":
        return "badge-warning";
      case "Draft":
        return "badge-secondary";
      case "Pending":
      default:
        return "badge-info";
    }
  }
}
