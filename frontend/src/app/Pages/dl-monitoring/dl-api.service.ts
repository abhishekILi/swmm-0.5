import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, forkJoin, map, of } from 'rxjs';
import { ApiResponse, DlHistory, DlHistoryResponse, DlRecord, DlTrackingResponse, DlType } from './models';
import { environment } from '../../../environments/environment';

/** `dashboard-counts/` returns dl1/dl2/dl3 either at the top level or nested under `data`. */
interface DashboardCountsResponse {
  data?: { dl1?: number; dl2?: number; dl3?: number };
  dl1?: number;
  dl2?: number;
  dl3?: number;
}

@Injectable({ providedIn: 'root' })
export class DlApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl + 'api/v1/dl-monitoring';

  // private get csrf(): string {
  //   return document.cookie.split('; ').find(v => v.startsWith('csrftoken='))?.split('=')[1] ?? '';
  // }
  // private get jsonOptions() { return { headers: new HttpHeaders({ 'X-CSRFToken': this.csrf }) }; }

  counts(): Observable<{ dl1: number; dl2: number; dl3: number }> {
    return this.http.get<DashboardCountsResponse>(`${this.base}/dashboard-counts/`).pipe(
      map(res => {
        if (res && typeof res === 'object') {
          const data = res.data ?? res;
          return {
            dl1: Number(data.dl1 ?? 0),
            dl2: Number(data.dl2 ?? 0),
            dl3: Number(data.dl3 ?? 0),
          };
        }
        return { dl1: 0, dl2: 0, dl3: 0 };
      })
    );
  }

  private static readonly ENDPOINT_BY_TYPE: Record<Exclude<DlType, 'ALL'>, string> = {
    DL1: 'dl_tracking',
    DL2: 'dl2tracking',
    DL3: 'dl3tracking',
  };

  records(type: DlType): Observable<DlRecord[]> {
    if (type === 'ALL') {
      return forkJoin([
        this.records('DL1').pipe(catchError(() => of([]))),
        this.records('DL2').pipe(catchError(() => of([]))),
        this.records('DL3').pipe(catchError(() => of([])))
      ]).pipe(
        map(([dl1, dl2, dl3]) => [
          ...dl1.map(r => ({ ...r, dl_type: r.dl_type || 'DL1' })),
          ...dl2.map(r => ({ ...r, dl_type: r.dl_type || 'DL2' })),
          ...dl3.map(r => ({ ...r, dl_type: r.dl_type || 'DL3' }))
        ])
      );
    }
    const endpoint = DlApiService.ENDPOINT_BY_TYPE[type];
    return this.http.get<DlTrackingResponse | DlRecord[]>(`${this.base}/${endpoint}/`).pipe(
      map(res => {
        const rows = Array.isArray(res) ? res : (res?.data ?? []);
        return rows.map(r => ({ ...r, dl_type: r.dl_type || type }));
      })
    );
  }
  history(): Observable<DlHistory[]> {
    return this.http.get<DlHistoryResponse | DlHistory[]>(`${this.base}/dl_history/`).pipe(
      map(res => Array.isArray(res) ? res : (res?.data ?? (res as { results?: DlHistory[] })?.results ?? []))
    );
  }
  importExcel(body: FormData): Observable<ApiResponse> { return this.http.post<ApiResponse>(`${this.base}/import-excel/`, body); }
  update(payload: Partial<DlRecord> & { id: number }): Observable<ApiResponse> { return this.http.post<ApiResponse>(`${this.base}/update_dl_tracking/`, payload); }
  close(payload: { id: number; er_date: string; start_work: string; complete_work: string }): Observable<ApiResponse> { return this.http.post<ApiResponse>(`${this.base}/close_dl_tracking/`, payload); }
  sync(type: DlType): Observable<ApiResponse<DlRecord[]>> { return this.http.post<ApiResponse<DlRecord[]>>(`${this.base}/sync_navyojana/`, { dl_type: type }); }
}
