import { Component, computed, DestroyRef, inject, input, OnInit, output, signal, effect } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Compartment, CreateCompartmentPayload } from '../sfd-config.models';
import { SfdConfigApiService } from '../../services/sfd-config-api.service';
import { firstValueFrom } from 'rxjs';
import { MasterDataService } from '../../../../../../Core/services/master/Master-data-service';
import { SelectInput } from '../../../../../../shared/components';
import { IconComponent } from '../../../../../../shared/components/icon/icon.component';
@Component({
  selector: 'app-compartment-from',
  imports: [ReactiveFormsModule, SelectInput, IconComponent],
  templateUrl: './compartment-form.html',
  styleUrl: './compartment-form.css',
})
export class CompartmentForm  implements OnInit {

  compartment = input<Compartment | null>(null);
  readonly isEditMode = computed(() => !!this.compartment());
  closed = output<void>();
  saved = output<void>();
  readonly sfdConfigApi = inject(SfdConfigApiService)
  readonly master = inject(MasterDataService)

  isLoading = signal<boolean>(false)

  upperDecks = this.master.upperDecks;
  locations = this.master.locations;
  lowerDecks = this.master.lowerDecks;

  readonly deckError = signal(false);

  ngOnInit(): void {
    console.log("compartment console", this.compartment())
    console.log("mode", this.isEditMode())
  }

  closeModal() {
    this.form.reset()
    this.closed.emit();
  }

  readonly fb = inject(FormBuilder);
  readonly destroyRef = inject(DestroyRef);

  readonly submittedSignal = signal(false);

  readonly form: FormGroup = this.fb.group({
    compartmentName: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9 ]+$/), Validators.minLength(2),
      Validators.maxLength(32)
      ]],
    mainDeck: [false],
    upperDeck: [''],
    lowerDeck: [''],
    frameFrom: ['',[ Validators.required, Validators.min(1)]],
    frameTo: ['',[ Validators.required, Validators.min(1)]],
    location: ['', Validators.required],
  });

  constructor() {
    this.listenDeckSelection();

    effect(() => {
      const compartment = this.compartment();

      if (compartment) {
        this.form.patchValue({
          id: compartment.id,
          compartmentName: compartment.name,
          mainDeck: compartment.main_deck,
          upperDeck: compartment.upper_deck,
          lowerDeck: compartment.lower_deck,
          frameFrom: compartment.frame_station_from,
          frameTo: compartment.frame_station_to,
          location: compartment.location_value || compartment.location,
        });
      } else {
        this.form.reset({
          compartmentName: '',
          mainDeck: false,
          upperDeck: '',
          lowerDeck: '',
          frameFrom: '',
          frameTo: '',
          location: '',
        });
      }
    });
  }



  private isDeckSelected(): boolean {
    const { mainDeck, upperDeck, lowerDeck } = this.form.getRawValue();
    return mainDeck || !!upperDeck || !!lowerDeck;
  }

  get f() {
    return this.form.controls;
  }

  private listenDeckSelection() {
    // Main Deck
    this.f['mainDeck'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((checked: boolean) => {
        if (!checked) return;

        this.form.patchValue(
          {
            upperDeck: '',
            lowerDeck: '',
          },
          { emitEvent: false }
        );
      });

    // Upper Deck
    this.f['upperDeck'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: string) => {
        if (!value) return;

        this.form.patchValue(
          {
            mainDeck: false,
            lowerDeck: '',
          },
          { emitEvent: false }
        );
      });

    // Lower Deck
    this.f['lowerDeck'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: string) => {
        if (!value) return;

        this.form.patchValue(
          {
            mainDeck: false,
            upperDeck: '',
          },
          { emitEvent: false }
        );
      });

    this.form.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (this.isDeckSelected()) {
          this.deckError.set(false);
        }
      });
  }



 async save() {
   const deckSelected = this.isDeckSelected();
   this.deckError.set(!deckSelected);

  //  if (!deckSelected) {
  //    return;
  //  }

  if (this.form.invalid || !deckSelected) {
    this.form.markAllAsTouched();
    return;
  }
   const raw = this.form.getRawValue();
   const payload: CreateCompartmentPayload = {
    name: raw.compartmentName,
    main_deck: raw.mainDeck,
    upper_deck: raw.upperDeck || null,
    lower_deck: raw.lowerDeck || null,
    frame_station_from: Number(raw.frameFrom),
    frame_station_to: Number(raw.frameTo),
    frame_station: raw.frame_station,
    location: raw.location,
    location_value: raw.location
  };

   try {
     this.isLoading.set(true)
     const compartment = this.compartment();
     const request = this.isEditMode() && compartment
       ? this.sfdConfigApi.updateCompartment(compartment.id, payload)
       : this.sfdConfigApi.addCompartment(payload);

     const response = await firstValueFrom(request);
       if (response.status === 201 || response.status === 200) {
         this.saved.emit();
         this.form.reset();
         this.closeModal();
       }
  } catch (error: unknown) {
    console.error(error);
   }
   finally {
     this.isLoading.set(false)
   }

  }

  showError(control: keyof typeof this.form.controls): boolean {
    const field = this.form.controls[control];

    return field.invalid && (field.touched || this.submittedSignal());
  }
}
