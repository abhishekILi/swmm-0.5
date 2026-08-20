import { CommonModule } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { Router } from "@angular/router";
import { firstValueFrom } from "rxjs";

import { MasterCard } from "../../refit-maintenance/master-card/master-card";
import { DataGrid } from "../../../shared/components/data-grid/data-grid";
import { Call } from "../../../services/network/call";
import { IconComponent } from "../../../shared/components/icon/icon.component";



import { FormBuilder, FormGroup, ReactiveFormsModule } from "@angular/forms";
import {
  DropdownOption,
  SelectInput,
} from "../../../shared/components/select-input/select-input";
import { InputField } from "../../../shared/components/input-field/input-field";
import {
  DartDetailsApiResponse,
  DefectDetail,
  FilterOption,
  OpenDefect,
  Spare,
} from "./open-defects.model";
import { ActionRenderer } from "../action-renderer/action-renderer";
import { NotificationService } from "../../../Core/services/notification/notification.service";
import { debounceTime, distinctUntilChanged } from "rxjs/operators";

@Component({
  selector: "app-open-defects",
  standalone: true,
  imports: [CommonModule, MasterCard, DataGrid, ReactiveFormsModule, SelectInput, InputField, IconComponent],
  templateUrl: "./open-defects.html",
  styleUrl: "./open-defects.css",
})
export class OpenDefects implements OnInit {
  private router = inject(Router);

  activeTab = "defects";
  form!: FormGroup;
  popupForm!: FormGroup;

  private api = inject(Call);
  private fb = inject(FormBuilder);
  private toastr = inject(NotificationService);

  defectsSearchText = "";
  dl3SearchText = "";
  showPopup = false;
  selectedDefect: DefectDetail | null = null;
  selectedDefects: OpenDefect[] = [];

  openDefectsData = signal<OpenDefect[]>([]);
  dl3DefectsData = signal<OpenDefect[]>([]);
  maintenancePeriodOptions: DropdownOption[] = [];
  dartOccasionOptions: DropdownOption[] = [];
  subDepartmentOptions: DropdownOption[] = [];
  nomenclatureOptions: DropdownOption[] = [];
  sparesData: Spare[] = [];

  dateRangeOptions: DropdownOption[] = [
    { label: "All Data", value: "all" },
    { label: "Today", value: "today" },
    { label: "Yesterday", value: "yesterday" },
    { label: "Last 7 Days", value: "last_7_days" },
    { label: "Last 30 Days", value: "last_30_days" },
    { label: "This Month", value: "this_month" },
    { label: "Last Month", value: "last_month" },
    { label: "Custom", value: "custom" },
  ];
  sparesColumnDefs = [
    {
      headerName: "Pattern",
      field: "pattern",
      flex: 1,
    },
    {
      headerName: "Description",
      field: "description",
      flex: 2,
    },
    {
      headerName: "Inventory Type",
      field: "inventory_type",
      flex: 1,
    },
    {
      headerName: "Quantity",
      field: "quantity",
      flex: 1,
    },
  ];

  ngOnInit(): void {
    this.form = this.fb.group({
      subDepartment: [""],
      maintenancePeriod: [""],
      dartOccasion: [""],
      equipmentName: [""],
      nomenclature: [""],
      dateRange: ["all"],
      fromDate: [null],
      toDate: [null],
    });
    this.popupForm = this.fb.group({
      // Basic Details
      dart_number: [""],
      dart_date: [""],
      occasion: [""],
      maintenance_period: [""],

      // Equipment Details
      nomenclature: [""],
      equipment_code: [""],
      sub_dept: [""],
      department: [""],
      serial_no: [""],
      location: [""],
      previous_dart_no: [""],
      rha_defect: [""],
      created_date: [""],

      // Defect Details
      rectification_date: [""],
      symptoms: [""],
      severity: [""],
      assistance: [""],
      defective_component: [""],
      resolved_by: [""],
      trial_required: [""],
      trial_agency: [""],
      description: [""],

      // Spares
      sapres_required: [""],
    });

    // Every filter change re-fetches from the backend — the backend does the
    // filtering (and returns narrowed dropdown option lists to match), the
    // frontend never filters the already-fetched rows itself. This is a
    // continuous stream (not a one-shot call), so it stays subscribe-based.
    this.form.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
      )
      .subscribe(() => this.loadDashboard());

