import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { TeamMember, UserProfile, UserTicket } from './user.model';
import { LandingPageService } from '../../../Modules/landing/landing-page.service';
import { CommonApiService } from '../common/commonApiService';

const ERROR_MSG = 'Something went wrong';

@Injectable({
  providedIn: 'root',
})
export class User {
  private readonly commonApiService = inject(CommonApiService);
  private readonly landingService = inject(LandingPageService);

  readonly userDetails = signal<UserProfile | null>(null);
  readonly userTickets = signal<UserTicket[] | null>(null);
  readonly teamMembers = signal<TeamMember[] | null>(null);

  async getLoggedInUserDetails(): Promise<UserProfile> {
    try {
      const user = await firstValueFrom(this.landingService.getLoggedInuserDetails());
      this.userDetails.set(user);
      this.landingService.user.set(user);
      return user;
    } catch (error) {
      console.error(error, ERROR_MSG);
      throw error;
    }
  }

  async getUserTickets(): Promise<void> {
    try {
      const res = await firstValueFrom(this.commonApiService.getTickets());
      this.userTickets.set(res);
    } catch (error) {
      console.error(error, ERROR_MSG);
    }
  }

  async getTeamMembers(): Promise<void> {
    try {
      const res = await firstValueFrom(this.commonApiService.getTeamMembers());
      this.teamMembers.set(res);
    } catch (error) {
      console.error(error, ERROR_MSG);
    }
  }
}
