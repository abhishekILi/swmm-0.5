
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ApiService } from './api.service';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
  selector: 'app-report',
  standalone: true,
  imports: [CommonModule],

  template: `
    <div class="report-container">

      <div *ngIf="isLoading">
        Loading report data...
      </div>

      <div *ngIf="!isLoading && reportData.length === 0">
        No report data found.
      </div>

      <div
        *ngIf="reportHtml"
        class="report-content"
        [innerHTML]="reportHtml">
      </div>

    </div>
  `,

  styles: [`
    .report-container {
      padding: 20px;
    }

    .report-content {
      border: 1px solid #ccc;
      padding: 10px;
      background-color: #f9f9f9;
    }

    /* HTML coming from [innerHTML] */
    .report-content .bg-white > div {
      width: 100%;
      display: flex;
      justify-content: space-between;
    }

   .report-content .bg-white > div > div:first-child img, .report-content .bg-white > div > div:last-child img { width: 50px !important; height: 50px !important; object-fit: contain !important; }
  `]
})
export class ReportComponent implements OnInit {

  reportData: any[] = [];
  reportHtml: SafeHtml | null = null;
  isLoading = false;

  constructor(
    private api: ApiService,
    private route: ActivatedRoute,
    private sanitizer: DomSanitizer,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {

    this.route.queryParams.subscribe(params => {

      const formId = params['trial'];

      if (!formId) {
        return;
      }

      this.isLoading = true;
      this.cdr.detectChanges();

      this.api
        .get('api/reports/trial-reports/', {
          trial_id: formId
        })
        .subscribe({

          next: (res: any) => {

            this.isLoading = false;

            const reports = Array.isArray(res)
              ? res
              : (res?.data ?? []);

            this.reportData = reports;

            const html = reports[0]?.json_data;

            console.log('Report API Response:', html);
            console.log('Type:', typeof html);

            if (typeof html === 'string') {
              this.reportHtml =
                this.sanitizer.bypassSecurityTrustHtml(html);
            } else {
              this.reportHtml = null;
            }

            this.cdr.detectChanges();
          },

          error: (error) => {

            this.isLoading = false;

            console.error('Report API Error:', error);

            this.reportData = [];
            this.reportHtml = null;

            this.cdr.detectChanges();
          }
        });
    });
  }

  get reportJson(): any {
    return this.reportData.length > 0
      ? this.reportData[0].json_data
      : null;
  }
}
