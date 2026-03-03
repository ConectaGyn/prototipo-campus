"""
seed_municipality.py

Script administrativo para popular a tabela `municipalities`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from sqlalchemy.exc import SQLAlchemyError

from backend.app import database
from backend.app.models import Municipality


MUNICIPALITIES: List[Dict[str, str]] = [
    {
        "name": "Goiânia",
        "ibge_code": "5208707",
        "geojson_path": "backend/app/data/municipalities/goiania.geojson",
    },
]


def _extract_bbox_from_geojson(geojson: Dict) -> Dict[str, float]:
    def extract_coords(obj):
        if isinstance(obj, list):
            for item in obj:
                yield from extract_coords(item)
        elif isinstance(obj, (int, float)):
            yield obj

    coords: List[float] = []

    if geojson["type"] == "Feature":
        geometry = geojson.get("geometry", {})
        coords = list(extract_coords(geometry.get("coordinates", [])))
    elif geojson["type"] == "FeatureCollection":
        features = geojson.get("features", [])
        if not features:
            raise ValueError("FeatureCollection vazia.")
        for feature in features:
            geometry = feature.get("geometry", {})
            coords.extend(extract_coords(geometry.get("coordinates", [])))
    else:
        raise ValueError("Tipo GeoJSON nao suportado.")

    if len(coords) < 4:
        raise ValueError("GeoJSON invalido ou sem coordenadas.")

    lons = coords[0::2]
    lats = coords[1::2]

    return {
        "bbox_min_lon": min(lons),
        "bbox_min_lat": min(lats),
        "bbox_max_lon": max(lons),
        "bbox_max_lat": max(lats),
    }


def _load_geojson_from_path(path: str) -> Dict:
    geo_path = Path(path)
    if not geo_path.is_absolute():
        geo_path = Path(__file__).resolve().parents[3] / geo_path

    if not geo_path.exists():
        raise FileNotFoundError(f"GeoJSON nao encontrado: {geo_path}")

    with open(geo_path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def seed_municipalities() -> dict:
    print("\n=======================================")
    print("=== SEED DE MUNICIPIOS INICIADO ===")
    print("=======================================\n")

    database.init_database()

    inseridos = 0
    ignorados = 0
    erros = 0

    with database.SessionLocal() as session:
        try:
            for item in MUNICIPALITIES:
                name = item["name"].strip()
                ibge_code = item.get("ibge_code")
                geojson = _load_geojson_from_path(item["geojson_path"])
                bbox = _extract_bbox_from_geojson(geojson)

                existing = (
                    session.query(Municipality)
                    .filter_by(name=name)
                    .first()
                )

                if existing:
                    print(f"[IGNORADO] Municipio ja existe: {name}")
                    ignorados += 1
                    continue

                municipality = Municipality(
                    name=name,
                    ibge_code=ibge_code,
                    active=True,
                    geojson=geojson,
                    bbox_min_lon=bbox["bbox_min_lon"],
                    bbox_min_lat=bbox["bbox_min_lat"],
                    bbox_max_lon=bbox["bbox_max_lon"],
                    bbox_max_lat=bbox["bbox_max_lat"],
                )
                session.add(municipality)
                inseridos += 1
                print(f"[INSERIDO] Municipio criado: {name}")

            session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            erros += 1
            print(f"[ERRO] Falha ao inserir municipios: {e}")

    print("\n=======================================")
    print("=== RESUMO DO SEED MUNICIPIOS ===")
    print("=======================================")
    print(f"Inseridos: {inseridos}")
    print(f"Ignorados (ja existentes): {ignorados}")
    print(f"Erros: {erros}")
    print("=======================================\n")

    return {
        "inserted": inseridos,
        "ignored": ignorados,
        "errors": erros,
    }


if __name__ == "__main__":
    seed_municipalities()
