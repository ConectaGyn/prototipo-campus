import requests
import pandas as pd
import numpy as np
import time
import warnings
import os
from datetime import datetime
from requests.exceptions import HTTPError

warnings.filterwarnings("ignore")

# =========================================================
# CONFIGURAÇÕES GERAIS
# =========================================================

ARQUIVO_COORDENADAS = "ai/data/metadata/pontos_criticos.csv"
TIMEZONE = "America/Sao_Paulo"
DATA_INICIO_HISTORICO = "1980-01-01"
ESPERA_ENTRE_PONTOS = 60  # segundos
MAX_TENTATIVAS = 3
BASE_DATA_DIR = "ai/data"

# =========================================================
# FUNÇÃO DE REQUISIÇÃO  (RETRY + BACKOFF)
# =========================================================

def request_com_retry(url, params, max_tentativas=MAX_TENTATIVAS):
    espera = 10

    for tentativa in range(1, max_tentativas + 1):
        try:
            resposta = requests.get(url, params=params, timeout=120)

            if resposta.status_code == 429:
                raise HTTPError("429 Too Many Requests")

            resposta.raise_for_status()
            return resposta.json()

        except HTTPError as erro:
            print(
                f"⚠ Tentativa {tentativa}/{max_tentativas} falhou ({erro}). "
                f"Aguardando {espera}s..."
            )
            time.sleep(espera)
            espera *= 2

    raise RuntimeError("❌ Falha definitiva após múltiplas tentativas.")

# =========================================================
# DOWNLOAD DOS DADOS
# =========================================================

def baixar_dados_historicos(lat, lon):
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": DATA_INICIO_HISTORICO,
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation"
        ],
        "daily": [
            "weather_code",
            "temperature_2m_mean",
            "apparent_temperature_mean",
            "precipitation_sum",
            "precipitation_hours"
        ],
        "timezone": TIMEZONE
    }

    return request_com_retry(url, params)


def baixar_dados_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation"
        ],
        "daily": [
            "weather_code",
            "temperature_2m_mean",
            "apparent_temperature_mean",
            "precipitation_sum",
            "precipitation_hours"
        ],
        "past_days": 7,
        "forecast_days": 16,
        "timezone": TIMEZONE
    }

    return request_com_retry(url, params)

# =========================================================
# PROCESSAMENTO DOS DADOS
# =========================================================

def processar_dados(dados, fonte, local):
    h = dados["hourly"]
    d = dados["daily"]

    df_horario = pd.DataFrame({
        "data_hora": pd.to_datetime(h["time"]),
        "temperatura_2m_C": h["temperature_2m"],
        "umidade_relativa_2m_pct": h["relative_humidity_2m"],
        "precipitacao_mm": h["precipitation"],
        "fonte": fonte,
        "local": local
    })

    df_diario = pd.DataFrame({
        "data": pd.to_datetime(d["time"]),
        "codigo_clima": d["weather_code"],
        "temperatura_media_2m_C": d["temperature_2m_mean"],
        "temperatura_aparente_media_2m_C": d["apparent_temperature_mean"],
        "precipitacao_total_mm": d["precipitation_sum"],
        "horas_precipitacao": d["precipitation_hours"],
        "fonte": fonte,
        "local": local
    })

    return df_horario, df_diario

# =========================================================
# FEATURE ENGINEERING
# =========================================================

def criar_features_horarias(df):
    df = df.copy()

    df["ano"] = df["data_hora"].dt.year
    df["mes"] = df["data_hora"].dt.month
    df["dia"] = df["data_hora"].dt.day
    df["hora"] = df["data_hora"].dt.hour
    df["dia_do_ano"] = df["data_hora"].dt.dayofyear
    df["dia_da_semana"] = df["data_hora"].dt.dayofweek

    df["hora_sin"] = np.sin(2 * np.pi * df["hora"] / 24)
    df["hora_cos"] = np.cos(2 * np.pi * df["hora"] / 24)
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)

    df["precipitacao_ma_24h"] = df["precipitacao_mm"].rolling(24, min_periods=1).mean()
    df["precipitacao_ma_168h"] = df["precipitacao_mm"].rolling(168, min_periods=1).mean()
    df["temperatura_ma_24h"] = df["temperatura_2m_C"].rolling(24, min_periods=1).mean()
    df["umidade_ma_24h"] = df["umidade_relativa_2m_pct"].rolling(24, min_periods=1).mean()

    return df


