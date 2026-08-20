# HITU Report System Guide

Ye document HITU static forms ke reports ke liye hai. Dynamic report files ko modify nahi karna hai. HITU report ke liye separate report engine banaya gaya hai.

## Current Status

HITU report engine ready hai.

Current coverage:

- `IUWHI` ka exact custom report builder available hai.
- Baaki HITU forms universal report builder se covered hain.
- Report print, version save/select, workflow history, QR signature aur final observation supported hai.
- Dynamic report files untouched hain.

## Main Files

HITU report code yahan hai:

```text
src/app/pages/Modules/hitu-module/hitu-reports/
```

Important files:

```text
hitu-report-host.component.ts      Report page / UI / print / versions / workflow
hitu-report-data.service.ts        API se saved form data load karta hai
hitu-report.registry.ts            Form name, title aur exact builder registry
hitu-report.helpers.ts             Universal builder aur helper functions
hitu-report.types.ts               Common report types
builders/iuwhi.report.ts           IUWHI exact custom builder
```

## Report Route

Route already add hai:

```ts
{
  path: 'report/:formName',
  loadComponent: () =>
    import('./hitu-reports/hitu-report-host.component').then(
      (m) => m.HituReportHostComponent,
    ),
}
```

Test URL format:

```text
/hitu/report/<formName>?trial=<trial_uuid>&type=trials
```

Examples:

```text
/hitu/report/iuwhi?trial=<trial_uuid>&type=trials
/hitu/report/vkd-ras-winch?trial=<trial_uuid>&type=trials
/hitu/report/boat-trials-data?trial=<trial_uuid>&type=trials
/hitu/report/water-tight-door?trial=<trial_uuid>&type=trials
```

## Data Flow

Report data same API flow se aata hai jo dynamic report use karta hai.

Flow:

```text
URL formName + trial id
FormApiService.setCurrentForm()
FormApiService.getForm()
FormApiService.getFormByEquipment()
HITU builder creates ReportSection[]
DynamicMatrixReportComponent renders report tables
```

## Universal Builder Kahan Hai

Universal builder function:

```text
src/app/pages/Modules/hitu-module/hitu-reports/hitu-report.helpers.ts
```

Function name:

```ts
genericPayloadReport(formName, payload)
```

Ye automatically payload se report banata hai:

- Basic information fields
- `basicDetails`
- `tableData`
- status / remarks / observation / details / files grouped rows
- arrays
- nested objects
- additional fields

Registry me fallback yahan call hota hai:

```text
src/app/pages/Modules/hitu-module/hitu-reports/hitu-report.registry.ts
```

Code:

```ts
export function buildHituReport(context: HituReportBuildContext) {
  const normalizedFormName = normalizeFormName(context.formName);
  const builder = HITU_REPORT_REGISTRY[normalizedFormName];
  if (builder) return builder(context);
  return genericPayloadReport(getHituReportTitle(context.formName), context.payload);
}
```

Meaning:

- Exact builder mila to exact builder chalega.
- Exact builder nahi mila to universal builder chalega.

## Exact Builder Kahan Hai

Currently exact builder:

```text
src/app/pages/Modules/hitu-module/hitu-reports/builders/iuwhi.report.ts
```

Registry entry:

```ts
export const HITU_REPORT_REGISTRY: Record<string, HituReportBuilder> = {
  iuwhi: buildIuwhiReport,
};
```

## New Form Add Karna Ho To Kya Karna Hai

New form add karne ke 2 cases hain.

## Case 1: Sirf Universal Report Chahiye

Agar exact layout nahi chahiye aur payload based readable report enough hai, to sirf title add karo.

File:

```text
src/app/pages/Modules/hitu-module/hitu-reports/hitu-report.registry.ts
```

`HITU_REPORT_TITLES` me entry add karo:

```ts
export const HITU_REPORT_TITLES: Record<string, string> = {
  'new-form-route': 'New Form Report Title',
};
```

Then report URL:

```text
/hitu/report/new-form-route?trial=<trial_uuid>&type=trials
```

Universal builder automatically payload render karega.

## Case 2: Exact Custom Report Chahiye

Agar form ka exact table structure, custom sections aur labels chahiye to custom builder banana hoga.

### Step 1: Form Files Read Karo

Read these files:

```text
src/app/pages/Modules/hitu-module/HituForms/<form-folder>/<form>.ts
src/app/pages/Modules/hitu-module/HituForms/<form-folder>/<form>.html
```

`.ts` file me check karo:

- `buildForm()`
- `buildPayload()`
- `handleSave()`
- saved payload flat hai ya nested
- form control names

`.html` file me check karo:

- report title
- header fields
- table columns
- parameter rows
- observation fields
- remarks fields
- file upload fields

### Step 2: Builder File Banao

Create file:

```text
src/app/pages/Modules/hitu-module/hitu-reports/builders/<form-name>.report.ts
```

Example:

```text
src/app/pages/Modules/hitu-module/hitu-reports/builders/vkd-ras-winch.report.ts
```

### Step 3: Builder Code Likho

Example:

