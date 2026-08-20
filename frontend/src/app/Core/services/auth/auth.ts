import { inject, Injectable } from "@angular/core";
import { HttpErrorResponse } from "@angular/common/http";
import { firstValueFrom } from "rxjs";
import { Router } from "@angular/router";
import { User } from "../user/user";
import { MasterDataService } from "../master/Master-data-service";
import { NotificationStore } from "../notification/notification-store";
import { LandingPageService } from "../../../Modules/landing/landing-page.service";
import { AppService } from "../app/app.service";
import { skipFeedback } from "../common/http-feedback";
import { Call } from "../../../services/network/call";

interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: number;
    username: string;
    is_active: boolean;
    is_admin: boolean;
    profile: Record<string, unknown>;
    capabilities: string[];
  };
}

export type LoginResult =
  | { success: true }
  | { success: false; message: string };

@Injectable({
  providedIn: "root",
})
export class Auth {
  private readonly landingService = inject(LandingPageService);
  private readonly router = inject(Router);
  private readonly userService = inject(User);
  private readonly notifications = inject(NotificationStore);
  readonly api = inject(AppService);
  readonly call = inject(Call)

  private refreshInFlight: Promise<boolean> | null = null;
  readonly masterData = inject(MasterDataService);

  logincall(cred: { username: string; password: string }) {
    const loginInfo = this.call.logincall({ loginname: cred.username, password: cred.password })
    console.log(loginInfo, "----------------------------------------------")

    return this.api.post<LoginResponse>("api/v1/user/token/", cred, {
      context: skipFeedback({ loader: true, toast: true }),
    });
  }

  refreshAccessTokenApi() {
    this.call.refreshAccessToken()
    const refreshToken = this.landingService.refreshToken();
    console.log("Using refresh token from memory:", refreshToken ? "✅ Present" : "❌ Missing");

    return this.api.post<{ access: string }>(
      "api/v1/user/token/access/",
      { refresh: refreshToken },
      {
        context: skipFeedback({ loader: true, toast: true }),
      },
    );
  }

  logoutcall() {

    const refreshToken = this.landingService.refreshToken();
    return this.api.post(
      "api/v1/user/logout/",
      { refresh: refreshToken },
      {
        context: skipFeedback({ loader: true, toast: true }),
      },
    );
  }

  async loginUser(cred: {
    username: string;
    password: string;
  }): Promise<LoginResult> {

    try {
      const res = await firstValueFrom(this.logincall(cred));
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", res.access);
      }
      this.landingService.accessToken.set(res.access);
      this.landingService.refreshToken.set(res.refresh);
      this.landingService.user.set(res.user);

      localStorage.setItem('access_token', res.access);
      localStorage.setItem('refresh_token', res.refresh);
      localStorage.setItem('user_data', JSON.stringify(res.user));

      console.log("✅ Session saved to localStorage");

      // Load master data but don't block login if it fails
      try {
        await this.masterData.load();
      } catch (error) {
        console.warn("Failed to load master data, but user is logged in", error);
      }
      return { success: true };
    } catch (error) {
      console.error("❌ Login failed", error);
      return {
        success: false,
        message: this.extractErrorMessage(error),
      };
    }
  }

  private extractErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const body = error.error as
        | { message?: string; detail?: string }
        | string
        | null;

      if (typeof body === "string" && body.trim()) {
        return body;
      }
      if (body && typeof body === "object") {
        if (body.message) return body.message;
        if (body.detail) return body.detail;
      }
      switch (error.status) {
        case 0:
          return 'Unable to reach the server. Please check your connection and try again.';

        case 400:
        case 401:
          return 'Invalid username or password.';

        default:
          return error.message || 'Login failed. Please try again.';
      }

    }
    return "Something went wrong. Please try again.";
  }

  async getuserDetails() {
    const user = await firstValueFrom(
      this.landingService.getLoggedInuserDetails(),
    );
    this.landingService.user.set(user);
  }

  hasAccessToken(): boolean {
    return !!this.landingService.accessToken();
  }

  isAuthenticated(): boolean {
    return this.hasAccessToken();
  }

  async initializeSession(): Promise<boolean> {
    // Check if user data is in localStorage
    const storedUser = localStorage.getItem('user_data');
    const storedAccessToken = localStorage.getItem('access_token');

    if (storedAccessToken && storedUser) {
      // Restore from localStorage
      this.landingService.accessToken.set(storedAccessToken);
      this.landingService.user.set(JSON.parse(storedUser));
      console.log("✅ Session restored from localStorage");
      try {
        await this.masterData.load();
      } catch (error) {
        console.warn("Failed to load master data, but session is restored", error);
      }
      return true;
    }

    // If no stored session, try to refresh
    const refreshed = await this.refreshAccessToken();
    if (refreshed) {
      try {
        await this.masterData.load();
      } catch (error) {
        console.warn("Failed to load master data, but session is restored", error);
      }
    }
    return refreshed;
  }

  async refreshAccessToken(): Promise<boolean> {
    if (this.refreshInFlight) {
      return this.refreshInFlight;
    }

    this.refreshInFlight = this.performRefresh();

    try {
      return await this.refreshInFlight;
    } finally {
      this.refreshInFlight = null;
    }
  }

  private async performRefresh(): Promise<boolean> {
    try {
      const refreshToken = this.landingService.refreshToken();
      console.log("🔄 Attempting refresh with token:", refreshToken ? "✅ Present" : "❌ MISSING!");

      const res = await firstValueFrom(this.refreshAccessTokenApi());
      console.log("✅ Refresh Success:", res);
      this.landingService.accessToken.set(res.access);
      return true;
    } catch (error) {
      if (this.landingService.user()) {
        console.error("Token refresh failed, logging out...", error);
        this.logout();
      } else {
        console.log("❌ Clearing session (no user)");
        this.clearClientSession();
      }
      return false;
    }
  }

  async logout() {
    try {
      await firstValueFrom(this.logoutcall());
    } catch (error) {
      console.error("Logout API failed, clearing session locally anyway", error);
    }
    this.clearClientSession();
    this.router.navigate(["landing"]);
  }

  private clearClientSession(): void {
    if (typeof window !== "undefined") {
      // localStorage.removeItem("access_token");
      // localStorage.removeItem("refresh_token");
      // localStorage.removeItem("user_data");
      localStorage.clear();
    }
    this.landingService.accessToken.set("");
    this.landingService.refreshToken.set("");
    this.landingService.user.set(null);

    this.userService.userDetails.set(null);
    this.userService.userTickets.set(null);
  }
}
