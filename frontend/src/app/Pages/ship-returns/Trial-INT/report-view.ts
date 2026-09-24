import { ChangeDetectorRef, Component, OnInit, ViewEncapsulation } from '@angular/core';
import { Location, CommonModule } from '@angular/common';
import { ApiService } from './api.service';
import { ActivatedRoute } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
  selector: 'app-report',
  standalone: true,
  imports: [CommonModule],
  encapsulation: ViewEncapsulation.None,

  template: `
    <div class="report-container min-h-screen md:p-8">

      <!-- Top Toolbar (Print / Back) -->
      <!-- <div class="no-print max-w-[1400px] mx-auto mb-4 flex items-center justify-between bg-slate-800/90 p-3 rounded-lg border border-slate-700/60 shadow-md">
        <button (click)="goBack()" type="button" class="inline-flex items-center gap-2 px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium transition-colors cursor-pointer">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4">
            <path d="M12.5 15L7.5 10L12.5 5"></path>
          </svg>
          Back
        </button>
        <span class="text-sm font-semibold text-white">Trial Report Preview</span>
        <button (click)="printReport()" type="button" class="inline-flex items-center gap-2 px-4 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow transition-colors cursor-pointer">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4">
            <path d="M5 7V3h10v4M5 14H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-2M5 11h10v6H5v-6z"></path>
          </svg>
          Print / Save PDF
        </button>
      </div> -->

      <!-- Loading State -->
      <div *ngIf="isLoading" class="max-w-[1400px] mx-auto bg-slate-800/50 rounded-xl p-12 text-center border border-slate-700/50 text-slate-300">
        <div class="w-8 h-8 border-3 border-sky-500/30 border-t-sky-500 rounded-full animate-spin mx-auto mb-2"></div>
        Loading report data...
      </div>

      <!-- Empty State -->
      <div *ngIf="!isLoading && reportData.length === 0" class="max-w-[1400px] mx-auto bg-slate-800/50 rounded-xl p-12 text-center border border-slate-700/50 text-slate-300">
        No report data found.
      </div>

      <!-- Report Paper Page -->
      <div *ngIf="reportHtml" class="report-paper-card max-w-[1400px] mx-auto bg-white rounded-xl shadow-2xl p-4 sm:p-8 border border-slate-200 min-h-[800px]">
        <div
          class="report-content"
          [innerHTML]="reportHtml">
        </div>
      </div>

    </div>
  `,

  styles: [`
   
    /* Force all report logos/images to be properly sized and constrained at the top */
     .report-content img {
       max-height: 68px !important;
       max-width: 68px !important;
       width: 68px !important;
       height: 68px !important;
       object-fit: contain !important;
       display: inline-block !important;
       vertical-align: middle !important;
     }

     /* Report HTML is loaded dynamically, so Tailwind may not generate this utility. */
     .report-content [class~="!justify-between"],
     .report-content [class~="justify-between"] {
       justify-content: space-between !important;
     }

     /* Apply colors to the dynamically loaded report header and equipment label. */
     .report-content [class*="bg-[#dcefd2]"] {
       background-color: #dcefd2 !important;
       padding: 5px;
       border: 3px solid #82919a ;
     }

     .report-content [class*="bg-[#2874c6]"] {
       background-color: #2874c6 !important;
       padding: 4px;
       border-radius: 3px;
       color: #ffffff !important;
     }

     .report-content h1 {
       font-size: 1.5rem !important;
       font-weight: 800 !important;
       line-height: 1.2 !important;
     }

     .report-content h3 {
       font-size: 1rem !important;
       font-weight: 700 !important;
       line-height: 1.25 !important;
     }

     
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
    private cdr: ChangeDetectorRef,
    private location: Location
  ) { }

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

            const rawHtml = reports[0]?.json_data;

            console.log('Report API Response:', rawHtml);

            if (typeof rawHtml === 'string' && rawHtml.trim()) {
              this.reportHtml = this.prepareReportHtml(rawHtml);
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

  private prepareReportHtml(rawHtml: string): SafeHtml {
    // 1. Un-escape HTML entities like &lt;span...&gt; so they parse as real DOM tags
    let cleaned = rawHtml.replace(/&lt;/g, '<').replace(/&gt;/g, '>');

    // 2. Bypass Angular security sanitizer for innerHTML
    return this.sanitizer.bypassSecurityTrustHtml(cleaned);
  }

  goBack(): void {
    this.location.back();
  }

  printReport(): void {
    window.print();
  }

  get reportJson(): any {
    return this.reportData.length > 0
      ? this.reportData[0].json_data
      : null;
  }
}
