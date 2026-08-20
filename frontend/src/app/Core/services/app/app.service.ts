  import { Injectable, signal, inject } from '@angular/core';
  import { HttpClient, HttpContext, HttpHeaders, HttpParams } from '@angular/common/http';
  import { Observable } from 'rxjs';
  import { environment } from '../../../../environments/environment';

  /** Query-string params accepted by Angular's `HttpClient` `params` option. */
  type HttpQueryParams =
    | HttpParams
    | Record<string, string | number | boolean | readonly (string | number | boolean)[]>;

  /** Options accepted by every {@link AppService} HTTP helper. */
  interface HttpRequestOptions {
    params?: HttpQueryParams;
    headers?: HttpHeaders | Record<string, string | string[]>;
    context?: HttpContext;
  }

  @Injectable({
    providedIn: 'root',
  })
  export class AppService {
    private readonly http = inject(HttpClient);

    baseUrl = environment.apiUrl;

    /** GET `baseUrl + url`. */
    get<T>(url: string, options?: HttpRequestOptions): Observable<T>;
    get<T>(url: string, options: HttpRequestOptions & { observe: 'response' }): Observable<import('@angular/common/http').HttpResponse<T>>;
    get<T>(url: string, options: (HttpRequestOptions & { observe?: 'response' }) = {}) {
      const { observe, ...rest } = options;
      return observe === 'response'
        ? this.http.get<T>(`${this.baseUrl}${url}`, { ...rest, observe: 'response' as const })
        : this.http.get<T>(`${this.baseUrl}${url}`, rest);
    }
    getBlob(url: string, options: HttpRequestOptions = {}): Observable<Blob> {
      return this.http.get(`${this.baseUrl}${url}`, { ...options, responseType: 'blob' });
    }

    /** POST `baseUrl + url`. */
    post<T = unknown>(url: string, payload: unknown, options?: HttpRequestOptions): Observable<T>;
    post<T = unknown>(url: string, payload: unknown, options: HttpRequestOptions & { observe: 'response' }): Observable<import('@angular/common/http').HttpResponse<T>>;
    post<T = unknown>(url: string, payload: unknown, options: (HttpRequestOptions & { observe?: 'response' }) = {}) {
      const { observe, ...rest } = options;
      return observe === 'response'
        ? this.http.post<T>(`${this.baseUrl}${url}`, payload, { ...rest, observe: 'response' as const })
        : this.http.post<T>(`${this.baseUrl}${url}`, payload, rest);
    }

    /** PUT `baseUrl + url`. */
    put<T = unknown>(url: string, payload: unknown, options?: HttpRequestOptions): Observable<T>;
    put<T = unknown>(url: string, payload: unknown, options: HttpRequestOptions & { observe: 'response' }): Observable<import('@angular/common/http').HttpResponse<T>>;
    put<T = unknown>(url: string, payload: unknown, options: (HttpRequestOptions & { observe?: 'response' }) = {}) {
      const { observe, ...rest } = options;
      return observe === 'response'
        ? this.http.put<T>(`${this.baseUrl}${url}`, payload, { ...rest, observe: 'response' as const })
        : this.http.put<T>(`${this.baseUrl}${url}`, payload, rest);
    }

    /** PATCH `baseUrl + url`. */
    patch<T = unknown>(url: string, payload: unknown, options?: HttpRequestOptions): Observable<T>;
    patch<T = unknown>(url: string, payload: unknown, options: HttpRequestOptions & { observe: 'response' }): Observable<import('@angular/common/http').HttpResponse<T>>;
    patch<T = unknown>(url: string, payload: unknown, options: (HttpRequestOptions & { observe?: 'response' }) = {}) {
      const { observe, ...rest } = options;
      return observe === 'response'
        ? this.http.patch<T>(`${this.baseUrl}${url}`, payload, { ...rest, observe: 'response' as const })
        : this.http.patch<T>(`${this.baseUrl}${url}`, payload, rest);
    }

    /** DELETE `baseUrl + url`. */
    delete<T = unknown>(url: string, options?: HttpRequestOptions): Observable<T>;
    delete<T = unknown>(url: string, options: HttpRequestOptions & { observe: 'response' }): Observable<import('@angular/common/http').HttpResponse<T>>;
    delete<T = unknown>(url: string, options: (HttpRequestOptions & { observe?: 'response' }) = {}) {
      const { observe, ...rest } = options;
      return observe === 'response'
        ? this.http.delete<T>(`${this.baseUrl}${url}`, { ...rest, observe: 'response' as const })
        : this.http.delete<T>(`${this.baseUrl}${url}`, rest);
    }

    loading = signal(false);
    private requestCount = 0;
    private startTime = 0;
    private readonly minDuration = 3000;

    showAlert = signal(false);
    alertTitle = signal('');
    alertMessage = signal('');

    showLoader() {
      if (this.requestCount === 0) {
        this.startTime = Date.now();
        this.loading.set(true);
      }

      this.requestCount++;
    }

    hideLoader(): Promise<void> {
      this.requestCount--;

      if (this.requestCount > 0) {
        return Promise.resolve();
      }

      this.requestCount = 0;

      const elapsed = Date.now() - this.startTime;
      const remaining = Math.max(0, this.minDuration - elapsed);

      return new Promise((resolve) => {
        setTimeout(() => {
          this.loading.set(false);
          resolve();
        }, remaining);
      });
    }

    private alertCallback: (() => void) | null = null;

    openAlert(title: string, message: string, callback?: () => void) {
      this.alertTitle.set(title);
      this.alertMessage.set(message);
      this.showAlert.set(true);
      this.alertCallback = callback || null;
    }

    closeAlert() {
      this.showAlert.set(false);
      if (this.alertCallback) {
        this.alertCallback();
        this.alertCallback = null;
      }
    }

  }
