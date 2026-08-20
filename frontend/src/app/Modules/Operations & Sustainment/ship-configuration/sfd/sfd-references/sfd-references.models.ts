export type SyncKey =
  | "cmms"
  | "maintop"
  | "routine"
  | "missingRoutine"
  | "defect";

export type LogTone = "success" | "update" | "skipped" | "error" | "info";

export interface LogLine {
  text: string;
  tone: LogTone;
}

export interface SyncCardConfig {
  key: SyncKey;
  step: number;
  title: string;
  color: string;
  endpoint: string | null;
}
