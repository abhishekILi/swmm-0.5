export type TankType = 'HF/HSB Fuel' | 'AVCAT' | 'Double Bottom' | 'Overhead' | 'Dirty/Waste';
export type OilType = 'Diesel' | 'AVCAT' | 'Lube Oil' | 'Waste Oil';

export interface TankRecord {
  id: number;
  tank_type: TankType;
  manual_name: string;
  location: string;
  oil_type: OilType;
  mm_measurement: number;
  volume: number;
  weight: number;
  reading_time: string;
  created_date: string;
}

// Dummy per-tank-type calibration factors — stand-in for the real mm→volume/weight lookup table.
export const TANK_TYPE_FACTORS: Record<TankType, { volumePerMm: number; density: number; capacity100: number; capacity95: number }> = {
  'HF/HSB Fuel': { volumePerMm: 0.42, density: 0.86, capacity100: 180, capacity95: 171 },
  AVCAT: { volumePerMm: 0.35, density: 0.8, capacity100: 120, capacity95: 114 },
  'Double Bottom': { volumePerMm: 0.5, density: 0.86, capacity100: 220, capacity95: 209 },
  Overhead: { volumePerMm: 0.28, density: 0.86, capacity100: 90, capacity95: 85.5 },
  'Dirty/Waste': { volumePerMm: 0.3, density: 0.92, capacity100: 60, capacity95: 57 },
};

export function computeVolumeAndWeight(tankType: TankType, mm: number): { volume: number; weight: number } {
  const factor = TANK_TYPE_FACTORS[tankType];
  const volume = Math.round(mm * factor.volumePerMm * 100) / 100;
  const weight = Math.round(volume * factor.density * 100) / 100;
  return { volume, weight };
}
