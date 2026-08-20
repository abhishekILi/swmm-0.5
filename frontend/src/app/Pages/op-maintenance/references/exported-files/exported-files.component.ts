import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ColDef } from 'ag-grid-community';
import { firstValueFrom } from 'rxjs';

import { DataGrid } from '../../../../shared/components/data-grid/data-grid';
import { Call } from '../../../../services/network/call';
import { Router } from '@angular/router';

export interface GeneratedDlIiReport {
  id: number;
  ra_dl_name: string;
  dockyard_name: string;
  refit: string;
  rows_count: number;
  created_date: string;
}

interface ExportedFileRow {
  serialNo: number;
  id: number;
  raDlName: string;
  dockyard: string;
  refit: string;
  rows: number;
  createdDate: string;
}

@Component({
  selector: 'app-exported-files',
  standalone: true,
  imports: [
    CommonModule,
    DataGrid
  ],
  templateUrl: './exported-files.component.html',
  styleUrls: ['./exported-files.component.scss']
})
export class ExportedFilesComponent implements OnInit {
  private call = inject(Call);
  private router = inject(Router);


  rowData = signal< ExportedFileRow[]>([])
  errorMessage = '';

  ngOnInit(): void {
    void this.loadReports();
  }

  async loadReports(): Promise<void> {
    try {
      const res: GeneratedDlIiReport[] = await firstValueFrom(this.call.getGeneratedDlIiReports());

      const rows = (res || []).map(
        (item: GeneratedDlIiReport, index: number) => ({
          serialNo: index + 1,
          id: item.id,
          raDlName: item.ra_dl_name,
          dockyard: item.dockyard_name,
          refit: item.refit,
          rows: item.rows_count,
          createdDate: item.created_date
        })
      );

      this.rowData.set(rows)
    } catch {
      this.errorMessage = 'Failed to load reports';
      this.rowData.set([]);
    }
  }

  columnDefs: ColDef[] = [
    {
      headerName: 'Serial No.',
      field: 'serialNo',
      width: 120
    },
    {
      headerName: 'RA/DL Name',
      field: 'raDlName',
      flex: 2,
      minWidth: 220
    },
    {
      headerName: 'Dockyard',
      field: 'dockyard',
      flex: 1.5,
      minWidth: 180
    },
    {
      headerName: 'Refit',
      field: 'refit',
      width: 140
    },
    {
      headerName: 'Rows (No of Series)',
      field: 'rows',
      width: 180
    },
    {
      headerName: 'Created Date',
      field: 'createdDate',
      width: 180
    },
    {
      headerName: 'Actions',
      //field: 'id',
      width: 140
    }
  ];

  backToDarts(): void {
    this.router.navigateByUrl("/afterAuth/op-maintenance/open-darts", {
        replaceUrl: true,
      });
  }
}
