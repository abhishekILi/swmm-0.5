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

export function roundFrequencyCalculation(value: number, decimals = 2): number {
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

/** Governor droop row: permissible range 2% to 4%. */
export function evaluateGovernorDroopStatus(droopPercent: number | null): SteadyStateStatus {
  if (droopPercent === null) return '';
  return droopPercent >= 2 && droopPercent <= 4 ? 'Sat' : 'Unsat';
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

export function evaluateRecoveryTimeStatus(
  observedSeconds: number | null,
  permissibleSeconds: number | null,
): SteadyStateStatus {
  if (observedSeconds === null || permissibleSeconds === null) return '';
  return observedSeconds <= permissibleSeconds ? 'Sat' : 'Unsat';
}

/** Combine peak and recovery checks for transient row remarks. */
export function evaluateTransientRowStatus(
  peakStatus: SteadyStateStatus,
  recoveryStatus: SteadyStateStatus,
): SteadyStateStatus {
  if (peakStatus === 'Unsat' || recoveryStatus === 'Unsat') return 'Unsat';
  if (peakStatus === 'Sat' || recoveryStatus === 'Sat') return 'Sat';
  return '';
}

export function parsePercentLabel(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const match = String(value).match(/[\d.]+/);
  if (!match) return null;
  const parsed = Number(match[0]);
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
  return (100 * (voltsMax - voltsMin)) / (2 * nominalVoltage);
}

export const VOLTAGE_MODULATION_SAT_LIMIT_PERCENT = 2;

/** Difference between max and min of three line voltages. */
export function calculateVoltageBalanceDifference(
  ry: number | null,
  yb: number | null,
  br: number | null,
): number | null {
  if (ry === null || yb === null || br === null) return null;
  return Math.max(ry, yb, br) - Math.min(ry, yb, br);
}

/** Permissible limit = 1% of average of three line voltages. */
export function calculateVoltageBalancePermissibleLimit(
  ry: number | null,
  yb: number | null,
  br: number | null,
): number | null {
  if (ry === null || yb === null || br === null) return null;
  return (ry + yb + br) / 3 / 100;
}

export function evaluateVoltageBalanceStatus(
  difference: number | null,
  permissibleLimit: number | null,
): SteadyStateStatus {
  if (difference === null || permissibleLimit === null) return '';
  return difference <= permissibleLimit ? 'Sat' : 'Unsat';
}

/** Permissible voltage range span = 5% of rated voltage. */
export function calculateVoltageRangePermissibleLimit(ratedVoltage: number | null): number | null {
  if (ratedVoltage === null || ratedVoltage === 0) return null;
  return ratedVoltage * 0.05;
}

export interface ParallelingSharingCalculated {
  combinedVal: number | null;
  proportionateA: number | null;
  proportionateB: number | null;
  difference: number | null;
  toleranceBand: number | null;
}

/** kW / kVAr sharing calculations for unattended paralleling trial rows. */
export function calculateParallelingSharing(
  loadPercent: number,
  ratedA: number | null,
  ratedB: number | null,
  machineA: number | null,
  machineB: number | null,
): ParallelingSharingCalculated {
  if (ratedA === null || ratedB === null) {
    return {
      combinedVal: null,
      proportionateA: null,
      proportionateB: null,
      difference: null,
      toleranceBand: null,
    };
  }

  const factor = loadPercent / 100;
  const combinedRated = ratedA + ratedB;
  const combinedVal = factor * combinedRated;
  const proportionateA = factor * ratedA;
  const proportionateB = factor * ratedB;
  const toleranceBand = 0.1 * ((ratedA + ratedB) / 2);

  let difference: number | null = null;
  if (machineA !== null && machineB !== null) {
    difference = Math.max(
      Math.abs(proportionateA - machineA),
      Math.abs(proportionateB - machineB),
    );
  }

  return { combinedVal, proportionateA, proportionateB, difference, toleranceBand };
}

export function evaluateParallelingSharingStatus(
  difference: number | null,
  toleranceBand: number | null,
): SteadyStateStatus {
  if (difference === null || toleranceBand === null) return '';
  return difference < toleranceBand ? 'Sat' : 'Unsat';
}
