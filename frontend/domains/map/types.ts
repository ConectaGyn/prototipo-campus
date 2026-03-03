// domains/map/types.ts
//
// Tipos alinhados com os contratos atuais do backend:
// - GET /map/points
// - GET /points/{point_id}/risk

export type MapRiskLevel = "Baixo" | "Moderado" | "Alto" | "Muito Alto";

export interface MapPointView {
  id: string;
  nome: string;
  latitude: number;
  longitude: number;
  bairro: string | null;
  raio_influencia_m: number;
  ativo: boolean;
  municipality_id: number | null;
  icra: number | null;
  icra_std: number | null;
  nivel_risco: MapRiskLevel | null;
  nivel_risco_relativo: MapRiskLevel | null;
  confianca: string | null;
  referencia_em: string | null;
}

export interface MapPointsResponse {
  pontos: MapPointView[];
  snapshot_timestamp: string | null;
  snapshot_valid_until: string | null;
  total: number;
}

export interface PointRiskSnapshotResponse {
  point_id: string;
  icra: number;
  icra_std: number;
  nivel_risco: MapRiskLevel;
  nivel_risco_relativo: MapRiskLevel | null;
  confianca: string;
  referencia_em: string;
  fonte: "snapshot" | "on_demand";
}

export type RiskStatus = PointRiskSnapshotResponse;
