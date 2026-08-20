import {
  Component,
  ChangeDetectionStrategy,
  signal,
  computed,
  inject,
  OnInit,
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { ColDef } from "ag-grid-community";

import { IconComponent } from "../../../../../shared/components/icon/icon.component";
import {
  ExportToolbar,
  ExportKind,
} from "../../../../../shared/components/export-toolbar/export-toolbar";
import { DataGrid } from "../../../../../shared/components/data-grid/data-grid";
import { DatePickerComponent, DatePickerValue } from "../../../../../shared/components/date-picker/picker";
import {
  CommonApiService,
  HotworkItem,
} from "../../../../../Core/services/common/commonApiService";

import { DetailDrawer } from "../../../../../shared/components/detail-drawer/detail-drawer";

export interface OutboxRecord {
  sNo: number;
  hotworkCode: string;
  parentCode: string;
  dateOfHotwork: string;
  departmentSection: string;
  descriptionOfHotwork: string;
  locationAdjacent: string;
  hotworkType: string;
  currentStatus: string;
  safeToWeldCert: string;
}

@Component({
  selector: "app-outbox",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IconComponent,
    ExportToolbar,
    DataGrid,
    DatePickerComponent,
    DetailDrawer,
  ],
  templateUrl: "./outbox.html",
  styleUrl: "./outbox.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OutboxComponent implements OnInit {
  private readonly commonApiService = inject(CommonApiService);

  readonly selectedRecord = signal<OutboxRecord | null>(null);

  onRowClicked(row: unknown): void {
    if (row && typeof row === "object") {
      this.selectedRecord.set(row as OutboxRecord);
    }
  }

  closeDrawer(): void {
    this.selectedRecord.set(null);
  }

  // Filter signals
  readonly selectedHotworkCode = signal<string>("ALL");
  readonly selectedDateRange = signal<DatePickerValue>(null);

  // Outbox data (Fetched dynamically from API)
  readonly rowData = signal<OutboxRecord[]>([]);

  readonly hotworkCodes = computed(() => {
    const codes = this.rowData()
      .map((r) => r.hotworkCode)
      .filter(Boolean);
    return Array.from(new Set(codes));
  });

  readonly filteredRowData = computed(() => {
    let list = this.rowData();
    const code = this.selectedHotworkCode();
    if (code && code !== "ALL") {
      list = list.filter((r) => r.hotworkCode === code);
    }
    return list;
  });

  ngOnInit(): void {
    this.commonApiService.getHotworkOutbox().subscribe({
      next: (res) => {
        if (res && Array.isArray(res)) {
          const mapped: OutboxRecord[] = res.map(
            (item: HotworkItem, index: number) => ({
              sNo: index + 1,
              hotworkCode: item.hotwork_code || `HW-2026-00${item.id}`,
              parentCode: item.created_by_name || "-",
              dateOfHotwork: item.date_of_hotwork || "-",
              departmentSection: item.hotwork_incharge_name || "-",
              descriptionOfHotwork: `${item.type_of_hotwork || "Hotwork"} Work`,
              locationAdjacent: item.location_of_hotwork || "-",
              hotworkType: item.type_of_hotwork || "-",
              currentStatus:
                item.current_status || item.approval_status || "Pending",
              safeToWeldCert: item.night_work ? "Issued" : "Pending",
            }),
          );
          this.rowData.set(mapped);
        } else {
          this.rowData.set([]);
        }
      },
      error: (err) => {
        console.warn("API GET /api/v1/hotwork/outbox/ fallback", err);
        this.rowData.set([]);
      },
    });
  }

  readonly colDefs: ColDef[] = [
    { headerName: "Sr No", field: "sNo", width: 90, minWidth: 80 },
    {
      headerName: "Hotwork Code",
      field: "hotworkCode",
      flex: 1.2,
      minWidth: 130,
    },
    { headerName: "Parent Code", field: "parentCode", flex: 1, minWidth: 110 },
    {
      headerName: "Date of Hotwork",
      field: "dateOfHotwork",
      flex: 1.2,
      minWidth: 130,
    },
    {
      headerName: "Department/Section",
      field: "departmentSection",
      flex: 1.3,
      minWidth: 140,
    },
    {
      headerName: "Description of Hotwork",
      field: "descriptionOfHotwork",
      flex: 2,
      minWidth: 180,
    },
    {
      headerName: "Location/Adjacent Compartments",
      field: "locationAdjacent",
      flex: 2,
      minWidth: 180,
    },
    {
      headerName: "Hotwork Type",
      field: "hotworkType",
      flex: 1.1,
      minWidth: 120,
    },
    {
      headerName: "Current Status",
      field: "currentStatus",
      flex: 1.2,
      minWidth: 130,
    },
    {
      headerName: "Safe To Weld Cert.",
      field: "safeToWeldCert",
      flex: 1.2,
      minWidth: 140,
    },
  ];

  handleExport(type: ExportKind) {
    console.log("Exporting as", type);
  }
}
