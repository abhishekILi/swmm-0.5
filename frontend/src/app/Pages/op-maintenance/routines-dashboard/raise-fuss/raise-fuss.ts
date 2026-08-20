import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { MasterCard } from '../../../refit-maintenance/master-card/master-card';
import { IconComponent } from '../../../../shared/components/icon/icon.component';
import { Router } from '@angular/router';
import { Call } from '../../../../services/network/call';

interface FussRaisedRow {
  id: number;
  subDept: string;
  equipmentNomenclature: string;
  routineName: string;
  status: string;
  previousRoutineDate: string;
}

interface FussRaisedRoutinesResponse {
  fuss_list: {
    id: number;
    department: string;
    equipment: string;
    routine_name: string;
    status: string;
    due_date: string;
  }[];
}

@Component({
  selector: 'app-raise-fuss',
  standalone: true,
  imports: [CommonModule, MasterCard, IconComponent],
  templateUrl: './raise-fuss.html',
  styleUrl: './raise-fuss.css',
})
export class RaiseFUSS implements OnInit {
  private router = inject(Router);
  private call = inject(Call);
  private cdr = inject(ChangeDetectorRef);

  maintopRoutines: FussRaisedRow[] = [];

  ngOnInit(): void {
    this.call.getFUSSRaisedRoutines().subscribe({
      next: (res: unknown) => {
        const data = res as FussRaisedRoutinesResponse;
        this.maintopRoutines = (data.fuss_list ?? []).map((item) => ({
          id: item.id,
          subDept: item.department ?? '',
          equipmentNomenclature: item.equipment ?? '',
          routineName: item.routine_name ?? '',
          status: item.status ?? '',
          previousRoutineDate: item.due_date ?? 'NA',
        }));
        this.cdr.detectChanges();
      },
      error: (err: unknown) => console.error('Failed to load raised FUSS routines', err),
    });
  }

  navigateTo(url: string) {
    this.router.navigateByUrl(url);
  }

  navigateToCloseRoutine(id: number): void {
    this.router.navigate(
      ['/afterAuth/op-maintenance/routine/close-routine'],
      { state: { routineId: id } },
    );
  }
}