```ts
import { ReportSection } from '../../../../../angulerFromconverting/dynamic-form-report-builder.service';
import { fieldsSection, tableSection } from '../hitu-report.helpers';
import { HituReportBuildContext } from '../hitu-report.types';

export function buildVkdRasWinchReport(context: HituReportBuildContext): ReportSection[] {
  const payload = context.payload || {};

  return [
    fieldsSection('basic_information', 'Basic Information', payload, [
      ['Ship', 'ship'],
      ['Date of Conduct Trial', 'date_of_conduct_trail'],
      ['Place of Conduct Trial', 'place_of_conduct_trail'],
      ['Occasion', 'occasion_of_conduct_trail'],
      ['Authority', 'authority'],
    ]),

    tableSection('checks', 'Checks / Observations', payload, ['Ser', 'Parameter', 'Observation', 'Remarks'], [
      ['1', 'Type', '${type}'],
      ['2', 'Make', '${make}'],
      ['3', 'Gear Box', '${gear_box_obs}', '${gear_box_remarks}'],
    ]),
  ];
}
```

### Step 4: Registry Me Import Add Karo

File:

```text
src/app/pages/Modules/hitu-module/hitu-reports/hitu-report.registry.ts
```

Add import:

```ts
import { buildVkdRasWinchReport } from './builders/vkd-ras-winch.report';
```

Add title:

```ts
export const HITU_REPORT_TITLES: Record<string, string> = {
  'vkd-ras-winch': 'VKD RAS Winch',
};
```

Add builder registry:

```ts
export const HITU_REPORT_REGISTRY: Record<string, HituReportBuilder> = {
  'vkd-ras-winch': buildVkdRasWinchReport,
};
```

### Step 5: Test URL

```text
/hitu/report/vkd-ras-winch?trial=<trial_uuid>&type=trials
```

### Step 6: Build Verify

Run:

```bash
npm run build
```

Build pass hona chahiye.

## Payload Mapping Rules

Flat payload example:

```ts
payload.ship
payload.date_of_conduct_trail
payload.mlab_report_status
```

Use path:

```ts
['Ship', 'ship']
['Date', 'date_of_conduct_trail']
['MLAB Status', 'mlab_report_status']
```

Nested payload example:

```ts
payload.basicDetails.ship
payload.tableData.type_of_capstan
payload.tableData.gear_box_remarks
```

Use path:

```ts
['Ship', 'basicDetails.ship']
['Type of Capstan', 'tableData.type_of_capstan']
['Gear Box Remarks', 'tableData.gear_box_remarks']
```

Table interpolation example:

```ts
['1', 'Gear Box', '${tableData.gear_box_obs}', '${tableData.gear_box_remarks}']
```

## Important Helpers

Available in `hitu-report.helpers.ts`:

```ts
fieldsSection(id, title, payload, fields)
tableSection(id, title, payload, headers, rows)
getValue(payload, path)
displayValue(value)
genericPayloadReport(formName, payload)
toTitle(value)
```

## Existing Supported Form Titles

Titles are registered in:

```text
hitu-report.registry.ts
```

Examples:

```ts
'iuwhi': 'IUWHI'
'puwhi': 'PUWHI'
'vkd-ras-winch': 'VKD RAS Winch'
'boat-trials-data': 'Boat Trials Data'
'water-tight-door': 'Water Tight Door'
'grease-separator': 'Grease Separator'
```

If title missing hai, report still generate hoga, but title route name se banega.

## Verification Checklist

Har new form ke baad ye check karo:

- Report URL open ho raha hai.
- Header title correct hai.
- Saved API data visible hai.
- Basic fields visible hain.
- Table rows expected order me hain.
- SAT / UNSAT / remarks visible hain.
- File fields readable hain.
- Workflow history visible hai.
- Final observation visible hai.
- Print button works.
- Version create/select works.
- `npm run build` pass hai.

## When To Use Universal Builder

Universal builder use karo jab:

- form ka payload already clean hai
- exact old HTML layout required nahi hai
- quick report chahiye
- all saved values visible hone chahiye

## When To Use Exact Builder

Exact builder use karo jab:

- report format same form/table layout jaisa chahiye
- row order important hai
- table headings custom chahiye
- fields ko merge/group karna hai
- payload nested/complex hai
- report official print format me chahiye

## Current Recommendation

All forms ke liye universal report already available hai. Important forms ke liye gradually exact builders add karo.

Recommended exact builder priority:

```text
1. vkd-ras-winch
2. vkd-fire-screen-driver
3. vkd-lifting-transporting-device
4. boat-trials-data
5. water-tight-door
6. water-tight-hatches
7. puwhi
8. fuwhi
9. tow-worthiness-ship
10. boat-davit-crane
```

## Do Not Modify

HITU report ke liye ye dynamic report files modify nahi karni hain:

```text
src/app/angulerFromconverting/dynamic-form-report-host.component.ts
src/app/angulerFromconverting/dynamic-form-report-builder.service.ts
src/app/angulerFromconverting/dynamic-form-schema.service.ts
```

Reusable components/services use karna allowed hai:

```text
FormApiService
DynamicMatrixReportComponent
FinalObservationReportComponent
QRCodeComponent
NgxPrintDirective
ApiService
```
