import type { CurrentWeather, SensorData, SensorAlert, SensorLocationDef, SimulationOverride } from '../types.ts';

export const sensorLocations: SensorLocationDef[] = [
  { id: 'setor-bueno', name: 'Setor Bueno', coords: { lat: -16.6995, lon: -49.2798 } },
  { id: 'jardim-goias', name: 'Jardim Goiás', coords: { lat: -16.6970, lon: -49.2415 } },
  { id: 'setor-marista', name: 'Setor Marista', coords: { lat: -16.6950, lon: -49.2700 } },
  { id: 'centro', name: 'Centro', coords: { lat: -16.6786, lon: -49.2533 } },
  { id: 'parque-amazonas', name: 'Parque Amazonas', coords: { lat: -16.7325, lon: -49.2794 } },
  { id: 'jardim-america', name: 'Jardim América', coords: { lat: -16.7118, lon: -49.2795 } },
  { id: 'setor-oeste', name: 'Setor Oeste', coords: { lat: -16.6789, lon: -49.2717 } },
  { id: 'vila-nova', name: 'Vila Nova', coords: { lat: -16.6669, lon: -49.2381 } },
  { id: 'setor-pedro-ludovico', name: 'St. Pedro Ludovico', coords: { lat: -16.7114, lon: -49.2573 } },
  { id: 'parque-flamboyant', name: 'Parque Flamboyant', coords: { lat: -16.6983, lon: -49.2392 } },
];

const clamp = (num: number, min: number, max: number) => Math.min(Math.max(num, min), max);

/**
 * Calcula o nível de risco para um único sensor com base em seus dados.
 */
const calculateSensorRisk = (sensor: Omit<SensorData, 'id' | 'location' | 'alert' | 'coords'>): SensorAlert => {
  const { temp, humidity, wind_speed } = sensor;
  
  if (temp > 38 || wind_speed > 40) {
    return {
      level: 'Alto',
      message: 'Risco Alto: Temperatura muito alta ou ventos muito fortes.'
    };
  }
  
  if (temp > 35 || humidity < 20 || wind_speed > 30) {
    return {
      level: 'Moderado',
      message: 'Risco Moderado: Condições de calor, baixa umidade ou vento forte.'
    };
  }

  return { level: 'Nenhum', message: 'Condições normais.' };
};

/**
 * Gera dados simulados para uma rede de sensores.
 * @param baseWeather Os dados climáticos atuais da API para usar como base.
 * @param simulationEnabled Se a simulação está ligada globalmente.
 * @param overrides Mapa de sobrescritas por ID do sensor.
 */
export const generateSimulatedSensorData = (
  baseWeather: CurrentWeather, 
  simulationEnabled: boolean,
  overrides: Record<string, SimulationOverride>
): SensorData[] => {
  
  const now = Date.now();

  return sensorLocations.map((location) => {
    let sensorMetrics;
    
    // Verifica se existe uma regra de simulação ativa para este sensor específico
    const override = simulationEnabled ? overrides[location.id] : null;
    const isActiveOverride = override && override.endTime > now && override.intensity !== 'Normal';

    if (isActiveOverride && override?.intensity === 'Alto') {
      // Simula Risco Alto
      sensorMetrics = {
        temp: parseFloat((39 + Math.random() * 2).toFixed(1)), // 39.0 a 41.0
        humidity: Math.round(15 + Math.random() * 10),
        wind_speed: Math.round(45 + Math.random() * 15) // 45 a 60 km/h
      };
    } else if (isActiveOverride && override?.intensity === 'Moderado') {
      // Simula Risco Moderado
      sensorMetrics = {
        temp: parseFloat((36 + Math.random() * 1.5).toFixed(1)), // 36.0 a 37.5
        humidity: Math.round(20 + Math.random() * 5),
        wind_speed: Math.round(25 + Math.random() * 10)
      };
    } else {
      // Comportamento Padrão (Sem risco ou simulação expirada): Variação aleatória baseada no clima real
      const tempVariation = (Math.random() - 0.5) * 3; // +/- 1.5 graus
      const humidityVariation = (Math.random() - 0.5) * 10; // +/- 5%
      const windVariation = (Math.random() - 0.5) * 10; // +/- 5 km/h

      sensorMetrics = {
        temp: parseFloat((baseWeather.temp + tempVariation).toFixed(1)),
        humidity: Math.round(clamp(baseWeather.humidity + humidityVariation, 0, 100)),
        wind_speed: Math.round(Math.max(0, baseWeather.wind_speed + windVariation)),
      };
    }

    let alert: SensorAlert | undefined;

    // Calcula o risco e gera alerta APENAS se for um override ativo.
    // No modo normal, assumimos que as variações aleatórias não devem disparar alarmes falsos no app.
    if (isActiveOverride) {
      const calculatedAlert = calculateSensorRisk(sensorMetrics);
      if (calculatedAlert.level !== 'Nenhum') {
        alert = calculatedAlert;
      }
    }

    return {
      id: location.id,
      location: location.name,
      coords: location.coords,
      ...sensorMetrics,
      ...(alert && { alert }),
    };
  });
};