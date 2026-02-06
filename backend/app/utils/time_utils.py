"""
time_utils.py

Utilitários relacionados a datas e tempo.

Centraliza o tratamento de timestamps, datas atuais
e formatação temporal, evitando inconsistências
ao longo da aplicação.
"""

from datetime import datetime, date, timezone


# ================================
# TEMPO ATUAL
# ================================

def utc_now() -> datetime:
    """
    Retorna o timestamp atual em UTC.

    Deve ser usado sempre que a aplicação precisar
    de um horário de referência confiável.
    """
    return datetime.now(timezone.utc)


def today_utc() -> date:
    """
    Retorna a data atual em UTC (sem informação de hora).
    """
    return utc_now().date()


# ================================
# FORMATAÇÃO
# ================================

def to_iso_datetime(dt: datetime) -> str:
    """
    Converte um datetime para string ISO 8601.

    Exemplo:
    2026-01-06T14:32:10+00:00
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def to_iso_date(d: date) -> str:
    """
    Converte uma date para string ISO.

    Exemplo:
    2026-01-06
    """
    return d.isoformat()


# ================================
# PARSING
# ================================

def parse_iso_date(value: str) -> date:
    """
    Converte uma string ISO (YYYY-MM-DD) em objeto date.
    """
    return date.fromisoformat(value)


def parse_iso_datetime(value: str) -> datetime:
    """
    Converte uma string ISO 8601 em objeto datetime.
    """
    return datetime.fromisoformat(value)
