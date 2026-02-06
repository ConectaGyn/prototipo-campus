import type {
  CurrentWeather,
  SensorData,
  SensorAlert,
  SensorLocationDef,
  SimulationOverride
} from '../../types.ts';

/**
 * --------------------------------------------------
 * MÓDULO DE SIMULAÇÃO (NÃO USAR EM PRODUÇÃO)
 *
 * Ele NÃO representa sensores reais.
 * Ele NÃO é fonte oficial de pontos críticos.
 *
 * Os dados reais vêm do backend via /map/points.
 *
 * Este módulo existe para:
 * - modo demo
 * - modo simulação
 * - fallback visual
 * --------------------------------------------------
 */

export const simulatedSensorLocations: SensorLocationDef[] = [
  { id: 'marginal-botafogo-jamel-cecilio', name: 'Marginal Botafogo x Viaduto Jamel Cecilio', coords: { lat: -16.701694, lon: -49.244306 } },
  { id: 'marginal-botafogo-avenida-goias', name: 'Marginal Botafogo x Avenida Goias', coords: { lat: -16.653861, lon: -49.262556 } },
  { id: 'vila-redencao-nonato-mota', name: 'Vila Redencao - Rua Nonato Mota', coords: { lat: -16.717972, lon: -49.246167 } },
  { id: 'parque-amazonia-serrinha', name: 'Parque Amazonia - Feira de Santana x Serrinha', coords: { lat: -16.727750, lon: -49.272056 } },
  { id: 'joao-bras-francisco-oliveira', name: 'Pq Industrial Joao Bras - Av. Francisco Alves de Oliveira', coords: { lat: -16.684667, lon: -49.354833 } },
  { id: 'pedro-ludovico-radial-botafogo', name: 'Pedro Ludovico - 3a Radial x Corrego Botafogo', coords: { lat: -16.721889, lon: -49.250028 } },
  { id: 'finsocial-vf82', name: 'Finsocial - Rua VF-82', coords: { lat: -16.628584, lon: -49.323695 } },
  { id: 'finsocial-vf96', name: 'Finsocial - Rua VF-96', coords: { lat: -16.630667, lon: -49.319667 } },
  { id: 'setor-sul-praca-ratinho', name: 'Setor Sul - Praca do Ratinho', coords: { lat: -16.691028, lon: -49.261194 } },
  { id: 'goiania-viva-taquaral', name: 'Residencial Goiania Viva - Av. Gabriel H. Araujo x Corrego Taquaral', coords: { lat: -16.700917, lon: -49.347833 } },
  { id: 'campinas-marechal-deodoro', name: 'Campinas - Av. Marechal Deodoro', coords: { lat: -16.665278, lon: -49.295944 } },
  { id: 'campinas-jose-hermano-neropolis', name: 'Campinas/Perim - Av. Jose Hermano x Av. Neropolis', coords: { lat: -16.655417, lon: -49.289972 } },
  { id: 'campinas-rio-grande-sul', name: 'Campinas - Av. Rio Grande do Sul', coords: { lat: -16.666056, lon: -49.296667 } },
  { id: 'campinas-sergipe', name: 'Campinas - Av. Sergipe', coords: { lat: -16.664000, lon: -49.296833 } },
  { id: 'campininha-das-flores', name: 'Parque Campininha das Flores - Campinas', coords: { lat: -16.663917, lon: -49.298139 } },
  { id: 'vila-montecelli-perimetral', name: 'Vila Montecelli - Av. Perimetral', coords: { lat: -16.647944, lon: -49.250722 } },
  { id: 'setor-norte-ferroviario-contorno', name: 'Regiao 44 Norte - Av. Contorno', coords: { lat: -16.657389, lon: -49.256389 } },
];

export const sensorLocations = simulatedSensorLocations;

const clamp = (num: number, min: number, max: number) =>
  Math.min(Math.max(num, min), max);

/**
 * Calcula risco SIMULADO para um sensor
 */
const calculateSensorRisk = (
  sensor: Omit<SensorData, 'id' | 'location' | 'alert' | 'coords'>
): SensorAlert => {
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
 * Gera dados climáticos simuladossensores SIMULADOS
 *
 * Nunca deve ser usado como dado real
 */
export const generateSimulatedSensorData = (
  baseWeather: CurrentWeather,
  simulationEnabled: boolean,
  overrides: Record<string, SimulationOverride>,
  sensorWeatherMap?: Record<string, CurrentWeather>
): SensorData[] => {

  const now = Date.now();

  return sensorLocations.map(location => {
    const baseForSensor =
      sensorWeatherMap?.[location.id] ?? baseWeather;

    let sensorMetrics;

    const override =
      simulationEnabled ? overrides[location.id] : null;

    const isActiveOverride =
      override &&
      override.endTime > now &&
      override.intensity !== 'Normal';

    if (isActiveOverride && override?.intensity === 'Alto') {
      sensorMetrics = {
        temp: parseFloat((39 + Math.random() * 2).toFixed(1)),
        humidity: Math.round(15 + Math.random() * 10),
        wind_speed: Math.round(45 + Math.random() * 15)
      };
    } else if (isActiveOverride && override?.intensity === 'Moderado') {
      sensorMetrics = {
        temp: parseFloat((36 + Math.random() * 1.5).toFixed(1)),
        humidity: Math.round(20 + Math.random() * 5),
        wind_speed: Math.round(25 + Math.random() * 10)
      };
    } else {
      sensorMetrics = {
        temp: parseFloat((baseForSensor.temp + (Math.random() - 0.5) * 3).toFixed(1)),
        humidity: Math.round(
          clamp(baseForSensor.humidity + (Math.random() - 0.5) * 10, 0, 100)
        ),
        wind_speed: Math.round(
          Math.max(0, baseForSensor.wind_speed + (Math.random() - 0.5) * 10)
        ),
      };
    }

    const calculatedAlert = calculateSensorRisk(sensorMetrics);
    const alert =
      calculatedAlert.level !== 'Nenhum'
        ? calculatedAlert
        : undefined;

    return {
      id: location.id,
      location: location.name,
      coords: location.coords,
      ...sensorMetrics,
      ...(alert && { alert }),
    };
  });
};
