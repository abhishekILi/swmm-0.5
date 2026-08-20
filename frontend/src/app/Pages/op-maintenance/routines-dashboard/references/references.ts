import { Component} from "@angular/core";
import { ImportData } from "./import-data/import-data";
import { OneTimeRoutine } from "./one-time-routine/one-time-routine";
@Component({
  selector: "app-action-forms",
  imports: [ImportData, OneTimeRoutine],
  templateUrl: './references.html',
  styleUrl: './references.css',
})
export class References {
  activeTab: "import-data" | "one-time-routine"  = "import-data";






}
