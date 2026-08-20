import { ChangeDetectionStrategy, Component, input, signal } from "@angular/core";
import { IconComponent } from "../../../../../shared/components/icon/icon.component";

@Component({
  selector: "app-obs-help-guidance",
  standalone: true,
  imports: [IconComponent],
  templateUrl: "./help-guidance.html",
  styleUrl: "./help-guidance.css",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HelpGuidance {
  /** Developer-authored guidance markup (not user input) — Angular sanitizes [innerHTML] by default. */
  readonly bodyHtml = input<string>("");
  readonly expanded = signal(false);

  toggle(): void {
    this.expanded.update((value) => !value);
  }
}
