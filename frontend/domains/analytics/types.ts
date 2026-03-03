// frontend/domains/analytics/types.ts
//
// Tipos para Analytics (Inteligência Territorial)
// Contratos dos endpoints:
// - GET /analytics/municipalities/{id}/metrics
// - GET /analytics/municipalities/{id}/metrics/series
//

export interface MunicipalityInfo {
  id: number;
  name: string;
  ibge_code: string | null;
  active: boolean;
  bbox_min_lat: number;
  bbox_min_lon: number;
  bbox_max_lat: number;
  bbox_max_lon: number;
  updated_at: string; // ISO
}

export interface SurfaceInfo {
  snapshot_timestamp: string; // ISO
  valid_until: string | null; // ISO
  grid_resolution_m: number;
  kernel_sigma_m: number;
  total_cells: number | null;
  total_area_m2: number | null;
  high_risk_area_m2: number | null;
  high_risk_percentage: number | null;
  source: string;
}

export interface SurfaceSummary {
  total_area_m2: number;
  high_risk_area_m2: number;
  high_risk_percentage: number;
  mean_icra: number;
  median_icra: number;
  max_icra: number;
  std_icra: number;
  total_cells: number;
  high_risk_cells: number;
}

export type RiskClassification = "Baixo" | "Moderado" | "Alto" | "Crítico" | string;

export interface TerritorialMetrics {
  severity_score: number;       // 0..1
  criticality_score: number;    // 0..1
  dispersion_index: number;     // >=0
  exposure_index: number;       // 0..1
  risk_classification: RiskClassification;
}

export interface TerritorialMetricsResponse {
  municipality: MunicipalityInfo;
  surface: SurfaceInfo;
  high_risk_threshold: number;
  surface_summary: SurfaceSummary;
  territorial_metrics: TerritorialMetrics;
}

export interface MetricsSeriesItem {
  snapshot_timestamp: string; // ISO
  surface_summary: SurfaceSummary;
  territorial_metrics: TerritorialMetrics;
}

export interface TerritorialMetricsSeriesResponse {
  municipality: MunicipalityInfo;
  total: number;
  high_risk_threshold: number;
  series: MetricsSeriesItem[];
}
