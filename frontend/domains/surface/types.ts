// GEOJSON
export type GeoJSONGeometry =
  | {
      type: "Polygon";
      coordinates: number[][][];
    }
  | {
      type: "MultiPolygon";
      coordinates: number[][][][];
    };

// PROPRIEDADES REAIS DO BACKEND
export interface SurfaceCellProperties {
  risk_level: "Baixo" | "Moderado" | "Alto" | "Muito Alto";
  risk_value: number;
  risk_level_relative?: "Baixo" | "Moderado" | "Alto" | "Muito Alto";
  risk_value_relative?: number;
  color?: string;
  grid_resolution_m: number;
}

// FEATURE
export interface SurfaceFeature {
  type: "Feature";
  geometry: GeoJSONGeometry;
  properties: SurfaceCellProperties;
}

// COLLECTION
export interface SurfaceGeoJSON {
  type: "FeatureCollection";
  features: SurfaceFeature[];
}

// STATS
export interface SurfaceStats {
  total_cells: number;
  total_area_m2: number;
  high_risk_area_m2: number;
  high_risk_percentage: number;
}

// ENVELOPE REAL DO BACKEND
export interface SurfaceEnvelope {
  municipality_id: number;
  municipality_name: string;
  reference_ts: string;
  computed_at: string;
  valid_until: string;
  grid_resolution_m: number;
  kernel_sigma_m: number;
  stats: SurfaceStats;
  geojson: SurfaceGeoJSON;
}
