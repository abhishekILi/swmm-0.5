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

import { IconComponent } from "../../../../shared/components/icon/icon.component";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { ColDef } from "ag-grid-community";
import { CommonApiService } from "../../../../Core/services/common/commonApiService";
import {
  DepartmentOption,
  TagoutHistoryDataItem,
} from "../tag-in-tag-out.model";

import { DetailDrawer } from "../../../../shared/components/detail-drawer/detail-drawer";

export interface TagHistoryRecord {
  sNo: number;
  tagNo: string;
  equipment: string;
  department?: string;
  dateTagged: string;
  status: string;
}

@Component({
  selector: "app-tag-history",
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, DataGrid, DetailDrawer],
  templateUrl: "./tag-history.component.html",
  styleUrl: "./tag-history.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TagHistoryComponent implements OnInit {
  private readonly commonApiService = inject(CommonApiService);

  readonly selectedRecord = signal<TagHistoryRecord | null>(null);

  onRowClicked(row: unknown): void {
    if (row && typeof row === "object") {
      this.selectedRecord.set(row as TagHistoryRecord);
    }
  }

  closeDrawer(): void {
    this.selectedRecord.set(null);
  }

  readonly fromDate = signal<string>("");
  readonly toDate = signal<string>("");
  readonly selectedDepartment = signal<string>("ALL");
  readonly departmentsList = signal<DepartmentOption[]>([]);
  readonly historyRecords = signal<TagHistoryRecord[]>([]);
  readonly isLoading = signal<boolean>(false);

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.isLoading.set(true);
    const filters = {
      from_date: this.fromDate(),
      to_date: this.toDate(),
      department:
        this.selectedDepartment() === "ALL" ? "" : this.selectedDepartment(),
    };

    this.commonApiService.getTagoutHistoryList(filters).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        let items: TagoutHistoryDataItem[] = [];

        if (
          res &&
          typeof res === "object" &&
          "data" in res &&
          Array.isArray(res.data)
        ) {
          items = res.data;
          if (res.departments && Array.isArray(res.departments)) {
            this.departmentsList.set(res.departments);
          }
        } else if (Array.isArray(res)) {
          items = res as TagoutHistoryDataItem[];
        }

        const mapped: TagHistoryRecord[] = items.map(
          (item: TagoutHistoryDataItem, index: number) => {
            let equipName =
              item.ship_name ||
              item.name_of_component ||
              item.name_of_subsystem ||
              item.equipment;
            if (!equipName) {
              equipName = "-";
            }

            let deptSummary = item.department_name || "";
            if (
              item.departments_affected &&
              item.departments_affected.length > 0
            ) {
              deptSummary = item.departments_affected
                .map((d) =>
                  typeof d === "object" && d !== null && "name" in d
                    ? d.name
                    : String(d),
                )
                .join(", ");
            }

            const tagNoStr =
              item.tagout_number || item.tag_no || `TAG-2026-00${item.id}`;

            let statusStr: string;
            if (item.active === 1) {
              statusStr = "Active";
            } else if (item.active === 0) {
              statusStr = "Inactive";
            } else {
              statusStr = item.approval_status || item.status || "Active";
            }

            return {
              sNo: index + 1,
              tagNo: tagNoStr,
              equipment: equipName,
              department: deptSummary,
              dateTagged: item.date || "-",
              status: statusStr,
            };
          },
        );

        this.historyRecords.set(mapped);
      },
      error: (err) => {
        this.isLoading.set(false);
        console.warn("API GET /api/v1/inout-tags/history/ error:", err);
        this.historyRecords.set([]);
      },
    });
  }

  onSearch(): void {
    this.loadHistory();
  }

  readonly historyColumnDefs: ColDef[] = [
    { headerName: "S.NO", field: "sNo", width: 90 },
    { headerName: "TAG NO", field: "tagNo", flex: 1.5 },
    { headerName: "EQUIPMENT / SHIP", field: "equipment", flex: 2 },
    { headerName: "DEPARTMENT(S)", field: "department", flex: 2 },
    { headerName: "DATE TAGGED", field: "dateTagged", flex: 1.5 },
    { headerName: "STATUS", field: "status", flex: 1.2 },
  ];

  readonly filteredRecords = computed(() => {
    return this.historyRecords();
  });
}
