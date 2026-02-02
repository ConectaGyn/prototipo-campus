"""
point.py

Modelo de domínio para Pontos Críticos de Alagamento.

Este objeto representa um ponto físico monitorado no mapa,
independente de fonte climática, IA ou persistência.

Não é schema de API
Não contém lógica de negócio complexa
"""

from dataclasses import dataclass
from typing import Optional


# ======================================================
# VALOR-OBJETO
# ======================================================

@dataclass(frozen=True)
class GeoLocation:
    """
    Representa uma coordenada geográfica.
    """

    latitude: float
    longitude: float


# ======================================================
# ENTIDADE DE DOMÍNIO
# ======================================================

@dataclass
class CriticalPoint:
    """
    Representa um ponto crítico de alagamento monitorado.
    """

    id: str
    nome: str
    localizacao: GeoLocation

    # Metadados operacionais
    ativo: bool = True
    raio_influencia_m: int = 300

    # Classificação estática
    bairro: Optional[str] = None
    descricao: Optional[str] = None

    # ---------------------------------
    # Helpers simples
    # ---------------------------------

    def is_active(self) -> bool:
        """
        Indica se o ponto está ativo para monitoramento.
        """
        return self.ativo

    def coordinates(self) -> tuple[float, float]:
        """
        Retorna coordenadas no formato (lat, lon).
        """
        return (self.localizacao.latitude, self.localizacao.longitude)
    
    def to_feature_payload(self) -> dict:
        """
        Retorna uma dicionário básico com informações do ponto
        para uso em builders de features ou serviços externos
        """
        return {
            "id": self.id,
            "latitude": self.localizacao.latitude,
            "longitude": self.localizacao.longitude,
            "influence_radius_m": self.raio_influencia_m,
            "bairro": self.bairro,
        }


# ======================================================
# ALIAS DE COMPATIBILIDADE
# ======================================================

# Alias para integração com services e rotas
Point = CriticalPoint
