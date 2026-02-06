// domains/risk/types.ts

import type { ReactElement } from 'react';

export type RiskLevel =
  | 'Nenhum'
  | 'Baixo'
  | 'Moderado'
  | 'Alto'
  | 'Muito Alto';

export interface RiskAlert {
  level: RiskLevel;
  message?: string;
  color?: string;
  icon?: ReactElement;
  icra?: number;
  confianca?: string;
}
