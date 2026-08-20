import { Component, CUSTOM_ELEMENTS_SCHEMA, ElementRef, EventEmitter, HostListener, inject, Input, Output, ChangeDetectionStrategy, signal } from '@angular/core';

import { Router } from '@angular/router';
import { BaseModalComponent } from '../../../shared/components/modal/base-modal.component';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Auth } from '../../services/auth/auth';
import { AppService } from '../../services/app/app.service';
import { NotificationService } from '../../services/notification/notification.service';
import { ThemeService } from '../../services/theme/theme.service';
import { IconComponent } from '../../../shared/components/icon/icon.component';
import { LandingPageService } from '../../../Modules/landing/landing-page.service';

@Component({
  selector: 'app-login-modal',
  standalone: true,
  imports: [ReactiveFormsModule, IconComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './login-modal.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrls: ['./login-modal.component.scss']
})
export class LoginModalComponent extends BaseModalComponent {
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(Auth);
  private readonly appService = inject(AppService);
  private readonly notification = inject(NotificationService);
  private readonly elRef = inject(ElementRef);
  private readonly themeService = inject(ThemeService);
  private readonly landingService = inject(LandingPageService);

  readonly showPassword = signal(false);
  readonly showForgotInfo = signal(false);
  loginForm: FormGroup;

  @Input() shipData?: { name?: string;[key: string]: unknown };
  @Output() switchToSignup = new EventEmitter<void>();

  constructor() {
    super();
    this.loginForm = this.fb.nonNullable.group({
      username: ['', [Validators.required, Validators.minLength(3)]],
      password: ['', [Validators.required, Validators.minLength(4)]]
    });
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (this.showForgotInfo() && !this.elRef.nativeElement.contains(event.target)) {
      this.showForgotInfo.set(false);
    }
  }

  get f() {
    return this.loginForm.controls;
  }


  async onLogin(): Promise<void> {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.appService.showLoader();
    try {
      const res = await this.authService.loginUser(this.loginForm.getRawValue());
      if (res.success) {
        // Force dark mode on login
        this.themeService.theme.set('dark');
        localStorage.setItem('swmm-theme', 'dark');

        const user = this.landingService.user();
        const isAdmin = user ? user['is_admin'] : false;
        const redirectPath = isAdmin ? 'afterAuth/administration' : 'afterAuth/home';
        this.router.navigate([redirectPath]);
        this.onClose();
      } else {
        this.notification.error(res.message);
      }
    } catch (error) {
      console.error('Login failed', error);
      this.notification.error('Something went wrong while logging in. Please try again.');
    } finally {
      await this.appService.hideLoader();
    }
  }

  onSwitchToSignup(): void {
    this.switchToSignup.emit();
  }
}
