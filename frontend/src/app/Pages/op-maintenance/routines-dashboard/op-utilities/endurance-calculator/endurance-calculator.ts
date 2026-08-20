import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { IconComponent } from '../../../../../shared/components/icon/icon.component';

// Mirrors Django's ops_maintainance/endurance_calculator.html exactly — the source page
// itself is an unimplemented "Development in Progress" stub, not a real calculator.
@Component({
  selector: 'app-endurance-calculator',
  standalone: true,
  imports: [CommonModule, IconComponent],
  templateUrl: './endurance-calculator.html',
  styleUrl: './endurance-calculator.css',
})
export class EnduranceCalculator {}
