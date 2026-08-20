import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../api.service';

@Injectable({ providedIn: 'root' })
export class MasterService {
  private readonly api = inject(ApiService);

  getClasses(): Observable<any> { return this.api.get('master/ship-classes/'); }
  getLocations(): Observable<any> { return this.api.get('master/locations/'); }
  getEquipment(): Observable<any> { return this.api.get('master/equipments/'); }
  getCompartments(): Observable<any> { return this.api.get('master/compartments/'); }
  getVessels(): Observable<any> { return this.api.get('master/ships/'); }
  getShipsByClass(id: string | number): Observable<any> {
    return this.api.get(`master/ships/?shipClass=${id}`);
  }
  getDropDownOptionsByDropDownKey(key: string): Observable<any> {
    return this.api.get(`master/lookups/?dropdown__key=${encodeURIComponent(key)}`);
  }
}
