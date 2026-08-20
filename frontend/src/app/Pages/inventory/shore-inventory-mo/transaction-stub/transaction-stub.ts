import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from "@angular/core";
import { ActivatedRoute } from "@angular/router";
import { FormControl, FormGroup, ReactiveFormsModule } from "@angular/forms";
import { ColDef, RowData } from "ag-grid-community";
import { DataGrid } from "../../../../shared/components/data-grid/data-grid";
import { DynamicField, DynamicFieldSpec } from "../../../../shared/components/dynamic-field/dynamic-field";
import { HelpGuidance } from "../../shared/components/help-guidance/help-guidance";
import { NotificationService } from "../../../../Core/services/notification/notification.service";

export interface TransactionStubConfig {
  title: string;
  fields: DynamicFieldSpec[];
  columns: ColDef[];
  rows: RowData[];
  primaryButtonLabel?: string;
}

/**
 * Generic filter-form + read-only-table page used for the "As is Transaction"
 * references (Create Cart, Demand Action, Issue Authorise, ...). The Django
 * originals are themselves static/demo pages (hardcoded sample rows, no real
 * backend wiring) — this renders the same shape from a per-route config
 * instead of eight near-identical hand-written components.
 */
@Component({
  selector: "app-mo-transaction-stub",
  standalone: true,
  imports: [ReactiveFormsModule, DynamicField, DataGrid, HelpGuidance],
  templateUrl: "./transaction-stub.html",
  styleUrl: "./transaction-stub.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TransactionStub implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);

  title = "";
  fields: DynamicFieldSpec[] = [];
  columnDefs: ColDef[] = [];
  primaryButtonLabel: string | null = null;
  readonly rows = signal<RowData[]>([]);
  form = new FormGroup({});

  ngOnInit(): void {
    const data = this.route.snapshot.data as { config: TransactionStubConfig };
    this.title = data.config.title;
    this.fields = data.config.fields;
    this.columnDefs = data.config.columns;
    this.primaryButtonLabel = data.config.primaryButtonLabel ?? null;
    this.rows.set(data.config.rows);
    this.form = new FormGroup(
      Object.fromEntries(this.fields.map((f) => [f.key, new FormControl("")])),
    );
  }

  getControl(key: string): FormControl {
    return this.form.get(key) as FormControl;
  }

  clear(): void {
    this.form.reset();
  }

  runPrimaryAction(): void {
    if (this.primaryButtonLabel) {
      this.notifications.success(`${this.primaryButtonLabel} — done.`);
    }
  }
}
