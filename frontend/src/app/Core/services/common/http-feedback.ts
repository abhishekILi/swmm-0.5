import { HttpContext, HttpContextToken, HttpErrorResponse } from '@angular/common/http';
export const MUTATION_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
export const SKIP_LOADER = new HttpContextToken<boolean>(() => false);
export const SKIP_TOAST = new HttpContextToken<boolean>(() => false);

export function skipFeedback(skip: { loader?: boolean; toast?: boolean }): HttpContext {
  const context = new HttpContext();
  if (skip.loader) context.set(SKIP_LOADER, true);
  if (skip.toast) context.set(SKIP_TOAST, true);
  return context;
}

export function isAuthUrl(url: string): boolean {
  return url.includes('/user/token') || url.includes('/user/logout') || url.includes('/api/auth/token');
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function readStringField(source: unknown, ...keys: string[]): string | null {
  const record = asRecord(source);
  if (!record) return null;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) return value;
  }
  return null;
}

export function getSuccessMessage(body: unknown): string | null {
  if (typeof body === 'string') return body.trim() ? body : null;
  const record = asRecord(body);
  return (
    readStringField(record, 'message', 'detail') ??
    readStringField(record?.['data'], 'message', 'detail')
  );
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (typeof error.error === 'string' && error.error.trim()) return error.error;

    const record = asRecord(error.error);
    const fromBody =
      readStringField(record, 'message', 'detail') ??
      readStringField(record?.['data'], 'message', 'detail');
    if (fromBody) return fromBody;

    switch (error.status) {
      case 0:
        return 'Unable to reach the server. Please check your connection and try again.';

      case 401:
        return 'Your session has expired. Please log in again.';

      case 403:
        return 'You do not have permission to perform this action.';

      default:
        return error.message || 'Something went wrong. Please try again.';
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return 'Something went wrong. Please try again.';
}
