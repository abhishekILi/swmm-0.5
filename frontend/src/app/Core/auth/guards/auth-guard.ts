import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Auth } from '../../../Core/services/auth/auth';

export const authGuard: CanActivateFn = async () => {
  const router = inject(Router);
  const authService = inject(Auth);

  if (authService.hasAccessToken()) {
    return true;
  }

  return (await authService.initializeSession())
    ? true
    : router.createUrlTree(['/landing']);
};

export const guestGuard: CanActivateFn = async () => {
  const router = inject(Router);
  const authService = inject(Auth);

  if (authService.hasAccessToken() || (await authService.initializeSession())) {
    return router.createUrlTree(['/afterAuth/home']);
  }

  return true;
};
