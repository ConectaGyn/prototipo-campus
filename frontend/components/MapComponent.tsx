import React, { useEffect, useRef } from "react";
import type { SensorData } from "../types.ts";
import {
  getWeatherData,
  getLocationName,
} from "../services/weather/openWeather.service.ts";
import type { SurfaceEnvelope } from "../domains/surface/types.ts";

declare const L: any;

type RouteStopType = "start" | "via" | "destination";

interface RouteStop {
  coords: { lat: number; lon: number };
  label: string;
  kind: RouteStopType;
}

interface MapComponentProps {
  sensors: SensorData[];
  className?: string;
  userLocation: { lat: number; lon: number } | null;
  routePath?: { lat: number; lon: number }[];
  routeStops?: RouteStop[];
  highlightedSensors?: SensorData[];
  surface?: SurfaceEnvelope | null;
  municipalityGeoJson?: Record<string, unknown> | null;
}

const MapComponent: React.FC<MapComponentProps> = ({
  sensors,
  className,
  userLocation,
  surface,
  municipalityGeoJson,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const mapInitRef = useRef(false);

  const markerByIdRef = useRef<Record<string, any>>({});
  const tempMarkerRef = useRef<any>(null);
  const userMarkerRef = useRef<any>(null);
  const mapClickHandlerRef = useRef<((e: any) => void) | null>(null);

  const surfaceLayerRef = useRef<any>(null);
  const municipalityLayerRef = useRef<any>(null);
  const municipalityBoundsRef = useRef<any>(null);
  const hasAutoFittedRef = useRef(false);
  const surfaceRangeRef = useRef<{ min: number; max: number } | null>(null);

  const getMarkerIcon = (level?: string | null) => {
    let color = "bg-slate-400";
    let pulse = "";

    if (level === "Alto" || level === "Muito Alto") {
      color = "bg-red-600";
      pulse =
        '<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>';
    } else if (level === "Moderado") {
      color = "bg-yellow-500";
    } else if (level === "Baixo") {
      color = "bg-green-500";
    }

    return L.divIcon({
      className: "bg-transparent border-none",
      html: `
        <div class="relative flex items-center justify-center w-6 h-6">
          ${pulse}
          <span class="relative inline-flex rounded-full h-4 w-4 ${color} border-2 border-white shadow-md"></span>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -12],
    });
  };

  const getUserIcon = () =>
    L.divIcon({
      className: "bg-transparent border-none",
      html: `
        <div class="relative flex items-center justify-center w-6 h-6">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-300 opacity-50"></span>
          <span class="relative inline-flex rounded-full h-4 w-4 bg-blue-600 border-2 border-white shadow-lg"></span>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

  const getTempIcon = () =>
    L.divIcon({
      className: "bg-transparent border-none",
      html: `
        <div class="relative flex items-center justify-center w-5 h-5">
          <span class="relative inline-flex rounded-full h-4 w-4 bg-slate-500 border-2 border-white shadow-lg"></span>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

  const getFeatureIcra = (feature: any): number => {
    const relativeRaw = feature?.properties?.risk_value_relative;
    if (relativeRaw !== undefined && relativeRaw !== null) {
      const rel = Number(relativeRaw);
      if (Number.isFinite(rel)) {
        return Math.max(0, Math.min(1, rel));
      }
    }

    const raw = feature?.properties?.icra ?? feature?.properties?.risk_value ?? 0;
    const v = Number(raw);
    if (!Number.isFinite(v)) return 0;

    const range = surfaceRangeRef.current;
    if (range && range.max > range.min) {
      const normalized = (v - range.min) / (range.max - range.min);
      return Math.max(0, Math.min(1, normalized));
    }

    return Math.max(0, Math.min(1, v));
  };

  const colorFromIcra = (icra: number): string => {
    if (icra >= 0.85) return "#991b1b";
    if (icra >= 0.7) return "#dc2626";
    if (icra >= 0.5) return "#f59e0b";
    if (icra >= 0.3) return "#84cc16";
    return "#22c55e";
  };

  const surfaceStyle = (feature: any) => {
    const icra = getFeatureIcra(feature);
    const fill = feature?.properties?.color ?? colorFromIcra(icra);
    return {
      color: "transparent",
      weight: 0,
      fillColor: fill,
      fillOpacity: 0.55,
      interactive: false,
    };
  };

  useEffect(() => {
    if (!mapContainerRef.current || mapInitRef.current) return;

    const map = L.map(mapContainerRef.current, {
      attributionControl: false,
      zoomControl: true,
      tap: false,
      preferCanvas: true,
    }).setView([-16.6869, -49.2648], 12);

    map.createPane("surfacePane");
    map.getPane("surfacePane").style.zIndex = 200;

    map.createPane("municipalityPane");
    map.getPane("municipalityPane").style.zIndex = 300;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
    map.keyboard.disable();

    const onMapClick = async (e: any) => {
      if (!mapRef.current) return;

      if (tempMarkerRef.current) {
        tempMarkerRef.current.remove();
      }

      const marker = L.marker([e.latlng.lat, e.latlng.lng], {
        icon: getTempIcon(),
        zIndexOffset: 700,
      }).addTo(map);

      tempMarkerRef.current = marker;
      marker.bindPopup("Buscando clima...").openPopup();

      try {
        const weather = await getWeatherData(e.latlng.lat, e.latlng.lng);
        const location = await getLocationName(e.latlng.lat, e.latlng.lng);

        if (!mapRef.current || tempMarkerRef.current !== marker) return;

        marker.setPopupContent(`
          <div class="p-2">
            <strong>${location}</strong><br/>
            Temp: ${weather.current.temp}°C<br/>
            Umidade: ${weather.current.humidity}%<br/>
            Vento: ${weather.current.wind_speed} km/h
          </div>
        `);
      } catch {
        if (!mapRef.current || tempMarkerRef.current !== marker) return;
        marker.setPopupContent("Erro ao buscar clima");
      }
    };

    map.on("click", onMapClick);
    mapClickHandlerRef.current = onMapClick;
    mapRef.current = map;
    mapInitRef.current = true;

    return () => {
      if (!mapRef.current) return;

      if (mapClickHandlerRef.current) {
        mapRef.current.off("click", mapClickHandlerRef.current);
      }

      if (surfaceLayerRef.current) {
        surfaceLayerRef.current.remove();
        surfaceLayerRef.current = null;
      }

      if (municipalityLayerRef.current) {
        municipalityLayerRef.current.remove();
        municipalityLayerRef.current = null;
      }

      if (tempMarkerRef.current) {
        tempMarkerRef.current.remove();
        tempMarkerRef.current = null;
      }

      if (userMarkerRef.current) {
        userMarkerRef.current.remove();
        userMarkerRef.current = null;
      }

      Object.values(markerByIdRef.current as Record<string, any>).forEach(
        (marker: any) => marker.remove()
      );
      markerByIdRef.current = {};

      mapRef.current.remove();
      mapRef.current = null;
      mapInitRef.current = false;
      mapClickHandlerRef.current = null;
      municipalityBoundsRef.current = null;
      hasAutoFittedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;

    if (surfaceLayerRef.current) {
      surfaceLayerRef.current.remove();
      surfaceLayerRef.current = null;
    }

    if (!surface?.geojson) return;

    const risks = (surface.geojson.features || [])
      .map((f: any) => Number(f?.properties?.risk_value))
      .filter((v: number) => Number.isFinite(v));

    if (risks.length > 0) {
      surfaceRangeRef.current = {
        min: Math.min(...risks),
        max: Math.max(...risks),
      };
    } else {
      surfaceRangeRef.current = null;
    }

    const layer = L.geoJSON(surface.geojson, {
      pane: "surfacePane",
      style: surfaceStyle,
      interactive: false,
    });

    layer.addTo(mapRef.current);
    surfaceLayerRef.current = layer;
  }, [surface]);

  useEffect(() => {
    if (!mapRef.current) return;

    if (municipalityLayerRef.current) {
      municipalityLayerRef.current.remove();
      municipalityLayerRef.current = null;
    }

    if (!municipalityGeoJson) return;

    const boundsLayer = L.geoJSON(municipalityGeoJson);
    municipalityBoundsRef.current = boundsLayer.getBounds();

    const outer = L.geoJSON(municipalityGeoJson, {
      pane: "municipalityPane",
      style: () => ({
        color: "#0f172a",
        weight: 6,
        opacity: 0.8,
        fillOpacity: 0,
      }),
      interactive: false,
    });

    const inner = L.geoJSON(municipalityGeoJson, {
      pane: "municipalityPane",
      style: () => ({
        color: "#22d3ee",
        weight: 3,
        opacity: 1,
        fillOpacity: 0,
      }),
      interactive: false,
    });

    const layer = L.layerGroup([outer, inner]);
    layer.addTo(mapRef.current);
    municipalityLayerRef.current = layer;
  }, [municipalityGeoJson]);

  useEffect(() => {
    if (!mapRef.current || hasAutoFittedRef.current) return;

    let targetBounds: any = null;

    if (municipalityBoundsRef.current && municipalityBoundsRef.current.isValid()) {
      targetBounds = municipalityBoundsRef.current;
    }

    if (sensors.length > 0) {
      const sensorBounds = L.latLngBounds(
        sensors.map((sensor) => [sensor.coords.lat, sensor.coords.lon])
      );

      if (sensorBounds.isValid()) {
        if (!targetBounds) {
          targetBounds = sensorBounds;
        } else {
          targetBounds = targetBounds.extend(sensorBounds);
        }
      }
    }

    if (!targetBounds || !targetBounds.isValid()) return;

    mapRef.current.fitBounds(targetBounds.pad(0.04), {
      padding: [28, 28],
      animate: false,
      maxZoom: 13,
    });

    hasAutoFittedRef.current = true;
  }, [sensors, municipalityGeoJson]);

  useEffect(() => {
    if (!mapRef.current) return;

    const nextSensorIds = new Set(sensors.map((s) => s.id));

    Object.entries(markerByIdRef.current as Record<string, any>).forEach(([id, marker]) => {
      if (!nextSensorIds.has(id)) {
        (marker as any).remove();
        delete markerByIdRef.current[id];
      }
    });

    sensors.forEach((sensor) => {
      let marker = markerByIdRef.current[sensor.id];
      const icon = getMarkerIcon(sensor.alert?.level);

      if (!marker) {
        marker = L.marker([sensor.coords.lat, sensor.coords.lon], {
          icon,
          zIndexOffset: 800,
        }).addTo(mapRef.current);
        markerByIdRef.current[sensor.id] = marker;
      } else {
        marker.setLatLng([sensor.coords.lat, sensor.coords.lon]);
        marker.setIcon(icon);
      }

      marker.off("click");

      marker.on("click", async (evt: any) => {
        L.DomEvent.stop(evt);
        marker.bindPopup("Carregando clima...").openPopup();

        try {
          const weather = await getWeatherData(sensor.coords.lat, sensor.coords.lon);

          if (!mapRef.current || markerByIdRef.current[sensor.id] !== marker) return;

          marker.setPopupContent(`
            <div class="p-2">
              <strong>${sensor.location}</strong><br/>
              Temp: ${weather.current.temp}°C<br/>
              Umidade: ${weather.current.humidity}%<br/>
              Vento: ${weather.current.wind_speed} km/h
              <hr class="my-2"/>
              <strong>Risco:</strong> ${sensor.alert?.level ?? "Indisponivel"}<br/>
              Confianca: ${sensor.alert?.confianca ?? "-"}
            </div>
          `);
        } catch {
          if (!mapRef.current || markerByIdRef.current[sensor.id] !== marker) return;
          marker.setPopupContent("Erro ao carregar dados.");
        }
      });
    });
  }, [sensors]);

  useEffect(() => {
    if (!mapRef.current) return;

    if (userMarkerRef.current) {
      userMarkerRef.current.remove();
      userMarkerRef.current = null;
    }

    if (!userLocation) return;

    userMarkerRef.current = L.marker([userLocation.lat, userLocation.lon], {
      icon: getUserIcon(),
      zIndexOffset: 1000,
    }).addTo(mapRef.current);
  }, [userLocation]);

  return (
    <div className="relative h-full w-full">
      <div
        ref={mapContainerRef}
        className={className || "h-[420px] md:h-[520px] w-full rounded-2xl shadow-md"}
      />
      <aside
        className="pointer-events-none absolute bottom-3 left-3 z-[1000] w-56 rounded-xl border border-slate-200/80 bg-white/90 p-3 shadow-lg backdrop-blur dark:border-slate-700/80 dark:bg-slate-900/85"
        aria-label="Legenda do mapa de calor"
      >
        <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">
          Legenda do Mapa de Calor
        </p>
        <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
          Escala relativa de risco territorial
        </p>

        <div className="mt-2 h-2 w-full rounded-full bg-gradient-to-r from-[#22c55e] via-[#f59e0b] to-[#991b1b]" />
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 dark:text-slate-400">
          <span>Baixo</span>
          <span>Moderado</span>
          <span>Muito Alto</span>
        </div>

        <div className="mt-2 space-y-1 text-[11px] text-slate-600 dark:text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#22c55e]" />
            <span>Menor risco relativo</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#f59e0b]" />
            <span>Risco intermediario</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#991b1b]" />
            <span>Maior risco relativo</span>
          </div>
        </div>

        <p className="mt-2 text-[10px] text-slate-500 dark:text-slate-400">
          Use a aba Analises para leitura institucional em escala absoluta.
        </p>
      </aside>
    </div>
  );
};

export default MapComponent;