def criar_features_diarias(df):
    df = df.copy()

    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df["dia"] = df["data"].dt.day
    df["dia_do_ano"] = df["data"].dt.dayofyear
    df["dia_da_semana"] = df["data"].dt.dayofweek

    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)
    df["dia_sin"] = np.sin(2 * np.pi * df["dia_do_ano"] / 365)
    df["dia_cos"] = np.cos(2 * np.pi * df["dia_do_ano"] / 365)

    df["diferenca_temp_aparente"] = (
        df["temperatura_aparente_media_2m_C"] -
        df["temperatura_media_2m_C"]
    )

    df["precipitacao_ma_7d"] = df["precipitacao_total_mm"].rolling(7, min_periods=1).mean()
    df["precipitacao_ma_30d"] = df["precipitacao_total_mm"].rolling(30, min_periods=1).mean()
    df["precipitacao_ma_90d"] = df["precipitacao_total_mm"].rolling(90, min_periods=1).mean()

    df["anomalia_precip_7d"] = df["precipitacao_total_mm"] - df["precipitacao_ma_7d"]
    df["anomalia_precip_30d"] = df["precipitacao_total_mm"] - df["precipitacao_ma_30d"]

    df["intensidade_precipitacao"] = np.where(
        df["horas_precipitacao"] > 0,
        df["precipitacao_total_mm"] / df["horas_precipitacao"],
        0
    )

    for lag in [1, 2, 3, 7, 14, 30]:
        df[f"precipitacao_lag_{lag}d"] = df["precipitacao_total_mm"].shift(lag)

    for lag in [1, 7]:
        df[f"temperatura_lag_{lag}d"] = df["temperatura_media_2m_C"].shift(lag)

    return df

# =========================================================
# SALVAMENTO
# =========================================================

def salvar_por_ponto(df_hor, df_diario, local, tipo):
    base = f"{BASE_DATA_DIR}/{tipo}/ponto_{local}"

    os.makedirs(f"{base}/horario", exist_ok=True)
    os.makedirs(f"{base}/diario", exist_ok=True)

    df_hor.to_csv(f"{base}/horario/dados_horarios_{tipo}.csv", index=False)
    df_diario.to_csv(f"{base}/diario/dados_diarios_{tipo}.csv", index=False)

# =========================================================
# MAIN
# =========================================================

def main():
    pontos = pd.read_csv(ARQUIVO_COORDENADAS)

    print(f"Total de pontos mapeados: {len(pontos)}")
    print("=" * 60)

    for _, ponto in pontos.iterrows():

        local = ponto["local"]
        lat = ponto["latitude"]
        lon = ponto["longitude"]

        caminho_hist = f"data/historico/ponto_{local}"
        caminho_fore = f"data/forecast/ponto_{local}"

        if os.path.exists(caminho_hist) and os.path.exists(caminho_fore):
            print(f"⏭ Ponto {local} já processado. Pulando...")
            continue

        print(f"\nProcessando ponto: {local} ({lat}, {lon})")

        dados_hist = baixar_dados_historicos(lat, lon)
        dados_fore = baixar_dados_forecast(lat, lon)

        df_hor_hist, df_diario_hist = processar_dados(dados_hist, "historico", local)
        df_hor_fore, df_diario_fore = processar_dados(dados_fore, "forecast", local)

        df_hor_hist = criar_features_horarias(df_hor_hist)
        df_diario_hist = criar_features_diarias(df_diario_hist)

        df_hor_fore = criar_features_horarias(df_hor_fore)
        df_diario_fore = criar_features_diarias(df_diario_fore)

        salvar_por_ponto(df_hor_hist, df_diario_hist, local, "historico")
        salvar_por_ponto(df_hor_fore, df_diario_fore, local, "forecast")

        print(f"Ponto {local} concluído.")
        print(f"Aguardando {ESPERA_ENTRE_PONTOS}s...\n")

        time.sleep(ESPERA_ENTRE_PONTOS)

    print("\nTodos os pontos processados com sucesso!")


if __name__ == "__main__":
    main()