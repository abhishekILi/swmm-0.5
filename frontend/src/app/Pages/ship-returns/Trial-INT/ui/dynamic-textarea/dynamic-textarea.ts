import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { FormGroup, FormBuilder, FormArray, FormsModule, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-dynamic-textarea',
  standalone: true,
  imports:[CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './dynamic-textarea.html',
  styleUrl: './dynamic-textarea.css',
})
export class DynamicTextarea {

  @Input() form!: FormGroup;
  @Input() controlName!: string;
  @Input() placeholder: string = 'Enter details';

  constructor(private fb: FormBuilder) {}



  get items(): FormArray {
  return (this.form.get(this.controlName) as FormArray) || this.fb.array([]);
}
  addItem() {
    this.items.push(this.fb.control(''));
  }

  removeItem(index: number) {
    this.items.removeAt(index);
  }
}
