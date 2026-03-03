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

import { getWeatherData, getLocationName, getCurrentWeather } from "@services/weather";
import { getMapPoints, getPointRisk } from "@services/map.service";
import { getSurface } from "@services/surface.service";
import { getMunicipalityGeoJson } from "@services/municipality.service";
import { getPoints, type PointItem } from "@services/points.service";

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
const RISK_ENRICH_BATCH_SIZE = 8;
const WEATHER_ENRICH_BATCH_SIZE = 5;

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

  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isSoundEnabled, setIsSoundEnabled] = useState<boolean>(() => {
    const stored = localStorage.getItem("soundEnabled");
    return stored === null ? true : stored === "true";
  });

  const isFetchingRef = useRef(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    localStorage.setItem("soundEnabled", String(isSoundEnabled));
  }, [isSoundEnabled]);

  const toggleSound = () => setIsSoundEnabled((prev) => !prev);

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
          await new Promise((resolve) => setTimeout(resolve, 250));
        }
      }

      return enriched;
    },
    []
  );

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

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);

        const [pointsResult, mapPointsResult, surfaceResult, geoJsonResult] =
          await Promise.allSettled([
            getPoints(),
            getMapPoints(),
            getSurface(DEFAULT_MUNICIPALITY_ID),
            getMunicipalityGeoJson(DEFAULT_MUNICIPALITY_ID),
          ]);

        const allPoints =
          pointsResult.status === "fulfilled" ? pointsResult.value : [];
        const mapPoints =
          mapPointsResult.status === "fulfilled" ? mapPointsResult.value.pontos : [];

        const riskByPointId = new Map<string, MapPointView>(
          mapPoints.map((item) => [item.id, item])
        );

        const converted: SensorData[] = allPoints
          .filter(
            (point: PointItem) =>
              point.active &&
              (point.municipality_id === DEFAULT_MUNICIPALITY_ID ||
                point.municipality_id === null)
          )
          .map((point: PointItem) => {
            const risk = riskByPointId.get(point.id);
            const level = risk?.nivel_risco_relativo ?? risk?.nivel_risco;

            return {
              id: point.id,
              location: point.name,
              coords: {
                lat: point.latitude,
                lon: point.longitude,
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
                    icra: risk?.icra ?? undefined,
                    confianca: risk?.confianca ?? undefined,
                  }
                : null,
            };
          });

        const sensorsWithWeather = await enrichSensorsWithWeather(converted);
        setMapSensors(sensorsWithWeather);

        const missingRiskIds = converted
          .filter((sensor) => !sensor.alert)
          .map((sensor) => sensor.id);

        if (missingRiskIds.length > 0) {
          const resolvedRiskById = new Map<string, Awaited<ReturnType<typeof getPointRisk>>>();

          for (let i = 0; i < missingRiskIds.length; i += RISK_ENRICH_BATCH_SIZE) {
            const batch = missingRiskIds.slice(i, i + RISK_ENRICH_BATCH_SIZE);
            const batchResults = await Promise.allSettled(
              batch.map((pointId) => getPointRisk(pointId))
            );

            batchResults.forEach((result) => {
              if (result.status === "fulfilled") {
                resolvedRiskById.set(result.value.point_id, result.value);
              }
            });
          }

          if (resolvedRiskById.size > 0) {
            setMapSensors((prev) =>
              prev.map((sensor) => {
                if (sensor.alert) return sensor;

                const risk = resolvedRiskById.get(sensor.id);
                if (!risk) return sensor;

                const level = risk.nivel_risco_relativo ?? risk.nivel_risco;
                return {
                  ...sensor,
                  alert: {
                    level: level as SensorRiskLevel,
                    message: `Risco ${level}`,
                    color: undefined,
                    icra: risk.icra,
                    confianca: risk.confianca,
                  },
                };
              })
            );
          }
        }

        if (surfaceResult.status === "fulfilled") {
          setSurface(surfaceResult.value);
        } else {
          setSurface(null);
          console.warn("Superficie nao carregada:", surfaceResult.reason);
        }

        if (geoJsonResult.status === "fulfilled") {
          setMunicipalityGeoJson(geoJsonResult.value);
        } else {
          setMunicipalityGeoJson(null);
          console.warn("GeoJSON do municipio nao carregado:", geoJsonResult.reason);
        }

        if (pointsResult.status !== "fulfilled") {
          throw pointsResult.reason;
        }
      } catch (err) {
        console.error("Erro ao carregar dados iniciais:", err);
        setError("Erro ao carregar dados do monitoramento.");
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, [enrichSensorsWithWeather]);

  useEffect(() => {
    updateUserLocationData(true);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      updateUserLocationData(false);
    }, 300000);

    return () => clearInterval(interval);
  }, [updateUserLocationData]);

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
        onRefresh={() => updateUserLocationData(true)}
        isRefreshing={isRefreshing}
        theme={theme}
        toggleTheme={toggleTheme}
        isSoundEnabled={isSoundEnabled}
        toggleSound={toggleSound}
      />

      <div className="mt-4">
        <Tabs tabs={tabs} />
      </div>
    </div>
  );
};

export default App;
