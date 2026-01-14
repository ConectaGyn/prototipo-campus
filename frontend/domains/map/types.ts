// domains/map/types.ts
//
// Tipos relacionados à visualização de pontos críticos no mapa.
// Representam exatamente o contrato do endpoint GET /map/points
// do backend ClimaGyn.
//
// Estes tipos NÃO contêm lógica de UI.
// São contratos de dados entre Backend ↔ Frontend.

import { RiskLevel } from "@/types";


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

export type RiskCategory = 'Baixo' | 'Moderado' | 'Alto' | 'Muito Alto';

export interface RiskStatus {
  /**
   * Índice Composto de Risco de Alagamento (0 a 1)
   */
  icra: number;

  /**
   * Classificação qualitativa do risco
   * Ex: "Baixo", "Moderado", "Alto", "Muito Alto"
   */
  nivel: RiskLevel;

  /**
   * Nível de confiança da previsão
   * Ex: "Alta", "Média", "Baixa"
   */
  confianca: string;

  /**
   * Cor associada ao risco para uso no mapa
   * Ex: "verde", "amarelo", "vermelho"
   */
  cor: string;
}


// ===============================
// PONTO + RISCO (MAPA)
// ===============================
    
export interface MapPoint {
  /**
   * Dados do ponto crítico
   */
  ponto: CriticalPoint;

  /**
   * Estado de risco atual.
   * Pode ser null quando:
   * - A IA está indisponível
   * - O risco ainda não foi calculado
   * - Estamos em modo de validação
   */
  risco_atual: RiskStatus | null;
}


// ===============================
// RESPOSTA DO ENDPOINT /map/points
// ===============================

export interface MapPointsResponse {
  /**
   * Lista de pontos críticos prontos para renderização no mapa
   */
  pontos: MapPoint[];

  /**
   * Timestamp ISO da última atualização
   */
  atualizado_em: string;
}
