import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import {
  PlannerActivityDto,
  PlannerActivityPayload,
  PlannerActivityQuery,
  PlannerChoicesDto,
  PlannerDartTrendDto,
  PlannerDashboardDto,
  PlannerOverdueDartsResponseDto,
  PlannerSummaryDto,
} from '../models/planner-api.models';

@Injectable({
  providedIn: 'root',
})
export class PlannerApiService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = `${environment.apiUrl}api/v1/events/planner-activities/`;

  getActivities(query: PlannerActivityQuery = {}): Observable<PlannerActivityDto[]> {
    return this.http.get<PlannerActivityDto[]>(this.baseUrl, {
      params: this.toParams(query),
    });
  }

  getSummary(query: PlannerActivityQuery = {}): Observable<PlannerSummaryDto> {
    return this.http.get<PlannerSummaryDto>(`${this.baseUrl}summary/`, {
      params: this.toParams(query),
    });
  }

  getChoices(): Observable<PlannerChoicesDto> {
    return this.http.get<PlannerChoicesDto>(`${this.baseUrl}choices/`);
  }

  getDashboard(query: PlannerActivityQuery = {}): Observable<PlannerDashboardDto> {
    return this.http.get<PlannerDashboardDto>(`${this.baseUrl}dashboard/`, {
      params: this.toParams(query),
    });
  }

  getDartTrend(): Observable<PlannerDartTrendDto> {
    return this.http.get<PlannerDartTrendDto>(`${this.baseUrl}dart-trend/`);
  }

  getOverdueDarts(): Observable<PlannerOverdueDartsResponseDto> {
    return this.http.get<PlannerOverdueDartsResponseDto>(`${this.baseUrl}overdue-darts/`);
  }

  createActivity(payload: PlannerActivityPayload): Observable<PlannerActivityDto> {
    return this.http.post<PlannerActivityDto>(this.baseUrl, payload);
  }

  updateActivity(id: number | string, payload: PlannerActivityPayload): Observable<PlannerActivityDto> {
    return this.http.put<PlannerActivityDto>(`${this.baseUrl}${id}/`, payload);
  }

  deleteActivity(id: number | string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}${id}/`);
  }

  private toParams(query: PlannerActivityQuery): HttpParams {
    let params = new HttpParams();

    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === '') {
        continue;
      }

      params = params.set(key, String(value));
    }

    return params;
  }
}
