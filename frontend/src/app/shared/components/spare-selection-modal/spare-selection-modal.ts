import { Component, EventEmitter, Output, computed, input, signal, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { ColDef } from "ag-grid-community";
import { DataGrid } from "../data-grid/data-grid";
import { FormControl, ReactiveFormsModule } from "@angular/forms";
import { OperationMaintenance } from "../../../services/operation-maintenance";
import { SpareItem } from "../../../Pages/op-maintenance/action-forms/action-forms.model";

interface SpareApiItem {
  pk?: number | string;
  equipmentClass?: string;
  patternNo?: string;
  itemDesc?: string;
  availabilityStatus?: string;
  denomination?: string;
  heldQty?: number | string;
  crpCategory?: string;
  authority?: string;
  item_code?: string;
  item_desc?: string;
  status?: string;
  crp_category?: string;
  eqpt?: string;
  category?: string;
  typeofspare?: string;
  avail_status?: string;
  wed_eqpt_name?: string;
  sfd_equipment?: string;
  oemPartNo?: string;
  spareName?: string;
  [key: string]: unknown;
}

@Component({
  selector: "app-spare-selection-modal",
  standalone: true,
  imports: [CommonModule, DataGrid, ReactiveFormsModule],
  templateUrl: "./spare-selection-modal.html",
  styleUrls: ["./spare-selection-modal.css"],
})
export class SpareSelectionModal {
  private operationMaintenance = inject(OperationMaintenance);

  @Output() closeModal= new EventEmitter<void>();
  @Output() save = new EventEmitter<SpareItem[]>();
  title = "Select Spare Parts";
  selectedRows: SpareItem[] = [];
  searchControl = new FormControl("");
  selectedRowsByTab: Record<string, SpareItem[]> = {};
  selectedTab = signal("OBS");
  searchText = signal("");
  allRows = signal<SpareItem[]>([]);

  columnDefs = signal<ColDef[]>([]);

  source = input<'defect' | 'aber' | 'guarantee'>('defect');



  selectedSpares = input<SpareItem[]>([]);
  tabs = computed(() => {
    if (this.source() === "aber") {
      return [
        "OBS",
        "History"
      ]
    }
    return [
      "OBS",
      "Mapped-OBS",
      "MO Inventory",
      "Mapped-MO Inventory",
      "WED Inventory",
      "Mapped-WED Inventory",
      "PIL",
    ];
  })
  private tabTypeMap: Record<string, string> = {
    "MO Inventory": "mo",
    "Mapped-MO Inventory": "mo_mapped",
    "WED Inventory": "wed",
    "Mapped-WED Inventory": "wed_mapped",
    OBS: "obs",
    "Mapped-OBS": 'map-obs',
    'History': 'obs',
    "PIL": "pil"
  };

  constructor() {
    this.searchControl.valueChanges.subscribe((value) => {
      this.searchText.set(value ?? "");
    });

    // clear preivous component tabs
    const availableTabs = this.tabs();
    if (!availableTabs.includes(this.selectedTab())) {
      this.selectedTab.set(availableTabs[0]);
    }

    this.loadSpareParts(this.selectedTab());
  }

  filteredRows = computed(() => {
    const search = this.searchText().toLowerCase();

    if (!search) {
      return this.allRows();
    }

    return this.allRows().filter((row) =>
      Object.values(row).some((value) =>
        String(value ?? "")
          .toLowerCase()
          .includes(search),
      ),
    );
  });



  private mapRowsByTab(tab: string, data: SpareApiItem[]): SpareItem[] {
    return data.map((item: SpareApiItem): SpareItem => {
      switch (tab) {

        case "OBS":
        case "Mapped-OBS":
        case "History":
          return {
            // original fields for modal grid
            equipmentClass: item.equipmentClass,
            patternNo: item.patternNo,
            itemDesc: item.itemDesc,
            availabilityStatus: item.availabilityStatus,
            denomination: item.denomination,
            heldQty: item.heldQty,
            crpCategory: item.crpCategory,
            authority: item.authority,

            // normalized fields for selected grid & payload
            item_code: item.patternNo,
            item_desc: item.itemDesc,
            inventoryType: "OBS",
            crp_category: item.crpCategory,

            sourceTab: tab,
            qtyRequired: 1,
            pk: item.pk,
          };

        case "MO Inventory":
        case "Mapped-MO Inventory":
          return {
            item_code: item.item_code,
            item_desc: item.item_desc,
            status: item.status,
            crp_category: item.crp_category,
            denomination: item.denomination,

            inventoryType: "MO",
            sourceTab: tab,
            qtyRequired: 1,
            pk: item.pk,
          };

        case "WED Inventory":
          return {
            eqpt: item.eqpt,
            item_code: item.item_code,
            item_desc: item.item_desc,
            denomination: item.denomination,
            category: item.category,
            typeofspare: item.typeofspare,
            avail_status: item.avail_status,

            inventoryType: "WED",
            crp_category: item.typeofspare,

            sourceTab: tab,
            qtyRequired: 1,
            pk: item.pk,
          };

        case "Mapped-WED Inventory":
          return {
            item_code: item.item_code,
            item_desc: item.item_desc,
            denomination: item.denomination,
            category: item.category,
            typeofspare: item.typeofspare,
            avail_status: item.avail_status,
            wed_eqpt_name: item.wed_eqpt_name,
            sfd_equipment: item.sfd_equipment,

            inventoryType: "WED",
            crp_category: item.typeofspare,

            sourceTab: tab,
            qtyRequired: 1,
            pk: item.pk,
          };

        case "PIL":
          return {
            oemPartNo: item.oemPartNo,
            itemDesc: item.itemDesc,
            denomination: item.denomination,
            spareName: item.spareName,

            item_code: item.oemPartNo,
            item_desc: item.itemDesc,
            inventoryType: "PIL",
            crp_category: "",

            sourceTab: tab,
            qtyRequired: 1,
            pk: item.pk,
          };

        default:
          return {
            ...item,
            inventoryType: "OTHER",
            sourceTab: tab,
            qtyRequired: 1,
          };
      }
    });
  }
  // load spare parts

  async loadSpareParts(tab: string) {
    const apiType = this.tabTypeMap[tab];
    this.columnDefs.set([...(this.columnConfig[tab] || [])]);

    if (!apiType) {
      this.allRows.set([]);
      return;
    }

    try {
      const res = (await this.operationMaintenance.getDartSpares(apiType)) as
        | { data?: SpareApiItem[] }
        | undefined;
      const rows = this.mapRowsByTab(tab, res?.data || []);
      this.allRows.set(rows);
      // this.allRows.set(rows);
    } catch (error) {
      console.error(error);
      this.allRows.set([]);
    }
  }

  selectTab(tab: string) {
    this.selectedTab.set(tab);
    this.loadSpareParts(tab);
  }

  onSelectionChanged(rows: unknown[]) {
    const currentTab = this.selectedTab();
    this.selectedRowsByTab[currentTab] = rows as SpareItem[];
    this.selectedRows = Object.values(this.selectedRowsByTab).flat();
  }

  saveSelection() {
    this.save.emit(this.selectedRows);
    this.closeModal.emit();
  }

  private columnConfig: Record<string, ColDef[]> = {
    OBS: [
      { field: "equipmentClass", headerName: "Equipment Class" },
      { field: "patternNo", headerName: "Pattern No." },
      { field: "itemDesc", headerName: "Item Description" },
      { field: "availabilityStatus", headerName: "Availability Status" },
      { field: "denomination", headerName: "Denomination" },
      { field: "heldQty", headerName: "Held Qty" },
      { field: "crpCategory", headerName: "CRP Category" },
      { field: "authority", headerName: "Authority" },
    ],

    "Mapped-OBS": [
      { field: "sfdEquipmentName", headerName: "SFD Equipment Name" },
      { field: "equipmentClass", headerName: "Equipment Class" },
      { field: "patternNo", headerName: "Pattern No." },
      { field: "itemDesc", headerName: "Item Description" },
      { field: "availabilityStatus", headerName: "Availability Status" },
      { field: "denomination", headerName: "Denomination" },
      { field: "heldQty", headerName: "Held Qty" },
      { field: "itemCategory", headerName: "Item Category" },
      { field: "authority", headerName: "Authority" },
    ],

    "MO Inventory": [
      { field: "item_code", headerName: "MO Item Code" },
      { field: "item_desc", headerName: "Item Description" },
      { field: "status", headerName: "MO Availability Status" },
      { field: "availabilityStatus", headerName: "Availability Status" },
      { field: "crp_category", headerName: "CRP Category" },
      { field: "denomination", headerName: "Denomination" },
      { field: "itemLine", headerName: "Item Line" },
      { field: "priceRs", headerName: "Price (Rs)" },
      { field: "priceDate", headerName: "Price Date" },
      { field: "ilmEquipmentCode", headerName: "ILM Equipment Code" },
      { field: "ilmEquipmentDesc", headerName: "ILM Equipment Desc" },
      { field: "vendorCode", headerName: "Vendor Code" },
      { field: "vendorName", headerName: "Vendor Name" },
    ],

    "Mapped-MO Inventory": [
      { field: "item_code", headerName: "MO Item Code" },
      { field: "item_desc", headerName: "Item Description" },
      { field: "status", headerName: "MO Availability Status" },
      { field: "availabilityStatus", headerName: "Availability Status" },
      { field: "crp_category", headerName: "CRP Category" },
      { field: "denomination", headerName: "Denomination" },
      { field: "itemLine", headerName: "Item Line" },
      { field: "priceRs", headerName: "Price (Rs)" },
      { field: "priceDate", headerName: "Price Date" },
      { field: "ilmEquipmentCode", headerName: "ILM Equipment Code" },
      { field: "ilmEquipmentDesc", headerName: "ILM Equipment Desc" },
      { field: "vendorCode", headerName: "Vendor Code" },
      { field: "vendorName", headerName: "Vendor Name" },
      { field: "sfdEquipmentName", headerName: "SFD Equipment Name" },
    ],

    "WED Inventory": [
      { field: "eqpt", headerName: "WED Equipment Name" },
      { field: "item_code", headerName: "WED Item Code" },
      { field: "item_desc", headerName: "Item Description" },
      { field: "denomination", headerName: "Denomination" },
      { field: "category", headerName: "Item Category" },
      { field: "typeofspare", headerName: "WED Inventory Type" },
      { field: "avail_status", headerName: "Availability Status" },
    ],

    "Mapped-WED Inventory": [
      { field: "item_code", headerName: "WED Item Code" },
      { field: "item_desc", headerName: "Item Description" },
      { field: "denomination", headerName: "Denomination" },
      { field: "category", headerName: "Item Category" },
      { field: "typeofspare", headerName: "WED Inventory Type" },
      { field: "avail_status", headerName: "Availability Status" },
      { field: "wed_eqpt_name", headerName: "WED Equipment Name" },
      { field: "sfd_equipment", headerName: "SFD Equipment Name" },
    ],

    PIL: [
      { field: "oemPartNo", headerName: "OEM Part No" },
      { field: "itemDesc", headerName: "Item Description" },
      { field: "denomination", headerName: "Denomination" },
      { field: "spareName", headerName: "Spare Name" },
      { field: "action", headerName: "Action" },
    ],

    History: [
      {
        field: "equipmentClass",
        headerName: "Equipment Name",
      },
      {
        field: "patternNo",
        headerName: "Pattern Number / OEM Part Number",
      },
      {
        field: "crpCategory",
        headerName: "Spare Class",
      },
      {
        field: "itemDesc",
        headerName: "Spare Description",
        flex: 1,
      },
      {
        field: "crpCategory",
        headerName: "Category",
      },
      {
        field: "authority",
        headerName: "Authority",
      },
    ],

  };

}
