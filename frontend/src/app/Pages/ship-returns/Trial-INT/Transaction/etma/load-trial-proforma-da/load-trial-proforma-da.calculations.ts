/** Row indices in {@link STEADY_STATE_LOAD_ROWS} for speed-control calculations. */
export const STEADY_STATE_ROW_INDEX = {
  FULL_LOAD: 0,
  NO_LOAD: 4,
  GOVERNOR_DROOP: 9,
} as const;

export function parseFrequency(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Nominal frequency = (No load frequency + Full load frequency) / 2 */
export function calculateNominalFrequency(
  noLoadFrequency: number | null,
  fullLoadFrequency: number | null,
): number | null {
  if (noLoadFrequency === null || fullLoadFrequency === null) return null;
  return (noLoadFrequency + fullLoadFrequency) / 2;
}

/** Governor Droop (%) = (No load frequency - Full load frequency) * 100 / Nominal frequency */
export function calculateGovernorDroop(
  noLoadFrequency: number | null,
  fullLoadFrequency: number | null,
  nominalFrequency: number | null,
): number | null {
  if (
    noLoadFrequency === null ||
    fullLoadFrequency === null ||
    nominalFrequency === null ||
    nominalFrequency === 0
  ) {
    return null;
  }
  return ((noLoadFrequency - fullLoadFrequency) * 100) / nominalFrequency;
}

/** Frequency Modulation (%) = 100 x (Fmax - Fmin) / (2 x Fnominal) */
export function calculateFrequencyModulation(
  initialSpeedHz: number | null,
  finalSpeedHz: number | null,
  nominalFrequency: number | null,
): number | null {
  if (
    initialSpeedHz === null ||
    finalSpeedHz === null ||
    nominalFrequency === null ||
    nominalFrequency === 0
  ) {
    return null;
  }
  const fMax = Math.max(initialSpeedHz, finalSpeedHz);
  const fMin = Math.min(initialSpeedHz, finalSpeedHz);
  return (100 * (fMax - fMin)) / (2 * nominalFrequency);
}

export function roundFrequencyCalculation(value: number, decimals = 4): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

/** Permissible limit: less than ± 0.25% of rated frequency. */
export const FREQUENCY_MODULATION_SAT_LIMIT_PERCENT = 0.25;

export type SteadyStateStatus = 'Sat' | 'Unsat' | '';

/** Sat when frequency modulation is below the ± 0.25% limit; otherwise Unsat. */
export function evaluateFrequencyModulationStatus(
  modulationPercent: number | null,
): SteadyStateStatus {
  if (modulationPercent === null) return '';
  return modulationPercent < FREQUENCY_MODULATION_SAT_LIMIT_PERCENT ? 'Sat' : 'Unsat';
}

/**
 * Evaluates governor droop against the permissible limit shown for the
 * selected governor type. A null result means that this form does not define
 * an automatic limit for that type, so the user's status is left unchanged.
 */
export function evaluateGovernorDroopStatus(
  droopPercent: number | null,
  governorType: string,
): SteadyStateStatus | null {
  let minimum: number;
  let maximum: number;

  switch (governorType) {
    case 'Electronic Governor':
      minimum = 0.75;
      maximum = 1;
      break;
    case 'Mechanical Governor':
      minimum = 3.5;
      maximum = 4;
      break;
    case 'For Ship Build Class':
      minimum = 0;
      maximum = 3;
      break;
    default:
      return null;
  }

  if (droopPercent === null) return '';
  return droopPercent >= minimum && droopPercent <= maximum ? 'Sat' : 'Unsat';
}

/** % peak = |Initial frequency − Momentary frequency| × 100 / Nominal frequency */
export function calculatePeakPercent(
  initialSpeedHz: number | null,
  momentarySpeedHz: number | null,
  nominalFrequency: number | null,
): number | null {
  if (
    initialSpeedHz === null ||
    momentarySpeedHz === null ||
    nominalFrequency === null ||
    nominalFrequency === 0
  ) {
    return null;
  }
  return (Math.abs(initialSpeedHz - momentarySpeedHz) * 100) / nominalFrequency;
}

export function evaluatePeakStatus(
  peakObserved: number | null,
  peakPermissibleLimit: number | null,
): SteadyStateStatus {
  if (peakObserved === null || peakPermissibleLimit === null) return '';
  return peakObserved <= peakPermissibleLimit ? 'Sat' : 'Unsat';
}

/** Recovery tolerance around final speed for governor transient tests. */
export function governorRecoveryTolerancePercent(governorType: string): number | null {
  switch (governorType) {
    case 'Mechanical Governor':
      return 1;
    case 'Electronic Governor':
    case 'For Non-Weapon Platform':
    case 'For Ship Build Class':
      return 0.2;
    default:
      return null;
  }
}

/**
 * Phase-1-compatible recovered final-value boundary.
 *
 * When load increases the lower tolerance boundary is used; when load
 * decreases the upper tolerance boundary is used.
 */
export function calculateRecoveryFinalValue(
  finalSpeedHz: number | null,
  loadInitial: unknown,
  loadTo: unknown,
  tolerancePercent: number | null,
): number | null {
  const initialLoad = parseFrequency(loadInitial);
  const targetLoad = parseFrequency(loadTo);
  if (
    finalSpeedHz === null ||
    finalSpeedHz < 0 ||
    initialLoad === null ||
    targetLoad === null ||
    tolerancePercent === null ||
    tolerancePercent < 0 ||
    initialLoad === targetLoad
  ) {
    return null;
  }

  const direction = targetLoad > initialLoad ? -1 : 1;
  return finalSpeedHz * (1 + direction * tolerancePercent / 100);
}
/** Extracts seconds from labels such as "2 Sec" and "5 Sec". */
export function parseRecoveryLimitSeconds(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const match = String(value).match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

/**
 * A transient row is satisfactory only when every applicable acceptance
 * criterion passes: peak, recovery time and recovered final-value tolerance.
 */
export function evaluateTransientTestStatus(
  peakObserved: number | null,
  peakPermissibleLimit: number | null,
  recoveryObservedSeconds: number | null,
  recoveryPermissibleSeconds: number | null,
  finalSpeedHz: number | null,
  recoveryFinalValueHz: number | null,
  finalValueTolerancePercent: number | null,
): SteadyStateStatus {
  if (peakObserved === null || peakPermissibleLimit === null) return '';

  if (recoveryPermissibleSeconds !== null && recoveryObservedSeconds === null) return '';

  if (
    finalValueTolerancePercent !== null &&
    (finalSpeedHz === null || finalSpeedHz === 0 || recoveryFinalValueHz === null)
  ) {
    return '';
  }

  const peakPasses = peakObserved <= peakPermissibleLimit;
  const recoveryTimePasses =
    recoveryPermissibleSeconds === null ||
    (recoveryObservedSeconds !== null && recoveryObservedSeconds <= recoveryPermissibleSeconds);

  const finalValuePasses =
    finalValueTolerancePercent === null ||
    (finalSpeedHz !== null &&
      finalSpeedHz !== 0 &&
      recoveryFinalValueHz !== null &&
      (Math.abs(recoveryFinalValueHz - finalSpeedHz) * 100) / Math.abs(finalSpeedHz) <=
        finalValueTolerancePercent + Number.EPSILON * 100);

  return peakPasses && recoveryTimePasses && finalValuePasses ? 'Sat' : 'Unsat';
}

export function parsePercentLabel(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(String(value).replace('%', '').trim());
  return Number.isFinite(parsed) ? parsed : null;
}

/** Voltage modulation (%) = 100 x (Vmax - Vmin) / (2 x Vnominal) */
export function calculateVoltageModulation(
  voltsMax: number | null,
  voltsMin: number | null,
  nominalVoltage: number | null,
): number | null {
  if (voltsMax === null || voltsMin === null || nominalVoltage === null || nominalVoltage === 0) {
    return null;
  }
  return (100 * Math.abs(voltsMax - voltsMin)) / (2 * nominalVoltage);
}

export const VOLTAGE_MODULATION_SAT_LIMIT_PERCENT = 2;
