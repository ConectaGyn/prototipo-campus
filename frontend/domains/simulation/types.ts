// domains/simulation/types.ts

export type SimulationIntensity = 'Normal' | 'Moderado' | 'Alto';

export interface SimulationOverride {
  intensity: SimulationIntensity;
  duration: number; // seconds (UI)
  endTime: number;  // timestamp (logic)
}

export interface SimulationState {
  isEnabled: boolean;
  overrides: Record<string, SimulationOverride>;
}

