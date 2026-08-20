import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Call } from '../network/call';
@Injectable({
  providedIn: 'root',
})
export class ShipConfig {
  private calls = inject(Call);

  // add sfd equipments for reference sfd

    async createEquipment(payload: Record<string, unknown>) {
      try {
        const res = await firstValueFrom(
          this.calls.createSfdEquipment(payload)
        );
        return res;
      } catch (error: unknown) {
        const err = error as { error?: { message?: string }; message?: string };
        const errorMessage =
          err?.error?.message ||
          err?.message ||
          'Something went wrong';
        console.error(errorMessage);
        throw error;
      }
    }

}
