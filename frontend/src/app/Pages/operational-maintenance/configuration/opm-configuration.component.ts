import {
  ChangeDetectionStrategy,
  Component,
  computed,
  signal,
} from "@angular/core";
import { ColDef } from "ag-grid-community";
import { CollapsibleSidebar } from "../../../shared/components/collapsible-sidebar/collapsible-sidebar";
import { DataGrid, IconComponent , StatusChip} from "../../../shared/components";

@Component({
  selector: "app-opm-configuration",
  standalone: true,
  imports: [CollapsibleSidebar, DataGrid, IconComponent, StatusChip],
  templateUrl: "./opm-configuration.component.html",
  styleUrls: ["./opm-configuration.component.css"],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OpmConfigurationComponent {
  readonly referenceSidebarCollapsed = signal(false);
  readonly selectedReferenceSection = signal("raTypeMaster");
  readonly referenceSections = signal([
    {
      id: "raTypeMaster",
      title: "RA Type Master",
      icon: "route",
      subHeading: "HQ-issued repair agencies and RA types. Read only.",
      // count: 2,
      description: "HQ-issued repair agencies and RA types. Read only.",
    },
    {
      id: "shipMasterRemarks",
      title: "Ship Remarks Master",
      icon: "message-square",
      subHeading: "Ship remark codes selectable against each DART when an RA is drafted (3.7).",
      // count: 2,
      description: "Ship remark codes selectable against each DART when an RA is drafted (3.7).",
    },
    {
      id: "certificateTypeMaster",
      title: "Certificate Type Master",
      icon: "message-square",
      subHeading: "",
      count: 2,
      description: "HQ-issued certificate types recorded when a defect cannot be resolved. Source: Configuration (HQ-issued). Read only.",
    },
    {
      id: "outComeMaster",
      title: "Deferral Outcome Master (DTNR)",
      icon: "award",
      subHeading: "",
      count: 2,
      description: "Deferral decision outcomes recorded when a defect is temporarily not rectifiable. DTNR is a deferral decision, not a certificate. Source: Configuration (HQ-issued). Read only.",
    },
    {
      id: "equipGuaranteeMaster",
      title: "Equipment Guarantee Master",
      icon: "truck",
      subHeading: "",
      count: 2,
      description: "Per-equipment guarantee coverage. Source: Configuration, per equipment. Ship Staff / HOD / CO act on it via the guarantee coverage workflow (3.5) but do not edit the master directly. Read only.",
    },

    {
      id: "repairAgencyMaster",
      title: "Repair Agency Master",
      icon: "users",
      subHeading: "",
      count: 2,
      description: "Authorised repair agencies to which a DART / RA can be routed. Source: Configuration (HQ-issued). Read only.",
    },
    {
      id: "assistanceMaster",
      title: "Assistance Master",
      icon: "users",
      subHeading: "",
      count: 2,
      description: "Trade / department categories of assistance selectable when raising a Required Assistance (RA).",
    },
    {
      id: "equipmentStatusMaster",
      title: "Equipment Status Master",
      icon: "users",
      subHeading: "",
      count: 2,
      description: "Operational status recorded against equipment during defect capture; drives readiness impact.",
    },
    {
      id: "reasonMaster",
      title: "Reason Master",
      icon: "users",
      subHeading: "",
      count: 2,
      description: "Drives branch logic at transaction initiation — the selected reason renders the applicable fields and workflow.",
    },
    {
      id: "servityMaster",
      title: "Severity Master",
      icon: "users",
      subHeading: "",
      count: 2,
      description: "Defines operational severity and tooltip guidance shown during defect capture.",
    },
    {
      id: "servicesMaster",
      title: "Services Master",
      icon: "users",
      subHeading: "",
      count: 2,
      description: "Defines operational severity and tooltip guidance shown during defect capture.",
    },
  ]);

  readonly referenceSidebarItems = computed(() =>
    this.referenceSections().map((item) => ({
      id: item.id,
      label: item.title,
      subHeading: item.subHeading,
      badge: item.count,
      icon: item.icon,
    }))
  );

  readonly referenceDataMap: Record<
    string,
    {
      columns: ColDef[];
      rows: Record<string, unknown>[];
    }
    > = {
      raTypeMaster: {
        columns: [
          { headerName: "RA Type", field: "type", flex: 1 },
          { headerName: "Description", field: "description", flex: 2 },
          { headerName: "Routing", field: "routing", flex: 2 },
          { headerName: "Ship Remarks Prefix", field: "prefix", flex: 1.5 },
        ],
        rows: [
          {
            type: "OP RA",
            description: "Standard operational Required Assistance",
            routing: "Ship → FMU → Yard",
            prefix: "DAN",
          },
          {
            type: "AMP",
            description: "Assisted Maintenance Period RA",
            routing: "HQ-authorised harbour period",
            prefix: "SSRR",
          },
          {
            type: "SMP",
            description: "Self Maintenance Period RA",
            routing: "Scheduled harbour period",
            prefix: "SSRR",
          },
          {
            type: "Signal RA",
            description: "RA transmitted in signal / letter form",
            routing: "Ship sailing, no connectivity",
            prefix: "DAN",
          },
          {
            type: "Normal RA",
            description: "Default RA pathway",
            routing: "Not tied to AMP / SMP / signal",
            prefix: "DAN",
          },
        ],
      },

      shipMasterRemarks: {
        columns: [
          { headerName: "Remark", field: "remark", flex: 1 },
          { headerName: "Raised By", field: "raisedBy", flex: 1 },
          { headerName: "Used On", field: "usedOn", flex: 1 },
        ],
        rows: [
          { remark: "hi", raisedBy: "me", usedOn: 'tomorrow'  }
        ]
      },

      certificateTypeMaster: {
        columns: [
          { headerName: "Certificate", field: "certificate", flex: 1 },
          { headerName: "Meaning", field: "meaning", flex: 2 },
        ],
        rows: [
          { certificate: "NAC", meaning: "No Assistance / Action Certificate" },
          { certificate: "NFC", meaning: "No Fault Certificate" },
          { certificate: "BER", meaning: "Beyond Economical Repair" },
          { certificate: "BLR", meaning: "Beyond Local Repair" },
        ],
      },

      outComeMaster: {
        columns: [
          { headerName: "Outcome", field: "outcome", flex: 1 },
          { headerName: "Meaning", field: "meaning", flex: 2 },
          { headerName: "Applies When", field: "appliesWhen", flex: 2 },
        ],
        rows: [
          {
            outcome: "DTNR",
            meaning: "Defect Temporarily Not Rectifiable",
            appliesWhen: "Repair deferred to a later maintenance opportunity",
          },
          {
            outcome: "DTNR (AMP)",
            meaning: "Deferred to next Assisted Maintenance Period",
            appliesWhen: "Requires HQ-authorised harbour period",
          },
          {
            outcome: "DTNR (SMP)",
            meaning: "Deferred to next Self Maintenance Period",
            appliesWhen: "Scheduled harbour period",
          },
          {
            outcome: "DTNR (Refit)",
            meaning: "Deferred to next planned refit",
            appliesWhen: "Beyond local / harbour capability",
          },
        ],
      },


      equipGuaranteeMaster: {
        columns: [
          { headerName: "Equipment", field: "equipment", flex: 2 },
          { headerName: "Guarantee Start", field: "start", flex: 1.5 },
          { headerName: "Guarantee End", field: "end", flex: 1.5 },
          { headerName: "Coverage", field: "coverage", flex: 1.5 },
        ],
        rows: [
          {
            equipment: "LO Pump - ME No.1",
            start: "01-Aug-2024",
            end: "31-Jul-2026",
            coverage: "Under Guarantee",
          },
          {
            equipment: "Sea Viper Director",
            start: "15-Mar-2023",
            end: "14-Mar-2025",
            coverage: "Expired",
          },
          {
            equipment: "Gyro Compass",
            start: "10-Jun-2025",
            end: "09-Jun-2027",
            coverage: "Under Guarantee",
          },
          {
            equipment: "Diesel Alternator",
            start: "01-Jan-2025",
            end: "31-Dec-2026",
            coverage: "Under Guarantee",
          },
          {
            equipment: "Fire Main Pump",
            start: "20-Sep-2022",
            end: "19-Sep-2024",
            coverage: "Expired",
          },
        ],
      },



      repairAgencyMaster: {
        columns: [
          { headerName: "Agency", field: "agency", flex: 1 },
          { headerName: "Description", field: "description", flex: 2 },
          { headerName: "Location", field: "location", flex: 1 },
          { headerName: "Type", field: "type", flex: 1 },
        ],
        rows: [
          { agency: "ND(Mbi)", description: "Naval Dockyard, Mumbai", location: "Mumbai", type: "Dockyard" },
          { agency: "ND(V)", description: "Naval Dockyard, Visakhapatnam", location: "Visakhapatnam", type: "Dockyard" },
          { agency: "NSRY(KAR)", description: "Naval Ship Repair Yard, Karwar", location: "Karwar", type: "Ship Repair Yard" },
          { agency: "NSRY(KOC)", description: "Naval Ship Repair Yard, Kochi", location: "Kochi", type: "Ship Repair Yard" },
          { agency: "NSRY(Pbr)", description: "Naval Ship Repair Yard, Porbandar", location: "Porbandar", type: "Ship Repair Yard" },
          { agency: "FTSU", description: "Fleet Technical Support Unit", location: "Fleet", type: "Support Unit" },
          { agency: "FMU", description: "Fleet Maintenance Unit", location: "Fleet", type: "Maintenance Unit" },
        ],
      },


      assistanceMaster: {
        columns: [
          { headerName: "Assistance", field: "assistance", flex: 1 },
          { headerName: "Description", field: "description", flex: 2 },
          { headerName: "Owning Department", field: "department", flex: 1.5 },
        ],
        rows: [
          { assistance: "Hull", description: "Hull, structure & fittings", department: "Marine Eng" },
          { assistance: "Engineering", description: "Propulsion & auxiliary machinery", department: "Marine Eng" },
          { assistance: "Electrical", description: "Electrical power & distribution", department: "Marine Eng" },
          { assistance: "Aviation", description: "Aviation support systems", department: "Aviation Support" },
          { assistance: "NBCD", description: "Nuclear, biological, chemical & damage control", department: "Damage Control" },
          { assistance: "Domestic", description: "Domestic & hotel services", department: "Logistics" },
          { assistance: "Weapon", description: "Weapon & sensor systems", department: "Weapon Eng" },
        ],
      },

      equipmentStatusMaster: {
        columns: [
          { headerName: "Status", field: "status", flex: 1 },
          { headerName: "Description", field: "description", flex: 2 },
          { headerName: "Readiness Impact", field: "impact", flex: 1.5 },
        ],
        rows: [
          { status: "Ops", description: "Fully operational", impact: "None" },
          { status: "Totally Non Ops", description: "Equipment wholly unavailable", impact: "Critical" },
          { status: "Partial Non Ops", description: "Partially available with limitations", impact: "Degraded" },
        ],
      },

      reasonMaster: {
        columns: [
          { headerName: "Reason", field: "reason", flex: 1 },
          { headerName: "Sub-Types", field: "subTypes", flex: 2 },
          { headerName: "Drives", field: "drives", flex: 2 },
        ],
        rows: [
          { reason: "As&As", subTypes: "Major, Minor", drives: "Alteration & Addition flow" },
          { reason: "ABER", subTypes: "CAT I, CAT II, CAT III", drives: "Broken / Expended / Survey flow" },
          { reason: "Defect", subTypes: "Rectified Yes / No", drives: "Standard defect lifecycle" },
          { reason: "Services", subTypes: "Painting, Crane, Diving ...", drives: "Dockyard service request flow" },
        ],
      },

      servityMaster: {
        columns: [
          { headerName: "Severity", field: "severity", flex: 1 },
          { headerName: "Description", field: "description", flex: 2 },
          { headerName: "Colour", field: "colour", flex: 1 },
        ],
        rows: [
          { severity: "OPDEF", description: "Operationally defective — readiness impacting", colour: "Red" },
          { severity: "OPDEF (STA)", description: "OPDEF with staff target date", colour: "Amber" },
          { severity: "Normal Defect", description: "Routine defect, no readiness impact", colour: "Blue" },
        ],
      },

      servicesMaster: {
        columns: [
          { headerName: "Service", field: "service", flex: 1 },
          { headerName: "Type", field: "type", flex: 2 },
          { headerName: "Requires Equipment", field: "requiresEquipment", flex: 1.5 },
        ],
        rows: [
          { service: "Painting", type: "Hull & structure", requiresEquipment: "Optional" },
          { service: "Staging", type: "Access", requiresEquipment: "Optional" },
          { service: "Scaffolding", type: "Access", requiresEquipment: "Optional" },
          { service: "Crane", type: "Lifting", requiresEquipment: "Optional" },
          { service: "Diving", type: "Underwater", requiresEquipment: "No" },
          { service: "Cleaning", type: "Housekeeping", requiresEquipment: "No" },
          { service: "Chipping", type: "Surface preparation", requiresEquipment: "Optional" },
          { service: "Fabrication", type: "Workshop", requiresEquipment: "Optional" },
          { service: "Housekeeping", type: "General", requiresEquipment: "No" },
        ],
      },


    };

  readonly currentReference = computed(() => {
    return (
      this.referenceSections().find(
        (x) => x.id === this.selectedReferenceSection()
      ) ?? this.referenceSections()[0]
    );
  });

  readonly referenceColumnDefs = computed(
    () =>
      this.referenceDataMap[this.selectedReferenceSection()]?.columns ?? []
  );

  readonly referenceRowData = computed(
    () => this.referenceDataMap[this.selectedReferenceSection()]?.rows ?? []
  );

  readonly referenceTotalCount = computed(
    () => this.referenceRowData().length
  );

  dynamicGridHeight(): string {
    return "calc(100vh - 250px)";
  }

  selectReference(id: string): void {
    this.selectedReferenceSection.set(id);
  }

  // loadReferencePage(: { page: number; pageSize: number }): void {
  //   // No-op for dummy data.
  // }
}