    this.loadDashboard();
  }

  private rawOpenDefects: OpenDefect[] = [];
  private rawDl3Defects: OpenDefect[] = [];

  async loadDashboard(): Promise<void> {
    const { subDepartment, maintenancePeriod, dartOccasion, nomenclature, dateRange, fromDate, toDate } =
      this.form.value;

    const params: Record<string, string> = {};
    if (subDepartment) params["sub_department"] = subDepartment;
    if (maintenancePeriod) params["maintenance_period"] = maintenancePeriod;
    if (dartOccasion) params["dart_occasion"] = dartOccasion;
    if (nomenclature) params["equipment_nomenclature"] = nomenclature;
    if (dateRange) params["date_range"] = dateRange;
    if (dateRange === "custom") {
      if (fromDate) params["defect_date_from"] = fromDate;
      if (toDate) params["defect_date_to"] = toDate;
    }

    try {
      const response = await firstValueFrom(this.api.getOpenDartsAndABER(params));
      this.rawOpenDefects = response.open_defects || [];
      this.rawDl3Defects = response.dl_3_defects || [];

      const filters = response.filter_options;

      const mapOptions = (items: FilterOption[] = []) =>
        items.map((item) =>
          typeof item === "string"
            ? { label: item, value: item }
            : { label: item.name, value: item.id },
        );

      this.subDepartmentOptions = mapOptions(filters?.sub_departments);
      this.maintenancePeriodOptions = mapOptions(filters?.maintenance_periods);
      this.dartOccasionOptions = mapOptions(filters?.dart_occasions);
      this.nomenclatureOptions = mapOptions(filters?.equipment_nomenclatures);

      this.applySearchOnly();
    } catch (err) {
      console.error(err);
    }
  }

  selectTab(id: string): void {
    this.activeTab = id;
    this.applySearchOnly();
  }

  onSelectionChanged(rows: unknown[]): void {
    this.selectedDefects = (rows as OpenDefect[]) ?? [];
  }

  // No selection required — createdlfun/ drafts whatever's newly selected (if
  // anything) AND always returns the full existing DRAFT DL-II list, so the
  // next page shows every already-drafted row regardless of what, if
  // anything, was checked here.
  async goToCreateDLII(): Promise<void> {
    const defectIds = this.selectedDefects.map((d) => d.id);

    try {
      const res = await firstValueFrom(this.api.createDL(defectIds));
      this.router.navigateByUrl("/afterAuth/op-maintenance/create-dlii", {
        state: {
          draftData: res.data?.draft_data ?? [],
          refitList: res.data?.refit_list ?? [],
          shipRemarksList: res.data?.ship_remarks_list ?? [],
        },
      });
    } catch (err) {
      const error = err as { error?: { message?: string } };
      console.error("Create DL-II failed", err);
      this.toastr.error(error?.error?.message ?? "Failed to initiate DL-II.");
    }
  }

  async goToCreateRA(): Promise<void> {
    const defectIds = this.selectedDefects.map((d) => d.id);
    if (!defectIds.length) {
      this.toastr.warning("Select at least one defect to raise an RA for.");
      return;
    }

    try {
      await firstValueFrom(this.api.createRA(defectIds));
      this.router.navigateByUrl("/afterAuth/op-maintenance/create-ra", {
        state: { selectedDefects: this.selectedDefects },
      });
    } catch (err) {
      const error = err as { error?: { message?: string } };
      console.error("Create RA failed", err);
      this.toastr.error(error?.error?.message ?? "Failed to initiate RA.");
    }
  }

  defectColumnDefs = [
    { headerName: "DART No.", field: "dart_number" },
    { headerName: "Defect Date", field: "dart_date" },
    { headerName: "Closing Date", field: "rectification_date" },
    { headerName: "Status", field: "status" },
    { headerName: "OPRA No.", field: "opra_no" },
    { headerName: "DL No.", field: "dl_no" },
    { headerName: "CMMS Sync Status", field: "cmms_sync_status" },
    { headerName: "Equipment Nomenclature", field: "nomenclature" },
    { headerName: "Defect Description", field: "defective_discriptions" },
    { headerName: "Remarks", field: "remarks" },
    {
      headerName: "Actions",
      field: "actions",
      cellRenderer: ActionRenderer,
      cellRendererParams: {
        onView: (data: OpenDefect) => this.openDefectPopup(data),
      },
      width: 180,
    },
  ];

  dl3ColumnDefs = [
    { headerName: "DART No.", field: "dart_number" },
    { headerName: "Defect Date", field: "dart_date" },
    { headerName: "Closing Date", field: "rectification_date" },
    { headerName: "Status", field: "status" },
    { headerName: "OPRA No.", field: "opra_no" },
    { headerName: "DL No.", field: "dl_no" },
    { headerName: "CMMS Sync Status", field: "cmms_sync_status" },
    { headerName: "Equipment Nomenclature", field: "nomenclature" },
    { headerName: "Defect Description", field: "defective_discriptions" },
    { headerName: "Remarks", field: "remarks" },
    { headerName: "Action", field: "Action" },
  ];

  async syncWithCMMS(): Promise<void> {
    const payload = this.openDefectsData();

    try {
      await firstValueFrom(this.api.postCmmsDart(payload));
      this.toastr.success('Synced with CMMS.');
    } catch (err) {
      console.error("CMMS Sync Failed", err);
      this.toastr.error('CMMS sync failed.');
    }
  }

  fetchingCmms = signal(false);

  async fetchAndSaveCmmsDefects(): Promise<void> {
    this.fetchingCmms.set(true);

    try {
      await firstValueFrom(this.api.postCmmsDart(this.openDefectsData()));
      this.fetchingCmms.set(false);
      this.toastr.success('CMMS defects fetched and saved.');
    } catch (err) {
      console.error("Fetch & Save CMMS Defects Failed", err);
      this.fetchingCmms.set(false);
      this.toastr.error('Failed to fetch defects from CMMS server.');
    }
  }
  exportPendingDefects(format: 'xlsx' | 'accdb'): void {
    window.open(new URL(`api/v1/dart/export/${format}/`, this.api.baseUrl).toString(), '_blank');
  }

  print(): void {
    window.print();
  }

  clearFilters(): void {
    if (this.activeTab === "defects") {
      this.defectsSearchText = "";
    } else {
      this.dl3SearchText = "";
    }

    this.form.reset({
      subDepartment: "",
      maintenancePeriod: "",
      dartOccasion: "",
      nomenclature: "",
      dateRange: "all",
      fromDate: null,
      toDate: null,
    });
  }

  onSearch(event: Event): void {
    const value = (event.target as HTMLInputElement).value.trim();

    if (this.activeTab === "defects") {
      this.defectsSearchText = value;
    } else {
      this.dl3SearchText = value;
    }

    this.applySearchOnly();
  }

  /** Applies only the free-text quick-search on top of the backend-filtered rows
   * already fetched via loadDashboard() — the dropdown/date filters themselves
   * are never applied client-side, the backend does that filtering. */
  private applySearchOnly(): void {
    const searchText =
      this.activeTab === "defects" ? this.defectsSearchText : this.dl3SearchText;

    const filterBySearch = (data: OpenDefect[]) =>
      searchText
        ? data.filter((item) =>
            Object.values(item).some((value) =>
              String(value ?? "").toLowerCase().includes(searchText.toLowerCase()),
            ),
          )
        : data;

    this.openDefectsData.set(filterBySearch(this.rawOpenDefects));
    this.dl3DefectsData.set(filterBySearch(this.rawDl3Defects));
  }

  async openDefectPopup(rowData: OpenDefect): Promise<void> {
    const dartId = rowData.id;

    try {
      const response = await firstValueFrom(this.api.getDartDetails(dartId));
      const data = (response as DartDetailsApiResponse).data;

      this.selectedDefect = data;

      this.popupForm.patchValue({
        // Basic Details
        dart_number: data.dart_number,
        dart_date: data.dart_date,
        occasion: data.occasion,
        maintenance_period: data.maintenance_period,

        // Equipment Details
        nomenclature: data.nomenclature,
        equipment_code: data.equipment_code,
        sub_dept: data.sub_dept,
        department: data.department,
        serial_no: data.serial_no,
        location: data.location,
        previous_dart_no: data.previous_dart_no,
        rha_defect: data.rha_defect,
        created_date: data.created_date,

        // Defect Details
        rectification_date: data.rectification_date,
        symptoms: data.symptoms,
        severity: data.severity,
        assistance: data.assistance,
        defective_component: data.defective_component,
        resolved_by: data.resolved_by,
        trial_required: data.trial_required,
        trial_agency: data.trial_agency,
        description: data.description,

        // Spares
        sapres_required: data.sapres_required,
      });
      this.sparesData = data.spares || [];
      this.showPopup = true;
    } catch (error) {
      console.error("Error fetching DART details:", error);
    }
  }
  closePopup(): void {
    this.showPopup = false;
  }
}
