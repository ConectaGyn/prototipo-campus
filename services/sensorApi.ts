import type { BackendSensorReading } from '../types.ts';

interface BackendSensorResponse {
  sensors: BackendSensorReading[];
  updatedAt: string | null;
  error?: string | null;
}

export const fetchLatestSensors = async (): Promise<BackendSensorResponse> => {
  const response = await fetch('/api/sensors/latest', { cache: 'no-store' });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Sensor API error: ${response.status} ${body}`);
  }
  return response.json();
};
