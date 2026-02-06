// domains/sensors/types.ts
//
// Tipos relacionados aos elementos exibidos no mapa e UI
// Um SensorData pode representar:
// - um ponto crítico real do backend
// - um ponto climático (OpenWeather)
// - um ponto simulado (módulo de simulação)
//

import type { ReactElement } from 'react';

export type SensorRiskLevel =
  | 'Baixo'
  | 'Moderado'
  | 'Alto'
  | 'Muito Alto'
  | 'Nenhum';

export type SensorRiskStatus = 'nao_avaliado' | 'avaliado';

export interface SensorAlert {
  level: SensorRiskLevel;
  status?: SensorRiskStatus;
  icra?: number;
  message?: string;
  confianca?: string;
  color?: string;
  icon?: ReactElement;
}

export interface SensorData {
  id: string;
  location: string;
  coords: { lat: number; lon: number };
  temp?: number;
  humidity?: number;
  wind_speed?: number;
  pressure?: number;
  feels_like?: number;
  rain?: any;
  alert?: SensorAlert | null;
}

export interface SensorLocationDef {
  id: string;
  name: string;
  coords: { lat: number; lon: number };
}
