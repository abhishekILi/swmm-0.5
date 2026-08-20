import {
  HttpErrorResponse,
  HttpHandlerFn,
  HttpInterceptorFn,
  HttpRequest,
  HttpResponse,
} from '@angular/common/http';
import { inject, Injector } from '@angular/core';
import { catchError, finalize, from, switchMap, tap, throwError } from 'rxjs';
import { Auth } from '../../services/auth/auth';
import { AppService } from '../app/app.service';
import { NotificationService } from '../../services/notification/notification.service';
import {
  getErrorMessage,
  getSuccessMessage,
  isAuthUrl,
  MUTATION_METHODS,
  SKIP_LOADER,
  SKIP_TOAST,
} from '../../services/common/http-feedback';
import { LandingPageService } from '../../../Modules/landing/landing-page.service';
import { environment } from '../../../../environments/environment';

const shouldSkipRefresh = (url: string): boolean => {
  return (
    url.includes('/landing') ||
    url.includes('/api/v1/user/token/') ||
    url.includes('/api/v1/user/token/access/') ||
    url.includes('/api/v1/user/logout/')
  );
};

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
) => {
  const landingService = inject(LandingPageService);
  const user = localStorage.getItem('user');
  const token = landingService.accessToken();
  const token2 = user ? JSON.parse(user)?.access : null;

  const isPhase2Api = req.url.includes(environment.API_URL);
  const bearerToken = isPhase2Api ? token2 : token;

  req = req.clone({
    withCredentials: true,
    setHeaders: bearerToken
      ? {
        Authorization: `Bearer ${bearerToken}`,
      }
      : {},
  });

  return next(req);
};
export const loaderInterceptor: HttpInterceptorFn = (req, next) => {
  const isMutation = MUTATION_METHODS.has(req.method.toUpperCase());
  if (!isMutation || req.context.get(SKIP_LOADER)) {
    return next(req);
  }
  const appService = inject(AppService);
  appService.showLoader();
  return next(req).pipe(
    finalize(() => {
      appService.hideLoader();
    }),
  );
};

export const feedbackInterceptor: HttpInterceptorFn = (req, next) => {
  const isMutation = MUTATION_METHODS.has(req.method.toUpperCase());
  if (!isMutation || req.context.get(SKIP_TOAST) || isAuthUrl(req.url)) {
    return next(req);
  }
  const notify = inject(NotificationService);
  return next(req).pipe(
    tap((event) => {
      if (event instanceof HttpResponse) {
        notify.success(getSuccessMessage(event.body) ?? 'Operation completed successfully.');
      }
    }),
    catchError((error: HttpErrorResponse) => {
      notify.error(getErrorMessage(error));
      return throwError(() => error);
    }),
  );
};

export const refreshTokenInterceptor: HttpInterceptorFn = (req, next) => {
  const injector = inject(Injector);
  const landingService = inject(LandingPageService);

  if (shouldSkipRefresh(req.url)) {
    return next(req);
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401) {
        return throwError(() => error);
      }

      return from(injector.get(Auth).refreshAccessToken()).pipe(
        switchMap((success) => {
          if (!success) {
            return throwError(() => error);
          }

          const newRequest = req.clone({
            withCredentials: true,
            setHeaders: {
              Authorization: `Bearer ${landingService.accessToken()}`,
            },
          });

          return next(newRequest);
        }),
      );
    }),
  );
};
