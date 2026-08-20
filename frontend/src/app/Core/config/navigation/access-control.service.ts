import { Injectable, computed, inject } from "@angular/core";

import { User } from "../../../Core/services/user/user";
import { AccessControlled } from "./navigation.model";

@Injectable({
  providedIn: "root",
})
export class AccessControlService {
  readonly userStore = inject(User);

  readonly roles = computed<ReadonlySet<string>>(() => {
    const raw = this.userStore.userDetails()?.roles;
    return new Set(Array.isArray(raw) ? raw : []);
  });

  readonly rbacActive = computed<boolean>(() =>
    Array.isArray(this.userStore.userDetails()?.roles),
  );

  readonly isSuperUser = computed<boolean>(() => {
    const user = this.userStore.userDetails();
    return user?.is_staff === true || user?.is_superuser === true;
  });
  canAccess(rule?: AccessControlled | null): boolean {
    const required = rule?.roles;
    if (!required || required.length === 0) {
      return true;
    }
    if (!this.rbacActive() || this.isSuperUser()) {
      return true;
    }
    const granted = this.roles();
    return required.some((role) => granted.has(role));
  }

  hasRole(role: string): boolean {
    return this.isSuperUser() || this.roles().has(role);
  }
}
