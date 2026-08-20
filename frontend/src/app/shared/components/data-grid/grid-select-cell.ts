import { Component, ChangeDetectionStrategy } from "@angular/core";
import { ICellRendererAngularComp } from "ag-grid-angular";
import { ICellRendererParams, RowData } from "ag-grid-community";

import { FormsModule } from "@angular/forms";

interface SelectOption { label: string; value: unknown; }

export interface GridSelectParams extends ICellRendererParams {
    getOptions: () => SelectOption[];
    onValueChange?: (row: RowData, field: string, newValue: unknown) => void;
}

@Component({
    selector: "app-grid-select-cell",
    standalone: true,
    imports: [FormsModule],
    styles: [`
        :host {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            width: 100%;
        }

        .select-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            height: 100%;
        }

        .grid-inline-select {
            width: 100%;
            min-width: 180px;
            height: 32px;
            padding: 0 10px;

            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;

            background: #4a4a4a;
            color: #fff;

            text-align: center;
            text-align-last: center;

            outline: none;
            cursor: pointer;
        }

        .grid-inline-select option {

            background: #5a5a5a;
            color: #fff;
        }
    `],
    changeDetection: ChangeDetectionStrategy.OnPush,
    template: `
    <!-- <select class="grid-inline-select" [(ngModel)]="selectedValue" (ngModelChange)="onChange($event)"   style="background-color: rgba(255, 255, 255, 0.10)">
      <option *ngFor="let opt of params.getOptions()" [ngValue]="opt.value">
        {{ opt.label }}
      </option>
    </select> -->

    <div class="select-wrapper">
        <select
            class="grid-inline-select"
            [(ngModel)]="selectedValue"
            (ngModelChange)="onChange($event)"
        >
            @for (opt of params.getOptions(); track $index) {
  <option [ngValue]="opt.value">
    {{ opt.label }}
  </option>
}
        </select>
    </div>
  `,
})
export class GridSelectCell implements ICellRendererAngularComp {
    params!: GridSelectParams;
    selectedValue: unknown;

    agInit(params: GridSelectParams): void {
        this.params = params;
        // auto-bind: pre-select whatever value came back from the API
        this.selectedValue = params.value;
    }

    refresh(params: GridSelectParams): boolean {
        this.params = params;
        this.selectedValue = params.value;
        return true;
    }

    onChange(newValue: unknown) {
        this.params.node.setDataValue(this.params.colDef!.field!, newValue);
        this.params.api?.refreshCells({
            rowNodes: [this.params.node],
            force: true,
        });
        this.params.onValueChange?.(this.params.data, this.params.colDef!.field!, newValue);
    }
}
