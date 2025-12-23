import type { CurrentWeather, SensorData, SensorAlert, SensorLocationDef, SimulationOverride } from '../types.ts';

export const sensorLocations: SensorLocationDef[] = [
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

const clamp = (num: number, min: number, max: number) => Math.min(Math.max(num, min), max);

/**
 * Calcula o nivel de risco para um unico sensor com base em seus dados.
 */
export const calculateSensorRisk = (sensor: Omit<SensorData, 'id' | 'location' | 'alert' | 'coords'>): SensorAlert => {
  const { temp, humidity, wind_speed } = sensor;
  
  if (temp > 40 || wind_speed > 50) {
    return {
      level: 'Alto',
      message: 'Risco Alto: Temperatura muito alta ou ventos muito fortes.'
    };
  }
  
  if (temp > 38 || humidity < 15 || wind_speed > 40) {
    return {
      level: 'Moderado',
      message: 'Risco Moderado: Condições de calor, baixa umidade ou vento forte.'
    };
  }

  return { level: 'Nenhum', message: 'Condições normais.' };
};

/**
 * Gera dados simulados para uma rede de sensores.
 * @param baseWeather Os dados climaticos atuais da API para usar como base.
 * @param simulationEnabled Se a simulacao esta ligada globalmente.
 * @param overrides Mapa de sobrescritas por ID do sensor.
 */
export const generateSimulatedSensorData = (
  baseWeather: CurrentWeather,
  simulationEnabled: boolean,
  overrides: Record<string, SimulationOverride>,
  sensorWeatherMap?: Record<string, CurrentWeather>
): SensorData[] => {
  
  const now = Date.now();

  return sensorLocations.map((location) => {
    // Usa o clima real do sensor quando disponivel; caso contrario, usa o clima do usuario como base.
    const baseForSensor = sensorWeatherMap?.[location.id] ?? baseWeather;
    let sensorMetrics;
    
    // Verifica se existe uma regra de simulacao ativa para este sensor especifico
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
      // Comportamento Padrao (Sem risco ou simulacao expirada): Variacao aleatoria baseada no clima real
      const tempVariation = (Math.random() - 0.5) * 3; // +/- 1.5 graus
      const humidityVariation = (Math.random() - 0.5) * 10; // +/- 5%
      const windVariation = (Math.random() - 0.5) * 10; // +/- 5 km/h

      sensorMetrics = {
        temp: parseFloat((baseForSensor.temp + tempVariation).toFixed(1)),
        humidity: Math.round(clamp(baseForSensor.humidity + humidityVariation, 0, 100)),
        wind_speed: Math.round(Math.max(0, baseForSensor.wind_speed + windVariation)),
      };
    }

    let alert: SensorAlert | undefined;

    // Calcula o risco com base nas metricas atuais (natural ou simulada).
    const calculatedAlert = calculateSensorRisk(sensorMetrics);
    if (calculatedAlert.level != 'Nenhum') {
      alert = calculatedAlert;
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
