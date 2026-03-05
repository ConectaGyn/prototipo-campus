import React, { useState, useEffect, useCallback, useRef } from "react";

import type {
  WeatherData,
  RiskAlert,
  SensorData,
  CurrentWeather,
  SensorRiskLevel,
} from "./types.ts";

import type { MapPointView } from "@domains/map/types";
import type { SurfaceEnvelope } from "@domains/surface/types";

import { getCurrentWeather, getWeatherData, getLocationName } from "@services/weather";
import { getMapPoints, recomputeAllRiskNow } from "@services/map.service";
import { getSurface } from "@services/surface.service";
import { getMunicipalityGeoJson } from "@services/municipality.service";

import Header from "./components/Header.tsx";
import WeatherCard from "./components/WeatherCard.tsx";
import AlertCard from "./components/AlertCard.tsx";
import LoadingSpinner from "./components/LoadingSpinner.tsx";
import SensorCarousel from "./components/SensorCarousel.tsx";
import Tabs from "./components/Tabs.tsx";
import MapComponent from "./components/MapComponent.tsx";
import SafetyInfo from "./components/SafetyInfo.tsx";
import AnalyticsPanel from "./components/AnalyticsPanel.tsx";

import { useTheme } from "./hooks/useTheme.ts";

const GOIANIA_COORDS = {
  lat: -16.6869,
  lon: -49.2648,
};

const DEFAULT_MUNICIPALITY_ID = 1;
const WEATHER_ENRICH_BATCH_SIZE = 6;
const WEATHER_REFRESH_INTERVAL_MS = 300000;
const RISK_REFRESH_INTERVAL_MS = 10800000;

