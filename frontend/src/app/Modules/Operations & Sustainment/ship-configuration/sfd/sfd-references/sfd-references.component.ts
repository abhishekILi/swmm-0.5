import { ChangeDetectionStrategy, Component, computed, inject, signal } from "@angular/core";
import { SfdReferencesApiService } from "../services/sfd-references-api.service";
import { LogLine, LogTone, SyncCardConfig, SyncKey } from "./sfd-references.models";

const SYNC_CARDS: SyncCardConfig[] = [
  {
    key: "cmms",
    step: 1,
    title: "CMMS SFD Sync",
    color: "#1671D9",
    endpoint: "fetch-from-cmms/",
  },
  {
    key: "maintop",
    step: 2,
    title: "CMMS MAINTOPS Sync",
    color: "#1E9E5A",
    endpoint: "maintop-sync/",
  },
  {
    key: "routine",
    step: 3,
    title: "CMMS Nomenclature wise Routines Sync",
    color: "#17A2B8",
    endpoint: "routine-sync/",
  },
  {
    key: "missingRoutine",
    step: 4,
    title: "Create Nomenclature wise Missing Routines",
    color: "#F0A500",
    endpoint: "missing-routine-sync/",
  },
  {
    key: "defect",
    step: 5,
    title: "Fetch & Save CMMS Open Defects",
    color: "#D9364A",
    endpoint: "open-defects-sync/",
  },
];

/** Substring → log-line classification, ported from the source Django template's inline
 *  `runSync()` script (see SFD/templates/SFD/sfd_import_master.html). */
function classify(chunk: string): LogTone {
  if (/INSERTED|Completed|\[OK\]|\[NEW\]/i.test(chunk)) return "success";
  if (/UPDATED|\[EXISTING\]/i.test(chunk)) return "update";
  if (/\[SKIPPED\]/i.test(chunk)) return "skipped";
  if (/Error/i.test(chunk)) return "error";
  return "info";
}

function stripHtml(chunk: string): string {
  // Bounded quantifier (real tags are nowhere near this long) so the pattern can't be
  // flagged/abused as unbounded backtracking — sonarjs/super-linear-regex.
  return chunk.replace(/<br[\s/]*>/gi, " ").replace(/<[^>]{0,1000}>/g, "").trim();
}

@Component({
  selector: "app-sfd-references",
  standalone: true,
  imports: [],
  templateUrl: "./sfd-references.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrls: ["./sfd-references.component.css"],
})
export class SfdReferencesComponent {
  private readonly api = inject(SfdReferencesApiService);

  readonly syncCards = SYNC_CARDS;
  readonly runningKey = signal<SyncKey | null>(null);
  readonly completedKeys = signal<ReadonlySet<SyncKey>>(new Set());
  readonly progress = signal(0);
  readonly currentAction = signal("Ready to synchronize Ship data...");
  readonly itemCount = signal(0);
  readonly logLines = signal<LogLine[]>([]);

  private totalItems = 0;

  readonly isRunning = computed(() => this.runningKey() !== null);

  isCardRunning(key: SyncKey): boolean {
    return this.runningKey() === key;
  }

  isCardCompleted(key: SyncKey): boolean {
    return this.completedKeys().has(key);
  }

  async runSync(card: SyncCardConfig): Promise<void> {
    if (this.isRunning() || !card.endpoint) return;
    const endpoint = card.endpoint;

    this.runningKey.set(card.key);
    this.progress.set(0);
    this.itemCount.set(0);
    this.totalItems = 0;
    this.logLines.set([]);
    this.currentAction.set(`Starting ${card.title}...`);
    this.appendLog(`[SYSTEM] Initializing sync from /api/v1/sfd/${endpoint}...`, "info");

    try {
      await this.api.streamSync(endpoint, (chunk) => this.handleChunk(chunk));
      this.currentAction.set("Synchronization Complete");
      this.progress.set(100);
    } catch (error) {
      this.appendLog(`[FATAL] Connection error: ${error instanceof Error ? error.message : String(error)}`, "error");
    } finally {
      this.runningKey.set(null);
      this.completedKeys.update((keys) => new Set(keys).add(card.key));
    }
  }

  private handleChunk(chunk: string): void {
    const clean = stripHtml(chunk);
    if (!clean) return;

    const countMatch = /(?:Found|Fetched)\D+(\d+)/i.exec(clean);
    if (countMatch) {
      this.totalItems = Number(countMatch[1]);
    }

    this.appendLog(clean, classify(chunk));

    const count = this.itemCount() + 1;
    this.itemCount.set(count);

    const percent = this.totalItems > 0
      ? Math.min(99, Math.round((count / this.totalItems) * 100))
      : Math.min(99, Math.round(count * 0.5));
    this.progress.set(percent);
    this.currentAction.set(
      this.totalItems > 0 ? `Processing records (${count}/${this.totalItems})` : `Processing records (${count})`,
    );
  }

  private appendLog(text: string, tone: LogTone): void {
    this.logLines.update((lines) => [...lines, { text, tone }]);
  }
}
