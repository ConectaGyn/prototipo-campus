import type { SensorLocationDef } from "../../types.ts";

/**
 * Dados legados para configuracao de simulacao.
 * Fonte oficial para monitoramento real continua sendo o backend (/map/points).
 */
export const sensorLocations: SensorLocationDef[] = [
  { id: "marginal-botafogo-jamel-cecilio", name: "Marginal Botafogo x Viaduto Jamel Cecilio", coords: { lat: -16.701694, lon: -49.244306 } },
  { id: "marginal-botafogo-avenida-goias", name: "Marginal Botafogo x Avenida Goias", coords: { lat: -16.653861, lon: -49.262556 } },
  { id: "vila-redencao-nonato-mota", name: "Vila Redencao - Rua Nonato Mota", coords: { lat: -16.717972, lon: -49.246167 } },
  { id: "parque-amazonia-serrinha", name: "Parque Amazonia - Feira de Santana x Serrinha", coords: { lat: -16.72775, lon: -49.272056 } },
  { id: "joao-bras-francisco-oliveira", name: "Pq Industrial Joao Bras - Av. Francisco Alves de Oliveira", coords: { lat: -16.684667, lon: -49.354833 } },
  { id: "pedro-ludovico-radial-botafogo", name: "Pedro Ludovico - 3a Radial x Corrego Botafogo", coords: { lat: -16.721889, lon: -49.250028 } },
  { id: "finsocial-vf82", name: "Finsocial - Rua VF-82", coords: { lat: -16.628584, lon: -49.323695 } },
  { id: "finsocial-vf96", name: "Finsocial - Rua VF-96", coords: { lat: -16.630667, lon: -49.319667 } },
  { id: "setor-sul-praca-ratinho", name: "Setor Sul - Praca do Ratinho", coords: { lat: -16.691028, lon: -49.261194 } },
  { id: "goiania-viva-taquaral", name: "Residencial Goiania Viva - Av. Gabriel H. Araujo x Corrego Taquaral", coords: { lat: -16.700917, lon: -49.347833 } },
  { id: "campinas-marechal-deodoro", name: "Campinas - Av. Marechal Deodoro", coords: { lat: -16.665278, lon: -49.295944 } },
  { id: "campinas-jose-hermano-neropolis", name: "Campinas/Perim - Av. Jose Hermano x Av. Neropolis", coords: { lat: -16.655417, lon: -49.289972 } },
  { id: "campinas-rio-grande-sul", name: "Campinas - Av. Rio Grande do Sul", coords: { lat: -16.666056, lon: -49.296667 } },
  { id: "campinas-sergipe", name: "Campinas - Av. Sergipe", coords: { lat: -16.664, lon: -49.296833 } },
  { id: "campininha-das-flores", name: "Parque Campininha das Flores - Campinas", coords: { lat: -16.663917, lon: -49.298139 } },
  { id: "vila-montecelli-perimetral", name: "Vila Montecelli - Av. Perimetral", coords: { lat: -16.647944, lon: -49.250722 } },
  { id: "setor-norte-ferroviario-contorno", name: "Regiao 44 Norte - Av. Contorno", coords: { lat: -16.657389, lon: -49.256389 } },
];
