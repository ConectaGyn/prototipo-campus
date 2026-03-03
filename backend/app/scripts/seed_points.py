"""
seed_points.py

Script administrativo para popular a tabela `points`
a partir do CSV `pontos_criticos.csv`.

Responsabilidade:
- Ler CSV
- Inserir pontos no banco (idempotente)
- Não duplicar registros
- Não recalcular risco
- Não chamar IA
"""

import csv
import os
from pathlib import Path
from typing import Tuple
from sqlalchemy.exc import SQLAlchemyError
from backend.app import database
from backend.app.models import Point
from backend.app.models import Municipality


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "pontos_criticos.csv"


# ==========================================================
# UTILITÁRIOS
# ==========================================================

def generate_point_id(latitude: float, longitude: float) -> str:
    """
    Gera ID determinístico baseado nas coordenadas.
    Evita duplicação e não depende da ordem do CSV.
    """
    return f"grid_{latitude:.6f}_{longitude:.6f}"


def normalize_row(row: dict) -> Tuple[str, float, float]:
    """
    Valida e normaliza uma linha do CSV.
    """
    name = row.get("local", "").strip()

    if not name:
        raise ValueError("Nome do ponto vazio")

    try:
        latitude = float(row.get("latitude"))
        longitude = float(row.get("longitude"))
    except Exception:
        raise ValueError("Latitude ou longitude inválida")

    return name, latitude, longitude


# ==========================================================
# SEED PRINCIPAL
# ==========================================================

def seed_points() -> dict:
    print("\n=======================================")
    print("=== SEED DE PONTOS CRÍTICOS INICIADO ===")
    print("=======================================\n")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV não encontrado em: {CSV_PATH}")

    database.init_database()

    SessionLocal = database.SessionLocal
    if SessionLocal is None:
        raise RuntimeError("SessionLocal não inicializada")
    

    total_lidos = 0
    inseridos = 0
    ignorados = 0
    erros = 0

    with SessionLocal() as session:

        try:
            municipality = session.query(Municipality).filter_by(name="Goiânia").first()

            if not municipality:
                raise RuntimeError("Município Goiânia não encontrado")
            
            municipality_id = municipality.id

            with open(CSV_PATH, mode="r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    total_lidos += 1

                    try:
                        name, latitude, longitude = normalize_row(row)
                        point_id = generate_point_id(latitude, longitude)

                        # Verifica se já existe
                        existing = session.get(Point, point_id)

                        if existing:
                            ignorados += 1
                            continue

                        new_point = Point(
                            id=point_id,
                            name=name,
                            latitude=latitude,
                            longitude=longitude,
                            active=True,
                            influence_radius_m=300,
                            municipality_id=municipality_id,
                            neighborhood=None,
                            description=None,
                        )

                        session.add(new_point)
                        inseridos += 1

                    except Exception as e:
                        erros += 1
                        print(f"[ERRO] Linha {total_lidos}: {e}")

                session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Erro de banco: {e}") from e

    print("\n=======================================")
    print("=== RESUMO DO SEED ===")
    print("=======================================")
    print(f"Total lidos: {total_lidos}")
    print(f"Inseridos: {inseridos}")
    print(f"Ignorados (já existentes): {ignorados}")
    print(f"Erros: {erros}")
    print("\nProcesso concluído.\n")

    return {
        "inserted": inseridos,
        "ignored": ignorados,
        "errors": erros,
    }

# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":
    seed_points()
