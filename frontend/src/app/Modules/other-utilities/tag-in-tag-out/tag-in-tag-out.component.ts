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
import { Router } from "@angular/router";

// Shared components from src/app/shared/components
import { IconComponent } from "../../../shared/components/icon/icon.component";
import {
  LineChart,
  LineSeries,
} from "../../../shared/components/line-chart/line-chart";
import {
  DonutChart,
  DonutSegment,
} from "../../../shared/components/donut-chart/donut-chart";
import { ExportKind } from "../../../shared/components/export-toolbar/export-toolbar";
import { ColDef, ICellRendererParams } from "ag-grid-community";
import {
  CommonApiService,
  TagoutDashboardItem,
} from "../../../Core/services/common/commonApiService";

export interface TagRecord {
  id?: number;
  sNo: number;
  tagNo: string;
  equipmentName: string;
  isolationBoundary: string;
  taggedBy: string;
  dateTagged: string;
  status: "Tagged Out" | "Tagged In" | "Pending Approval";
  hodApprovalStatus?: string;
  remark?: string;
  rawItem?: Record<string, unknown>;
}

@Component({
  selector: "app-tag-in-tag-out",
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, LineChart, DonutChart],
  templateUrl: "./tag-in-tag-out.component.html",
  styleUrl: "./tag-in-tag-out.component.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TagInTagOutComponent implements OnInit {
  protected readonly Math = Math;
  private readonly router = inject(Router);
  private readonly commonApiService = inject(CommonApiService);

  // Counter Signals
  readonly tagOutCount = signal<number>(0);
  readonly tagInCount = signal<number>(0);
  readonly weeklyTagOutCount = signal<number>(0);
  readonly weeklyTagInCount = signal<number>(0);
  readonly todayTagOutCount = signal<number>(0);
  readonly todayTagInCount = signal<number>(0);
  readonly waitingForApprovalCount = signal<number>(0);
  readonly yetToTagInCount = signal<number>(0);

  // Active view determined by current URL path
  readonly activeSubView = computed<
    "dashboard" | "tag-out" | "tag-in" | "approval" | "history"
  >(() => {
    const path = this.router.url.split("?")[0].split("#")[0];
    const lastSegment = path.split("/").filter(Boolean).reverse().pop();
    if (
      lastSegment === "tag-out" ||
      lastSegment === "tag-out-approval" ||
      lastSegment === "create-tagout" ||
      lastSegment === "addtagout"
    )
      return "tag-out";
    if (
      lastSegment === "tag-in" ||
      lastSegment === "tag-in-approval" ||
      lastSegment === "create-tagin" ||
      lastSegment === "addtagin"
    )
      return "tag-in";
    if (lastSegment === "approval") return "approval";
    if (lastSegment === "history") return "history";
    return "dashboard";
  });

  // Dates for Tag In-Out History chart
  readonly historyDates = signal<string[]>([
    "2026-08-01",
    "2026-08-02",
    "2026-08-03",
    "2026-08-04",
    "2026-08-05",
    "2026-08-06",
    "2026-08-07",
  ]);

  // Dual series for Tag Out and Tag In matching screenshot (values = 0)
  readonly historySeries = signal<LineSeries[]>([
    {
      label: "Tag Out",
      color: "#f59e0b",
      values: [0, 0, 0, 0, 0, 0, 0],
    },
    {
      label: "Tag In",
      color: "#06b6d4",
      values: [0, 0, 0, 0, 0, 0, 0],
    },
  ]);

  // Daily Pie Chart segments matching screenshot
  readonly dailyPieSegments = signal<DonutSegment[]>([
    { label: "Tag Out", value: 0, color: "#f59e0b" },
    { label: "Tag In", value: 0, color: "#06b6d4" },
  ]);

  // Master Tag Records
  readonly tagRecords = signal<TagRecord[]>([]);

  ngOnInit(): void {
    this.commonApiService.getTagoutDashboardList().subscribe({
      next: (res) => {
        if (res && Array.isArray(res)) {
          const mapped: TagRecord[] = res.map(
            (item: TagoutDashboardItem, index: number) => {
              const statusStr = (item.approval_status || "").toLowerCase();
              let statusVal: "Tagged Out" | "Tagged In" | "Pending Approval" =
                "Tagged Out";
              if (statusStr === "in_progress" || statusStr === "pending") {
                statusVal = "Pending Approval";
              } else if (
                statusStr === "tagged_in" ||
                statusStr === "completed"
              ) {
                statusVal = "Tagged In";
              }

              let equipName = item.name_of_component || item.name_of_subsystem;
              if (!equipName) {
                if (typeof item.tagout_equipment_name === "string") {
                  equipName = item.tagout_equipment_name;
                } else if (item.tagout_equipment_name) {
                  equipName = `Equipment #${item.tagout_equipment_name}`;
                } else {
                  equipName = "-";
                }
              }

              return {
                sNo: index + 1,
                tagNo: item.tagout_number || `TAG-2026-00${item.id}`,
                equipmentName: equipName,
                isolationBoundary:
                  item.special_instructions || item.tagout_description || "-",
                taggedBy: item.tagout_maintainer_name_rank || "-",
                dateTagged: item.date || "-",
                status: statusVal,
              };
            },
          );

          this.tagRecords.set(mapped);

          const tagOuts = res.filter(
            (i) =>
              (i.type || "").toLowerCase() === "danger" ||
              (i.approval_status || "").toLowerCase() === "approved" ||
              (i.approval_status || "").toLowerCase() === "in_progress",
          ).length;
          const tagIns = res.filter(
            (i) =>
              (i.approval_status || "").toLowerCase() === "tagged_in" ||
              (i.approval_status || "").toLowerCase() === "completed",
          ).length;
          const pending = res.filter(
            (i) =>
              (i.approval_status || "").toLowerCase() === "in_progress" ||
              (i.approval_status || "").toLowerCase() === "pending",
          ).length;

          this.tagOutCount.set(tagOuts);
          this.tagInCount.set(tagIns);
          this.weeklyTagOutCount.set(tagOuts);
          this.weeklyTagInCount.set(tagIns);
          this.waitingForApprovalCount.set(pending);
          this.yetToTagInCount.set(tagOuts);

          // Update Donut Chart graph data dynamically from API
          this.dailyPieSegments.set([
            { label: "Tag Out", value: tagOuts, color: "#f59e0b" },
            { label: "Tag In", value: tagIns, color: "#06b6d4" },
          ]);

          // Calculate Line Chart history dates & graph series dynamically from API response
          const dateMap = new Map<string, { tagOut: number; tagIn: number }>();
          res.forEach((item: TagoutDashboardItem) => {
            const itemDate = item.date ? item.date.slice(0, 10) : "";
            if (itemDate) {
              if (!dateMap.has(itemDate)) {
                dateMap.set(itemDate, { tagOut: 0, tagIn: 0 });
              }
              const counts = dateMap.get(itemDate)!;
              const statusStr = (item.approval_status || "").toLowerCase();
              if (statusStr === "tagged_in" || statusStr === "completed") {
                counts.tagIn += 1;
              } else {
                counts.tagOut += 1;
              }
            }
          });

          const todayStr = new Date().toISOString().slice(0, 10);
          let datesList: string[] = Array.from(dateMap.keys()).sort((a, b) =>
            a.localeCompare(b),
          );

          if (datesList.length < 7) {
            const recentDates: string[] = [];
            const todayObj = new Date();
            for (let i = 6; i >= 0; i--) {
              const d = new Date(todayObj);
              d.setDate(d.getDate() - i);
              recentDates.push(d.toISOString().slice(0, 10));
            }
            datesList = recentDates;
          }

          const tagOutValues = datesList.map(
            (d) => dateMap.get(d)?.tagOut || 0,
          );
          const tagInValues = datesList.map((d) => dateMap.get(d)?.tagIn || 0);

          this.historyDates.set(datesList);
          this.historySeries.set([
            {
              label: "Tag Out",
              color: "#f59e0b",
              values: tagOutValues,
            },
            {
              label: "Tag In",
              color: "#06b6d4",
              values: tagInValues,
            },
          ]);

          // Today Summary counts from API
          const todayItems = res.filter(
            (i) => i.date?.slice(0, 10) === todayStr,
          );
          const todayTagOuts =
            todayItems.length > 0
              ? todayItems.filter(
                (i) =>
                  (i.approval_status || "").toLowerCase() !== "tagged_in" &&
                  (i.approval_status || "").toLowerCase() !== "completed",
              ).length
              : tagOuts;
          const todayTagIns =
            todayItems.length > 0
              ? todayItems.filter(
                (i) =>
                  (i.approval_status || "").toLowerCase() === "tagged_in" ||
                  (i.approval_status || "").toLowerCase() === "completed",
              ).length
              : tagIns;

          this.todayTagOutCount.set(todayTagOuts);
          this.todayTagInCount.set(todayTagIns);
        } else {
          this.tagRecords.set([]);
        }
      },
      error: (err) => {
        console.warn(
          "API GET /api/v1/inout-tags/tag-outs/dashboard/ fallback",
          err,
        );
        this.tagRecords.set([]);
      },
    });
  }

  // DataGrid Column Definitions for Tag Records Table
  readonly tagColumnDefs: ColDef[] = [
    { headerName: "Sr No", field: "sNo", width: 90, minWidth: 80 },
    { headerName: "Tag No", field: "tagNo", flex: 1.2, minWidth: 120 },
    {
      headerName: "Equipment Name",
      field: "equipmentName",
      flex: 2,
      minWidth: 180,
    },
    {
      headerName: "Isolation Boundary",
      field: "isolationBoundary",
      flex: 2.2,
      minWidth: 200,
    },
    { headerName: "Tagged By", field: "taggedBy", flex: 1.3, minWidth: 140 },
    {
      headerName: "Date Tagged",
      field: "dateTagged",
      flex: 1.2,
      minWidth: 120,
    },
    {
      headerName: "Status",
      field: "status",
      flex: 1.2,
      minWidth: 130,
      cellRenderer: (params: ICellRendererParams) => {
        const status =
          typeof params.value === "string" ? params.value : "Tagged Out";
        let style =
          "background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3);";
        if (status === "Tagged In") {
          style =
            "background: rgba(6,182,212,0.15); color: #06b6d4; border: 1px solid rgba(6,182,212,0.3);";
        } else if (status === "Pending Approval") {
          style =
            "background: rgba(168,85,247,0.15); color: #a855f7; border: 1px solid rgba(168,85,247,0.3);";
        }
        return `<span style="padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; ${style}">${status}</span>`;
      },
    },
  ];

  // Global search input
  readonly globalSearch = signal<string>("");

  readonly filteredRecords = computed(() => {
    const list = this.tagRecords();
    const search = this.globalSearch().toLowerCase().trim();
    if (!search) return list;

    return list.filter((r) => {
      return (
        r.sNo.toString().includes(search) ||
        r.tagNo.toLowerCase().includes(search) ||
        r.equipmentName.toLowerCase().includes(search) ||
        r.isolationBoundary.toLowerCase().includes(search) ||
        r.taggedBy.toLowerCase().includes(search) ||
        r.dateTagged.toLowerCase().includes(search) ||
        r.status.toLowerCase().includes(search)
      );
    });
  });

  onExport(kind: ExportKind): void {
    if (kind === "pdf") {
      window.print();
    } else if (kind === "excel") {
      this.downloadCSV();
    } else if (kind === "print") {
      window.print();
    }
  }

  downloadCSV(): void {
    const headers = [
      "Sr No",
      "Tag No",
      "Equipment Name",
      "Isolation Boundary",
      "Tagged By",
      "Date Tagged",
      "Status",
    ];
    const rows = this.filteredRecords().map((r) => [
      r.sNo,
      `"${r.tagNo}"`,
      `"${r.equipmentName}"`,
      `"${r.isolationBoundary}"`,
      `"${r.taggedBy}"`,
      `"${r.dateTagged}"`,
      `"${r.status}"`,
    ]);
    const csvContent = [
      headers.join(","),
      ...rows.map((e) => e.join(",")),
    ].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `TagInOut_${new Date().toISOString().slice(0, 10)}.csv`,
    );
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  copyData(): void {
    const headers = [
      "Sr No",
      "Tag No",
      "Equipment Name",
      "Isolation Boundary",
      "Tagged By",
      "Date Tagged",
      "Status",
    ];
    const rows = this.filteredRecords().map((r) =>
      [
        r.sNo,
        r.tagNo,
        r.equipmentName,
        r.isolationBoundary,
        r.taggedBy,
        r.dateTagged,
        r.status,
      ].join("\t"),
    );
    const text = [headers.join("\t"), ...rows].join("\n");
    navigator.clipboard.writeText(text);
  }
}
