import { ColDef } from "ag-grid-community";
import { TransactionStubConfig } from "./transaction-stub";

const cols = (fields: [string, string, number?][]): ColDef[] =>
  fields.map(([field, headerName, width]) => (width ? { field, headerName, width } : { field, headerName, flex: 1 }));

export const CREATE_CART_CONFIG: TransactionStubConfig = {
  title: "Create Cart",
  fields: [
    {
      key: "authorityType",
      label: "Authority Type",
      kind: "select",
      options: [
        { label: "REP-Replenishment", value: "rep" },
        { label: "ARS-Auto Replenishment Store", value: "ars" },
        { label: "SPL-Special Demand", value: "spl" },
        { label: "PTS-Prior To Survey", value: "pts" },
      ],
    },
    { key: "itemCode", label: "Item Code", kind: "text" },
    { key: "itemDescription", label: "Item Description", kind: "text" },
    { key: "status", label: "Status", kind: "text" },
    { key: "crpCategory", label: "CRP Category", kind: "text" },
  ],
  columns: cols([
    ["srNo", "Sr No", 80],
    ["itemCode", "Item Code"],
    ["deno", "Deno"],
    ["crp", "CRP"],
    ["priceRs", "Price Rs"],
    ["incatYn", "INCATYN", 100],
    ["myStock", "My Stock"],
    ["logoStk", "Logo Stk"],
    ["qtyRequired", "Quantity Required"],
  ]),
  rows: [
    { srNo: 1, itemCode: "IT-001", deno: "PC", crp: "REP", priceRs: 45000, incatYn: "Y", myStock: "CR-105", logoStk: 10, qtyRequired: 10 },
    { srNo: 2, itemCode: "IT-002", deno: "Monitor", crp: "ARS", priceRs: 15000, incatYn: "Y", myStock: "CR-205", logoStk: 5, qtyRequired: 5 },
  ],
  primaryButtonLabel: "Add to Cart",
};

export const DEMAND_ACTION_CONFIG: TransactionStubConfig = {
  title: "Demand Action",
  fields: [
    { key: "demandFrom", label: "Demand Raised From", kind: "date" },
    { key: "demandTo", label: "Demand Raised To", kind: "date" },
    { key: "internalDemandNo", label: "Internal Demand No", kind: "text" },
    {
      key: "demandType",
      label: "Select Demand Type",
      kind: "select",
      options: [
        { label: "MOI", value: "MOI" },
        { label: "BVY", value: "BVY" },
        { label: "MOD", value: "MOD" },
      ],
    },
    {
      key: "authType",
      label: "Authority Type",
      kind: "select",
      options: [
        { label: "PTS", value: "PTS" },
        { label: "General", value: "General" },
        { label: "Certificate", value: "Certificate" },
      ],
    },
  ],
  columns: cols([
    ["internalDemandNo", "Internal Demand No"],
    ["dtRaised", "Dt Raised", 110],
    ["raisedFor", "Raised For (Cust Code)", 160],
    ["raisedOn", "Raised On (SubDept)", 150],
    ["demandType", "Demand Type", 110],
    ["authType", "Auth Type", 110],
    ["closed", "Closed", 90],
  ]),
  rows: [
    { internalDemandNo: "25BSE02RG000166", dtRaised: "05/02/26", raisedFor: "4121", raisedOn: "G002", demandType: "MOI", authType: "PTS", closed: "No" },
    { internalDemandNo: "25BSE02RG000167", dtRaised: "04/02/26", raisedFor: "4122", raisedOn: "G003", demandType: "BVY", authType: "Certificate", closed: "Yes" },
  ],
};

export const ISSUE_AUTHORISE_CONFIG: TransactionStubConfig = {
  title: "Issue Authorise",
  fields: [
    {
      key: "demandType",
      label: "Demand Type",
      kind: "select",
      options: [
        { label: "Demands Pending for Issue", value: "pending" },
        { label: "Closed demand", value: "closed" },
      ],
    },
    { key: "internalDemandNo", label: "Internal Demand No", kind: "text" },
    {
      key: "specification",
      label: "Specification",
      kind: "select",
      options: [
        { label: "ABR", value: "ABR" },
        { label: "ARS", value: "ARS" },
        { label: "PTS", value: "PTS" },
      ],
    },
  ],
  columns: cols([
    ["srNo", "Sr No", 80],
    ["internalDemandNo", "Internal Demand No", 160],
    ["authorityTp", "AuthorityTP", 120],
    ["itemCode", "Item Code", 110],
    ["deptCode", "Dept Code", 110],
    ["demandQty", "Demand Qty", 110],
    ["issueQty", "Issue Qty", 110],
  ]),
  rows: [
    { srNo: 1, internalDemandNo: "IA-2026-001", authorityTp: "AUTH-001", itemCode: "ITM001", deptCode: "DEPT001", demandQty: 100, issueQty: 50 },
    { srNo: 2, internalDemandNo: "IA-2026-002", authorityTp: "AUTH-002", itemCode: "ITM002", deptCode: "DEPT002", demandQty: 250, issueQty: 150 },
  ],
};