const App: React.FC = () => {
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [displayedCurrentWeather, setDisplayedCurrentWeather] =
    useState<CurrentWeather | null>(null);

  const [mapSensors, setMapSensors] = useState<SensorData[]>([]);
  const [surface, setSurface] = useState<SurfaceEnvelope | null>(null);
  const [municipalityGeoJson, setMunicipalityGeoJson] =
    useState<Record<string, unknown> | null>(null);

  const [currentCoords, setCurrentCoords] =
    useState<{ lat: number; lon: number } | null>(null);

  const [locationName, setLocationName] = useState("");
  const [riskAlert, setRiskAlert] = useState<RiskAlert | null>(null);
  const [riskSnapshotTimestamp, setRiskSnapshotTimestamp] = useState<string | null>(null);
  const [riskSnapshotValidUntil, setRiskSnapshotValidUntil] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRiskRecomputing, setIsRiskRecomputing] = useState(false);

  const [isSoundEnabled, setIsSoundEnabled] = useState<boolean>(() => {
    const stored = localStorage.getItem("soundEnabled");
    return stored === null ? true : stored === "true";
  });

  const isFetchingRef = useRef(false);
  const isRiskFetchingRef = useRef(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    localStorage.setItem("soundEnabled", String(isSoundEnabled));
  }, [isSoundEnabled]);

  const toggleSound = () => setIsSoundEnabled((prev) => !prev);

  const fetchWeatherAndLocation = useCallback(
    async (lat: number, lon: number, locationError: string | null) => {
      try {
        const [weather, locName] = await Promise.all([
          getWeatherData(lat, lon),
          getLocationName(lat, lon),
        ]);

        setWeatherData(weather);
        setDisplayedCurrentWeather(weather.current);
        setCurrentCoords({ lat, lon });
        setLocationName(locName);

        if (locationError) setError(locationError);
        else setError(null);
      } catch {
        setError("Erro ao buscar dados climaticos.");
        setWeatherData(null);
        setDisplayedCurrentWeather(null);
      }
    },
    []
  );

  const updateUserLocationData = useCallback(
    async (initial = false) => {
      if (isFetchingRef.current) return;
      isFetchingRef.current = true;

      if (initial) {
        setLoading(true);
        setError(null);
      }

      setIsRefreshing(true);

      const finalize = () => {
        setLoading(false);
        setIsRefreshing(false);
        isFetchingRef.current = false;
      };

      const fetchByCoords = async (
        lat: number,
        lon: number,
        err: string | null = null
      ) => {
        await fetchWeatherAndLocation(lat, lon, err);
        finalize();
      };

      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => fetchByCoords(pos.coords.latitude, pos.coords.longitude),
          () =>
            fetchByCoords(
              GOIANIA_COORDS.lat,
              GOIANIA_COORDS.lon,
              "Nao foi possivel obter sua localizacao. Exibindo Goiania."
            ),
          { enableHighAccuracy: true, timeout: 7000 }
        );
      } else {
        fetchByCoords(
          GOIANIA_COORDS.lat,
          GOIANIA_COORDS.lon,
          "Geolocalizacao nao suportada."
        );
      }
    },
    [fetchWeatherAndLocation]
  );

  const mapPointToSensor = useCallback((risk: MapPointView): SensorData => {
    const level = risk.nivel_risco ?? risk.nivel_risco_relativo;
    return {
      id: risk.id,
      location: risk.nome,
      coords: {
        lat: risk.latitude,
        lon: risk.longitude,
      },
      temp: null,
      humidity: null,
      wind_speed: null,
      feels_like: null,
      pressure: null,
      rain: null,
      alert: level
        ? {
            level: level as SensorRiskLevel,
            message: `Risco ${level}`,
            color: undefined,
            icra: risk.icra ?? undefined,
            confianca: risk.confianca ?? undefined,
          }
        : null,
    };
  }, []);

  const enrichSensorsWithWeather = useCallback(
    async (sensors: SensorData[]): Promise<SensorData[]> => {
      if (sensors.length === 0) return sensors;

      const enriched = [...sensors];

      for (let i = 0; i < enriched.length; i += WEATHER_ENRICH_BATCH_SIZE) {
        const batch = enriched.slice(i, i + WEATHER_ENRICH_BATCH_SIZE);
        const results = await Promise.allSettled(
          batch.map((sensor) =>
            getCurrentWeather(sensor.coords.lat, sensor.coords.lon)
          )
        );

        results.forEach((result, idx) => {
          const targetIndex = i + idx;
          if (result.status !== "fulfilled") return;

          const current = result.value;
          enriched[targetIndex] = {
            ...enriched[targetIndex],
            temp: current.temp,
            humidity: current.humidity,
            wind_speed: current.wind_speed,
            feels_like: current.feels_like,
            pressure: current.pressure,
            rain: current.rain,
          };
        });

        if (i + WEATHER_ENRICH_BATCH_SIZE < enriched.length) {
          await new Promise((resolve) => setTimeout(resolve, 150));
        }
      }

      return enriched;
    },
    []
  );

  const refreshSensorsWeatherOnly = useCallback(async () => {
    const sensorsSnapshot = mapSensors;
    if (sensorsSnapshot.length === 0) return;

    const weatherById = new Map<
      string,
      Awaited<ReturnType<typeof getCurrentWeather>>
    >();

    for (let i = 0; i < sensorsSnapshot.length; i += WEATHER_ENRICH_BATCH_SIZE) {
      const batch = sensorsSnapshot.slice(i, i + WEATHER_ENRICH_BATCH_SIZE);
      const results = await Promise.allSettled(
        batch.map((sensor) =>
          getCurrentWeather(sensor.coords.lat, sensor.coords.lon)
        )
      );

      results.forEach((result, idx) => {
        if (result.status !== "fulfilled") return;
        weatherById.set(batch[idx].id, result.value);
      });

      if (i + WEATHER_ENRICH_BATCH_SIZE < sensorsSnapshot.length) {
        await new Promise((resolve) => setTimeout(resolve, 150));
      }
    }

    if (weatherById.size === 0) return;

    setMapSensors((prev) =>
      prev.map((sensor) => {
        const current = weatherById.get(sensor.id);
        if (!current) return sensor;
        return {
          ...sensor,
          temp: current.temp,
          humidity: current.humidity,
          wind_speed: current.wind_speed,
          feels_like: current.feels_like,
          pressure: current.pressure,
          rain: current.rain,
        };
      })
    );
  }, [mapSensors]);

  const refreshRiskData = useCallback(
    async (initial = false) => {
      if (isRiskFetchingRef.current) return;
      isRiskFetchingRef.current = true;

      try {
        if (initial) {
          setLoading(true);
          setError(null);
        }

        const [mapPointsResult, surfaceResult, geoJsonResult] = await Promise.allSettled([
          getMapPoints(DEFAULT_MUNICIPALITY_ID),
          getSurface(DEFAULT_MUNICIPALITY_ID),
          municipalityGeoJson
            ? Promise.resolve(municipalityGeoJson)
            : getMunicipalityGeoJson(DEFAULT_MUNICIPALITY_ID),
        ]);

        if (mapPointsResult.status !== "fulfilled") {
          throw mapPointsResult.reason;
        }

        const baseSensors = mapPointsResult.value.pontos
          .filter((point) => point.ativo)
          .map(mapPointToSensor);

        setRiskSnapshotTimestamp(mapPointsResult.value.snapshot_timestamp);
        setRiskSnapshotValidUntil(mapPointsResult.value.snapshot_valid_until);

        const sensorsWithWeather = await enrichSensorsWithWeather(baseSensors);
        setMapSensors(sensorsWithWeather);

        if (surfaceResult.status === "fulfilled") {
          setSurface(surfaceResult.value);
        } else {
          console.warn("Superficie nao carregada:", surfaceResult.reason);
        }

        if (geoJsonResult.status === "fulfilled") {
          setMunicipalityGeoJson(geoJsonResult.value);
        } else {
          console.warn("GeoJSON do municipio nao carregado:", geoJsonResult.reason);
        }
      } catch (err) {
        console.error("Erro ao carregar dados de risco:", err);
        setError("Erro ao atualizar dados de risco.");
      } finally {
        if (initial) {
          setLoading(false);
        }
        isRiskFetchingRef.current = false;
      }
    },
    [enrichSensorsWithWeather, mapPointToSensor, municipalityGeoJson]
  );

  const runManualRiskRecompute = useCallback(async () => {
    if (isRiskRecomputing) return;
    setIsRiskRecomputing(true);
    setIsRefreshing(true);
    try {
      await recomputeAllRiskNow();
      await refreshRiskData(false);
    } catch (err) {
      console.error("Erro ao recalcular risco global:", err);
      setError("Falha ao recalcular risco global.");
    } finally {
      setIsRiskRecomputing(false);
      setIsRefreshing(false);
    }
  }, [isRiskRecomputing, refreshRiskData]);

  useEffect(() => {
    void refreshRiskData(true);
  }, [refreshRiskData]);

  useEffect(() => {
    updateUserLocationData(true);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      void updateUserLocationData(false);
    }, WEATHER_REFRESH_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [updateUserLocationData]);

  useEffect(() => {
    const interval = setInterval(() => {
      void refreshSensorsWeatherOnly();
    }, WEATHER_REFRESH_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [refreshSensorsWeatherOnly]);

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | undefined;
    const msUntilNextCycle =
      RISK_REFRESH_INTERVAL_MS - (Date.now() % RISK_REFRESH_INTERVAL_MS);

    const timeoutId = setTimeout(() => {
      void refreshRiskData(false);
      intervalId = setInterval(() => {
        void refreshRiskData(false);
      }, RISK_REFRESH_INTERVAL_MS);
    }, msUntilNextCycle);

    return () => {
      clearTimeout(timeoutId);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [refreshRiskData]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error && !weatherData) {
    return <div className="p-6 text-red-600">{error}</div>;
  }

  const tabs =
    weatherData && displayedCurrentWeather
      ? [
          {
            label: "Monitoramento",
            content: (
              <div className="flex flex-col gap-4 px-3 pb-6 max-w-screen-2xl mx-auto">
                {riskAlert && (
                  <div className="max-w-3xl">
                    <AlertCard alert={riskAlert} soundEnabled={isSoundEnabled} />
                  </div>
                )}

                <div className="relative z-0 w-full">
                  <MapComponent
                    sensors={mapSensors}
                    surface={surface}
                    municipalityGeoJson={municipalityGeoJson}
                    userLocation={currentCoords}
                    className="h-[60vh] md:h-[65vh]"
                  />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
                  <div className="lg:col-span-2">
                    <SensorCarousel sensors={mapSensors} />
                  </div>
                  <div className="lg:col-span-1">
                    <WeatherCard current={displayedCurrentWeather} />
                  </div>
                </div>
              </div>
            ),
          },
          {
            label: "Seguranca",
            content: <SafetyInfo userCoords={currentCoords} sensors={mapSensors} />,
          },
          {
            label: "Analises",
            content: <AnalyticsPanel municipalityId={DEFAULT_MUNICIPALITY_ID} />,
          },
        ]
      : [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 px-3 sm:px-4 lg:px-6">
      <Header
        onRefresh={() => {
          void updateUserLocationData(true);
          void refreshRiskData(false);
        }}
        onRecomputeRiskNow={() => {
          void runManualRiskRecompute();
        }}
        isRefreshing={isRefreshing}
        isRiskRecomputing={isRiskRecomputing}
        theme={theme}
        toggleTheme={toggleTheme}
        isSoundEnabled={isSoundEnabled}
        toggleSound={toggleSound}
        riskSnapshotTimestamp={riskSnapshotTimestamp}
        riskSnapshotValidUntil={riskSnapshotValidUntil}
      />

      <div className="mt-4">
        <Tabs tabs={tabs} />
      </div>
    </div>
  );
};

export default App;
