import type { ReactElement } from 'react';

export interface WeatherDescription {
  id: number;
  main: string;
  description: string;
  icon: string;
}

export interface CurrentWeather {
  dt: number;
  temp: number;
  feels_like: number;
  humidity: number;
  pressure: number;
  wind_speed: number; // in km/h for this app
  wind_deg: number;
  rain?: { '1h': number };
  weather: WeatherDescription[];
}

export interface DailyForecast {
  dt: number;
  temp: {
    min: number;
    max: number;
  };
  pop: number; // Probability of precipitation
  weather: WeatherDescription[];
}

export interface HourlyForecast {
    dt: number;
    temp: number;
    pop: number;
    weather: WeatherDescription[];
}

export interface WeatherData {
  current: CurrentWeather;
  daily: DailyForecast[];
  hourly: HourlyForecast[];
}

export type RiskLevel = 'Baixo' | 'Moderado' | 'Alto' | 'Muito Alto';

export interface RiskAlert {
  level: RiskLevel;
  message: string;
  color: string;
  icon: ReactElement;
}

export type SensorRiskLevel = 'Alto' | 'Moderado' | 'Nenhum';

export interface SensorAlert {
  level: SensorRiskLevel;
  message: string;
}

export interface SensorData {
  id: string;
  location: string;
  temp: number;
  humidity: number;
  wind_speed: number;
  level?: number | null;
  timestamp?: string | null;
  coords: { lat: number; lon: number; };
  alert?: SensorAlert;
}

export interface BackendSensorReading {
  sensorId?: string | null;
  location?: string | null;
  temp: number | null;
  humidity: number | null;
  wind_speed: number | null;
  level?: number | null;
  timestamp?: string | null;
}

export type SimulationIntensity = 'Normal' | 'Moderado' | 'Alto';

export interface SimulationOverride {
  intensity: SimulationIntensity;
  duration: number; // in seconds, used for UI state
  endTime: number; // timestamp, used for logic
}

export interface SimulationState {
  isEnabled: boolean;
  overrides: Record<string, SimulationOverride>; // Map sensor ID to config
}

export interface SensorLocationDef {
  id: string;
  name: string;
  coords: { lat: number; lon: number };
}