export const DEMAND_CONSOLIDATION_CONFIG: TransactionStubConfig = {
  title: "Demand Consolidation",
  fields: [
    {
      key: "demandType",
      label: "Demand Type",
      kind: "select",
      options: [
        { label: "Consolidated Demand to be Forward for HQ Approval", value: "hq" },
        { label: "Consolidated Demand to be Forward to Mo", value: "mo" },
      ],
    },
    { key: "itemCode", label: "Item Code", kind: "text" },
    {
      key: "authorityCode",
      label: "Authority Type",
      kind: "select",
      options: [
        { label: "ABR", value: "ABR" },
        { label: "ARS", value: "ARS" },
        { label: "PTS", value: "PTS" },
      ],
    },
  ],
  columns: cols([
    ["srNo", "Sr No", 80],
    ["custCode", "Cust Code"],
    ["itemCode", "Item Code", 110],
    ["description", "Description"],
    ["demandQty", "Demand Qty", 120],
  ]),
  rows: [
    { srNo: 1, custCode: "EA3050TRN421529402060", itemCode: "ITM001", description: "Diesel, rubber, ship related items", demandQty: 100 },
    { srNo: 2, custCode: "EA3050TRN421529402061", itemCode: "ITM002", description: "Diesel, rubber, ship related items", demandQty: 250 },
  ],
};

export const CONSUMPTION_CONFIG: TransactionStubConfig = {
  title: "Consumption",
  fields: [
    {
      key: "selectOption",
      label: "Select Options",
      kind: "select",
      options: [{ label: "Initiate Consumption", value: "initiate" }],
    },
    { key: "itemCode", label: "Item Code", kind: "text" },
    {
      key: "consumptionType",
      label: "Consumption Type",
      kind: "select",
      options: [{ label: "Staff Consumption", value: "staff" }],
    },
    { key: "consumptionCode", label: "Consumption Code", kind: "text" },
    { key: "mosd", label: "MOSD", kind: "text" },
  ],
  columns: cols([
    ["srNo", "Sr No", 80],
    ["itemCode", "Item Code", 110],
    ["itemDesc", "Item Desc"],
    ["crp", "CRP", 90],
    ["deno", "Deno", 90],
    ["consumptionCode", "Consumption Code", 150],
    ["moQty", "Mo Qty", 100],
    ["stationCode", "Station Code", 110],
  ]),
  rows: [
    { srNo: 1, itemCode: "IT-001", itemDesc: "Laptop Computer", crp: "CR-105", deno: "45000", consumptionCode: "Yes", moQty: "Yes", stationCode: "K" },
  ],
};

export const SURVEY_CONFIG: TransactionStubConfig = {
  title: "Survey",
  fields: [
    {
      key: "surveyType",
      label: "Select Option",
      kind: "select",
      options: [
        { label: "Initiate Survey", value: "initiate" },
        { label: "Initial Survey NOMM", value: "nomm" },
      ],
    },
    { key: "dateFrom", label: "Date From", kind: "date" },
    { key: "dateTo", label: "Date To", kind: "date" },
    { key: "itemCode", label: "Item Code", kind: "text" },
    { key: "internalSurveyNo", label: "Internal Survey No", kind: "text" },
  ],
  columns: cols([
    ["srNo", "Sr No", 80],
    ["itemCode", "Item Code", 110],
    ["desc", "Desc"],
    ["internalSurveyNo", "Internal Survey No", 150],
    ["moSurveyNo", "MO Survey No", 130],
    ["qty", "Qty", 90],
    ["totalPrice", "Total Price", 110],
  ]),
  rows: [
    { srNo: 1, itemCode: "ITM001", desc: "Item Description 1", internalSurveyNo: "ISN-2026-001", moSurveyNo: "MSN-2026-001", qty: 100, totalPrice: 100000 },
    { srNo: 2, itemCode: "ITM002", desc: "Item Description 2", internalSurveyNo: "ISN-2026-002", moSurveyNo: "MSN-2026-002", qty: 150, totalPrice: 225000 },
  ],
};

export const STOCK_TRANSFER_CONFIG: TransactionStubConfig = {
  title: "Stock Transfer",
  fields: [
    {
      key: "authorityType",
      label: "Authority Type",
      kind: "select",
      options: [
        { label: "General Query Stock", value: "general" },
        { label: "StockTransfers Pending For Approval", value: "pending" },
      ],
    },
    { key: "itemCode", label: "Item Code", kind: "text" },
  ],
  columns: cols([
    ["srNo", "Sr No", 80],
    ["shNo", "ShNo", 90],
    ["itemCode", "Item Code", 110],
    ["itemDesc", "Item Desc"],
    ["deno", "Deno", 90],
    ["qty", "Qty", 90],
  ]),
  rows: [
    { srNo: 1, shNo: "REP", itemCode: "IT-001", itemDesc: "Laptop Computer", deno: "PC", qty: 10 },
    { srNo: 2, shNo: "ARS", itemCode: "IT-002", itemDesc: "Monitor 24 inch", deno: "Monitor", qty: 5 },
  ],
};

export const OBS_MASTER_CONFIG: TransactionStubConfig = {
  title: "OBS Master",
  fields: [
    {
      key: "criteria",
      label: "Select Criteria",
      kind: "select",
      options: [{ label: "Initialized Consumption", value: "init" }],
    },
    { key: "itemCode", label: "Item Code", kind: "text" },
    { key: "itemDescription", label: "Item Description", kind: "text" },
  ],
  columns: cols([
    ["srNo", "Sr No", 80],
    ["itemCode", "ItemCode", 120],
    ["itemDesc", "Item Disc"],
    ["crpCategory", "CRP Category", 130],
    ["equipmentCode", "Equipment Code", 140],
    ["shipAllowance", "Ship Allowance", 130],
    ["stock", "Stock", 100],
  ]),
  rows: [
    { srNo: 1, itemCode: "IA-2026-001", itemDesc: "Pressure Gauge", crpCategory: "AUTH-001", equipmentCode: "DEPT001", shipAllowance: "LGO-STK-001", stock: 100 },
    { srNo: 2, itemCode: "IA-2026-002", itemDesc: "Hydraulic Pump", crpCategory: "AUTH-002", equipmentCode: "DEPT002", shipAllowance: "LGO-STK-002", stock: 250 },
  ],
};
