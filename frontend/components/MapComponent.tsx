import React, { useEffect, useRef } from 'react';
import type { SensorData } from '../types.ts';
import { getWeatherData, getLocationName } from '../services/weather/openWeather.service.ts';

declare const L: any;

type RouteStopType = 'start' | 'via' | 'destination';

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
}

const MapComponent: React.FC<MapComponentProps> = ({
  sensors,
  className,
  userLocation,
  routePath,
  routeStops,
  highlightedSensors
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const mapInitRef = useRef(false);

  const markerByIdRef = useRef<Record<string, any>>({});
  const riskCacheRef = useRef<Record<string, any>>({});
  const tempMarkerRef = useRef<any>(null);
  const userMarkerRef = useRef<any>(null);

  /* =======================
     ICON HELPERS
  ======================= */

  const getMarkerIcon = (level: string) => {
    let color = 'bg-slate-400';
    let pulse = '';

    if (level === 'Alto') {
      color = 'bg-red-600';
      pulse =
        '<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>';
    } else if (level === 'Moderado') {
      color = 'bg-yellow-500';
    } else if (level === 'Baixo') {
      color = 'bg-green-500';
    }

    return L.divIcon({
      className: 'bg-transparent border-none',
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
      className: 'bg-transparent border-none',
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
      className: 'bg-transparent border-none',
      html: `
        <div class="relative flex items-center justify-center w-5 h-5">
          <span class="relative inline-flex rounded-full h-4 w-4 bg-slate-500 border-2 border-white shadow-lg"></span>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

  /* =======================
     POPUP HELPERS
  ======================= */

  const popupLoading = (label: string) => `
    <div class="flex items-center gap-2 p-2">
      <div class="w-4 h-4 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin"></div>
      <span class="text-sm font-semibold text-slate-600">${label}</span>
    </div>
  `;

  const popupWeatherOnly = (title: string, weather: any) => `
    <div class="font-sans p-2 min-w-[200px]">
      <h3 class="font-bold text-base border-b pb-1 mb-2">${title}</h3>
      <div class="text-sm">
        Temperatura: ${weather.current.temp}°C<br/>
        Umidade: ${weather.current.humidity}%<br/>
        Vento: ${weather.current.wind_speed} km/h
      </div>
    </div>
  `;

  const popupWeatherWithRisk = (title: string, weather: any, risk: any) => `
    <div class="font-sans p-2 min-w-[200px]">
      <h3 class="font-bold text-base border-b pb-1 mb-2">${title}</h3>
      <div class="text-sm">
        Temperatura: ${weather.current.temp}°C<br/>
        Umidade: ${weather.current.humidity}%<br/>
        Vento: ${weather.current.wind_speed} km/h
      </div>
      <div class="mt-3 pt-2 border-t text-center font-bold">
        Risco ${risk.nivel}
      </div>
      <div class="text-xs text-center text-slate-500">
        Confiança: ${risk.confianca ?? '—'}
      </div>
    </div>
  `;

  /* =======================
     MAP INIT + CLICK LIVRE
  ======================= */

  useEffect(() => {
    if (!mapContainerRef.current || mapInitRef.current) return;

    mapRef.current = L.map(mapContainerRef.current, {
      attributionControl: false,
      zoomControl: true,
      tap: false,
    }).setView([-16.6869, -49.2648], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(mapRef.current);
    mapRef.current.keyboard.disable();

    mapRef.current.on('click', async (e: any) => {
      if (tempMarkerRef.current) {
        tempMarkerRef.current.remove();
        tempMarkerRef.current = null;
      }

      const marker = L.marker([e.latlng.lat, e.latlng.lng], {
        icon: getTempIcon(),
        zIndexOffset: 700,
      }).addTo(mapRef.current);

      tempMarkerRef.current = marker;
      marker.bindPopup(popupLoading('Buscando clima...')).openPopup();

      try {
        const weather = await getWeatherData(e.latlng.lat, e.latlng.lng);
        const location = await getLocationName(e.latlng.lat, e.latlng.lng);
        marker.setPopupContent(popupWeatherOnly(location, weather));
      } catch {
        marker.setPopupContent('<div class="p-2 text-red-600">Erro ao buscar clima</div>');
      }
    });

    mapInitRef.current = true;
  }, []);

  /* =======================
     SENSORS / MARKERS
  ======================= */

  useEffect(() => {
    if (!mapRef.current) return;

    sensors.forEach(sensor => {
      let marker = markerByIdRef.current[sensor.id];

      if (!marker) {
        marker = L.marker([sensor.coords.lat, sensor.coords.lon], {
          icon: getMarkerIcon('Nenhum'),
          zIndexOffset: 800,
          interactive: true,
        }).addTo(mapRef.current);

        markerByIdRef.current[sensor.id] = marker;
      }

      marker.off('click');
      marker.on('click', async (evt: any) => {
        L.DomEvent.stop(evt);

        if (tempMarkerRef.current) {
          tempMarkerRef.current.remove();
          tempMarkerRef.current = null;
        }

        marker.bindPopup(popupLoading('Carregando informações...')).openPopup();

        try {
          const weather = await getWeatherData(sensor.coords.lat, sensor.coords.lon);

          const cached = riskCacheRef.current[sensor.id];
          if (cached) {
            marker.setIcon(getMarkerIcon(cached.nivel));
            marker.setPopupContent(popupWeatherWithRisk(sensor.location, weather, cached));
            return;
          }

          const res = await fetch(
            `${import.meta.env.VITE_API_BASE_URL}/points/${sensor.id}/risk`
          );

          if (res.ok) {
            const risk = await res.json();
            riskCacheRef.current[sensor.id] = risk;
            marker.setIcon(getMarkerIcon(risk.nivel));
            marker.setPopupContent(popupWeatherWithRisk(sensor.location, weather, risk));
          } else {
            marker.setPopupContent(popupWeatherOnly(sensor.location, weather));
          }
        } catch {
          marker.setPopupContent('<div class="p-2 text-red-600">Erro ao carregar dados</div>');
        }
      });
    });
  }, [sensors]);

  /* =======================
     USER LOCATION
  ======================= */

  useEffect(() => {
    if (!mapRef.current) return;

    if (userMarkerRef.current) {
      userMarkerRef.current.remove();
      userMarkerRef.current = null;
    }

    if (userLocation) {
      userMarkerRef.current = L.marker(
        [userLocation.lat, userLocation.lon],
        { icon: getUserIcon(), zIndexOffset: 1000 }
      ).addTo(mapRef.current);
    }
  }, [userLocation]);

  /* =======================
     RENDER
  ======================= */

  return (
    <div className="relative h-full w-full">
      <div
        ref={mapContainerRef}
        className={className || 'h-[420px] md:h-[520px] w-full rounded-2xl shadow-md'}
      />
    </div>
  );
};

export default MapComponent;
