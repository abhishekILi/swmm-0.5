import { inject, Injectable } from "@angular/core";
import { AppService } from "../../../../../Core/services/app/app.service";
import { LandingPageService } from "../../../../landing/landing-page.service";

@Injectable({ providedIn: "root" })
export class SfdReferencesApiService {
  private readonly appService = inject(AppService);
  private readonly landing = inject(LandingPageService);

  /** Streams a sync endpoint's progress chunks, invoking `onChunk` as each one arrives. */
  async streamSync(endpoint: string, onChunk: (chunk: string) => void): Promise<void> {
    const token = this.landing.accessToken();
    const response = await fetch(`${this.appService.baseUrl}api/v1/sfd/${endpoint}`, {
      method: "GET",
      credentials: "include",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!response.ok || !response.body) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      onChunk(decoder.decode(value, { stream: true }));
    }
  }
}
