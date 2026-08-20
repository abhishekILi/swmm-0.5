import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ColDef } from "ag-grid-community";
import { firstValueFrom } from "rxjs";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { HelpGuidance } from "../../shared/components/help-guidance/help-guidance";
import { MoApiService } from "../services/mo-api.service";
import { IifHistoryEntry, NormalDemandHistoryEntry, RioHistoryEntry } from "../models/mo.model";

type HistoryRow = NormalDemandHistoryEntry | RioHistoryEntry | IifHistoryEntry;

type HistoryTab = "normal" | "pts" | "rio" | "iif";

const NORMAL_COLUMNS: ColDef[] = [
  { field: "moItemCode", headerName: "MO Item Code", flex: 1 },
  { field: "itemDescription", headerName: "Item Description", flex: 1.2 },
  { field: "category", headerName: "Category", width: 110 },
  { field: "surveyNo", headerName: "Survey No", width: 110 },
  { field: "surveyDate", headerName: "Survey Date", width: 110 },
  { field: "demandNo", headerName: "Demand No", width: 110 },
  { field: "demandedQty", headerName: "Demanded Qty", width: 120 },
  { field: "demandDate", headerName: "Demand Date", width: 110 },
  { field: "moIssuedQty", headerName: "MO Issued Qty", width: 120 },
  { field: "dartNo", headerName: "DART No", width: 110 },
];

const RIO_COLUMNS: ColDef[] = [
  { field: "rioType", headerName: "RIO Type", width: 110 },
  { field: "moItemCode", headerName: "MO Item Code", flex: 1 },
  { field: "itemDescription", headerName: "Item Description", flex: 1.2 },
  { field: "rioDemandNo", headerName: "RIO Demand No", width: 130 },
  { field: "demandDate", headerName: "Demand Date", width: 110 },
  { field: "dartNo", headerName: "DART No", width: 110 },
  { field: "qtyDemanded", headerName: "Qty Demanded", width: 120 },
  { field: "moIssueQty", headerName: "MO Issue Qty", width: 120 },
  { field: "onboardReceiptDate", headerName: "Onboard Receipt Date", width: 160 },
  { field: "equipmentClass", headerName: "Equipment Class", flex: 1 },
];

const IIF_COLUMNS: ColDef[] = [
  { field: "iifRequisitionNo", headerName: "IIF Requisition No", flex: 1 },
  { field: "iifRequisitionDate", headerName: "IIF Requisition Date", width: 150 },
  { field: "ilmsSyncDate", headerName: "ILMS Sync Date", width: 130 },
  { field: "swmmItemCode", headerName: "SWMM Item Code", width: 140 },
  { field: "moItemCode", headerName: "MO Item Code", width: 130 },
  { field: "incattingCompletionDate", headerName: "INcatting Completion Date", width: 180 },
  { field: "equipmentClass", headerName: "Equipment Class", flex: 1 },
  { field: "equipmentNomenclature", headerName: "Equipment Nomenclature (SFD)", flex: 1.2 },
];

@Component({
  selector: "app-mo-history",
  standalone: true,
  imports: [DataGrid, HelpGuidance],
  templateUrl: "./mo-history.html",
  styleUrl: "./mo-history.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MoHistory implements OnInit {
  private readonly api = inject(MoApiService);

  readonly activeTab = signal<HistoryTab>("normal");
  readonly rows = signal<HistoryRow[]>([]);
  readonly columnDefs = signal<ColDef[]>(NORMAL_COLUMNS);

  ngOnInit(): void {
    void this.load();
  }

  selectTab(tab: HistoryTab): void {
    this.activeTab.set(tab);
    void this.load();
  }

  private async load(): Promise<void> {
    switch (this.activeTab()) {
      case "normal":
        this.columnDefs.set(NORMAL_COLUMNS);
        this.rows.set(await firstValueFrom(this.api.getNormalDemandHistory()));
        break;
      case "pts":
        this.columnDefs.set(NORMAL_COLUMNS);
        this.rows.set(await firstValueFrom(this.api.getPtsDemandHistory()));
        break;
      case "rio":
        this.columnDefs.set(RIO_COLUMNS);
        this.rows.set(await firstValueFrom(this.api.getRioDemandHistory()));
        break;
      case "iif":
        this.columnDefs.set(IIF_COLUMNS);
        this.rows.set(await firstValueFrom(this.api.getIifHistory()));
        break;
    }
  }
}
