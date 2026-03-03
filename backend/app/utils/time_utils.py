"""
time_utils.py

Utilitários centrais de manipulação temporal do backend.

Regras arquiteturais do projeto:
- Todo datetime é UTC
- Todo datetime deve ser timezone-aware
- Snapshots utilizam timestamp arredondado por intervalo
- Nenhuma lógica de negócio deve existir aqui
"""

from datetime import datetime, date, timezone, timedelta
from typing import List


# =====================================================
# BASE UTC
# =====================================================

def utc_now() -> datetime:
    """
    Retorna datetime atual timezone-aware (UTC).
    """
    return datetime.now(timezone.utc)


def today_utc() -> date:
    """
    Retorna a data atual em UTC.
    """
    return utc_now().date()


# =====================================================
# NORMALIZAÇÃO
# =====================================================

def ensure_utc(dt: datetime) -> datetime:
    """
    Garante que um datetime esteja em UTC e timezone-aware.

    - Se for naive → assume UTC
    - Se tiver timezone → converte para UTC
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


# =====================================================
# SNAPSHOT / INTERVALOS
# =====================================================

def floor_to_hour_interval(
    dt: datetime,
    interval_hours: int,
) -> datetime:
    """
    Arredonda um datetime para baixo com base em um intervalo fixo de horas.

    Exemplo:
        interval=3
        14:37 → 12:00
        16:02 → 15:00
    """

    if interval_hours <= 0:
        raise ValueError("interval_hours deve ser maior que zero")

    dt = ensure_utc(dt)

    hour_block = (dt.hour // interval_hours) * interval_hours

    return dt.replace(
        hour=hour_block,
        minute=0,
        second=0,
        microsecond=0,
    )


def ceil_to_hour_interval(
    dt: datetime,
    interval_hours: int,
) -> datetime:
    """
    Arredonda para cima baseado no intervalo.

    Útil caso seja necessário para scheduler.
    """

    floored = floor_to_hour_interval(dt, interval_hours)

    if floored == ensure_utc(dt):
        return floored

    return floored + timedelta(hours=interval_hours)


# =====================================================
# HISTÓRICO
# =====================================================

def generate_past_dates(
    target_date: date,
    days: int,
) -> List[date]:
    """
    Gera lista de datas passadas (excluindo target_date).

    Ordem cronológica crescente.

    Exemplo:
        target=10
        days=3
        → [7, 8, 9]
    """

    if days <= 0:
        return []

    return [
        target_date - timedelta(days=i)
        for i in reversed(range(1, days + 1))
    ]


def generate_date_window(
    target_date: date,
    days: int,
) -> List[date]:
    """
    Gera janela incluindo o dia alvo.

    Exemplo:
        target=10
        days=3
        → [8, 9, 10]
    """

    if days <= 0:
        return [target_date]

    return [
        target_date - timedelta(days=i)
        for i in reversed(range(0, days))
    ]


# =====================================================
# SERIALIZAÇÃO
# =====================================================

def to_iso_datetime(dt: datetime) -> str:
    """
    Converte datetime para string ISO 8601 segura.
    """
    return ensure_utc(dt).isoformat()


def to_iso_date(d: date) -> str:
    """
    Converte date para string ISO.
    """
    return d.isoformat()


# =====================================================
# PARSING SEGURO
# =====================================================

def parse_iso_date(value: str) -> date:
    """
    Converte string ISO (YYYY-MM-DD) em date.
    """
    return date.fromisoformat(value)


def parse_iso_datetime(value: str) -> datetime:
    """
    Converte string ISO 8601 em datetime timezone-aware UTC.
    """
    dt = datetime.fromisoformat(value)
    return ensure_utc(dt)
