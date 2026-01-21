// domains/map/types.ts
//
// Tipos relacionados à visualização de pontos críticos no mapa.
// Representam exatamente o contrato do endpoint GET /map/points
// do backend ClimaGyn.
//
// Estes tipos NÃO contêm lógica de UI.
// São contratos de dados entre Backend ↔ Frontend.


// ===============================
// LOCALIZAÇÃO GEOGRÁFICA
// ===============================

export interface GeoLocation {
  latitude: number;
  longitude: number;
}


// ===============================
// PONTO CRÍTICO (DADOS BÁSICOS)
// ===============================

export interface CriticalPoint {
  id: string;
  nome: string;
  localizacao: GeoLocation;

  ativo: boolean;
  raio_influencia_m: number;

  bairro: string | null;
  descricao: string | null;
}


// ===============================
// RISCO (STATUS ATUAL)
// ===============================

export type RiskLevel = 'Baixo' | 'Moderado' | 'Alto' | 'Muito Alto';

export interface RiskStatus {
  icra: number;
  nivel: RiskLevel;
  confianca: "Alta" | "Média" | "Baixa" | string;
  cor: string;
}


// ===============================
// PONTO + RISCO (MAPA)
// ===============================
    
export interface MapPoint {
  ponto: CriticalPoint;

  /**
   * Estado de risco atual.
   * Pode ser null quando:
   * - A IA está indisponível
   * - Erro de inferência
   * - Ambiente de Validação
   */
  risco_atual: RiskStatus | null;
}


// ===============================
// RESPOSTA DO ENDPOINT /map/points
// ===============================

export interface MapPointsResponse {
  pontos: MapPoint[];
  atualizado_em: string;
}
