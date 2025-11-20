
/**
 * Calcula a distância em quilômetros entre dois pontos geográficos usando a fórmula de Haversine.
 * @param lat1 Latitude do ponto 1
 * @param lon1 Longitude do ponto 1
 * @param lat2 Latitude do ponto 2
 * @param lon2 Longitude do ponto 2
 * @returns Distância em km
 */
export const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
  const R = 6371; // Raio da Terra em km
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

const toRad = (value: number): number => {
  return (value * Math.PI) / 180;
};

/**
 * Verifica se um ponto de risco (sensor) está próximo da rota (linha reta) entre origem e destino.
 * @param start Coordenadas de origem (usuário)
 * @param end Coordenadas de destino (ponto de apoio)
 * @param riskPoint Coordenadas do ponto de risco
 * @param thresholdKm Distância mínima de segurança em km (ex: 2km)
 */
export const checkRouteRisk = (
  start: { lat: number; lon: number },
  end: { lat: number; lon: number },
  riskPoint: { lat: number; lon: number },
  thresholdKm: number = 2.0
): boolean => {
  // Converte lat/lon para um sistema cartesiano aproximado (em km) relativo ao ponto de início
  // 1 grau lat ~= 111km. 1 grau lon ~= 111 * cos(lat)
  const ky = 40000 / 360;
  const kx = Math.cos((Math.PI * start.lat) / 180.0) * ky;

  const Ax = 0;
  const Ay = 0;
  const Bx = (end.lon - start.lon) * kx;
  const By = (end.lat - start.lat) * ky;
  const Px = (riskPoint.lon - start.lon) * kx;
  const Py = (riskPoint.lat - start.lat) * ky;

  // Calcula a projeção do ponto P no segmento AB
  const dot = Px * Bx + Py * By;
  const len_sq = Bx * Bx + By * By;
  
  // Parâmetro t da projeção (0 <= t <= 1 significa que a projeção cai dentro do segmento)
  let param = -1;
  if (len_sq !== 0) // evita divisão por zero
      param = dot / len_sq;

  let xx, yy;

  if (param < 0) {
    xx = Ax;
    yy = Ay;
  } else if (param > 1) {
    xx = Bx;
    yy = By;
  } else {
    xx = Ax + param * Bx;
    yy = Ay + param * By;
  }

  const dx = Px - xx;
  const dy = Py - yy;
  const distance = Math.sqrt(dx * dx + dy * dy);

  return distance < thresholdKm;
};
