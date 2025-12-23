import React, { useEffect, useRef } from 'react';
import type { SensorData } from '../types.ts';
import { getWeatherData, getLocationName } from '../services/weatherService.ts';

// Declara o objeto mapboxgl para o TypeScript, carregado via script global.
declare const mapboxgl: any;

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
  highlightedSensors,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const mapLoadedRef = useRef(false);
  const markersRef = useRef<any[]>([]);
  const routeMarkersRef = useRef<any[]>([]);
  const userMarkerRef = useRef<any>(null);
  const tempMarkerRef = useRef<any>(null);

  const createDotElement = (options: { color: string; size?: number; borderColor?: string; shadow?: string }) => {
    const { color, size = 12, borderColor = '#ffffff', shadow } = options;
    const el = document.createElement('div');
    el.style.width = `${size}px`;
    el.style.height = `${size}px`;
    el.style.borderRadius = '50%';
    el.style.background = color;
    el.style.border = `2px solid ${borderColor}`;
    el.style.boxShadow = shadow || '0 2px 6px rgba(0,0,0,0.25)';
    return el;
  };

  const createRouteMarkerElement = (label: string, color: string) => {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.alignItems = 'center';
    container.style.gap = '4px';

    const tag = document.createElement('span');
    tag.textContent = label;
    tag.style.fontSize = '10px';
    tag.style.fontWeight = '600';
    tag.style.background = 'rgba(255,255,255,0.9)';
    tag.style.color = '#475569';
    tag.style.padding = '2px 4px';
    tag.style.borderRadius = '6px';
    container.appendChild(tag);

    const dot = createDotElement({
      color,
      size: 10,
      borderColor: '#ffffff',
      shadow: '0 2px 8px rgba(0,0,0,0.35)',
    });
    container.appendChild(dot);

    return container;
  };

  useEffect(() => {
    if (!mapContainerRef.current || typeof mapboxgl === 'undefined') return;

    const token = import.meta.env.VITE_MAPBOX_TOKEN;
    if (!token) {
      console.error('Mapbox token nao configurado. Defina VITE_MAPBOX_TOKEN no .env.local.');
      return;
    }

    if (!mapRef.current) {
      mapboxgl.accessToken = token;
      mapRef.current = new mapboxgl.Map({
        container: mapContainerRef.current,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [-49.2648, -16.6869],
        zoom: 12,
        attributionControl: false,
      });

      mapRef.current.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), 'top-right');
      mapRef.current.on('load', () => {
        mapLoadedRef.current = true;
      });

      mapRef.current.on('click', async (event: any) => {
        const { lng, lat } = event.lngLat;

        if (tempMarkerRef.current) {
          tempMarkerRef.current.remove();
          tempMarkerRef.current = null;
        }

        const loadingContent = `
          <div style="display:flex;align-items:center;gap:8px;padding:6px 8px;font-family:sans-serif;">
            <div style="width:14px;height:14px;border:2px solid #0891b2;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;"></div>
            <span style="font-size:12px;color:#475569;font-weight:600;">Buscando dados...</span>
          </div>
        `;

        const markerEl = createDotElement({ color: '#64748b', size: 12, borderColor: '#ffffff' });
        const marker = new mapboxgl.Marker({ element: markerEl }).setLngLat([lng, lat]);

        const popup = new mapboxgl.Popup({ offset: 12 }).setHTML(loadingContent);
        marker.setPopup(popup).addTo(mapRef.current).togglePopup();
        popup.on('close', () => {
          marker.remove();
          if (tempMarkerRef.current === marker) {
            tempMarkerRef.current = null;
          }
        });

        tempMarkerRef.current = marker;

        try {
          const [weatherData, locName] = await Promise.all([
            getWeatherData(lat, lng),
            getLocationName(lat, lng),
          ]);

          const weather = weatherData.current;
          const popupContent = `
            <div class="font-sans p-1 min-w-[160px]">
              <h3 class="font-bold text-base text-slate-800 border-b pb-1 mb-2">${locName}</h3>
              <div class="space-y-1 text-sm text-slate-600">
                <div class="flex items-center gap-2 mb-2">
                  <img src="https://openweathermap.org/img/wn/${weather.weather[0].icon}.png" alt="${weather.weather[0].description}" class="w-8 h-8 -my-2" />
                  <span class="capitalize font-semibold text-cyan-700">${weather.weather[0].description}</span>
                </div>
                <div class="flex justify-between"><span>Temperatura:</span> <span class="font-semibold text-slate-800">${weather.temp.toFixed(1)}C</span></div>
                <div class="flex justify-between"><span>Sensacao:</span> <span class="font-semibold">${weather.feels_like.toFixed(1)}C</span></div>
                <div class="flex justify-between"><span>Umidade:</span> <span class="font-semibold">${weather.humidity}%</span></div>
                <div class="flex justify-between"><span>Vento:</span> <span class="font-semibold">${Math.round(weather.wind_speed)} km/h</span></div>
              </div>
              <div class="mt-2 pt-1 text-xs text-slate-400 text-center italic">
                Dados em tempo real
              </div>
            </div>
          `;

          if (tempMarkerRef.current === marker) {
            popup.setHTML(popupContent);
          }
        } catch (error) {
          console.error('Erro ao buscar dados do ponto:', error);
          if (tempMarkerRef.current === marker) {
            popup.setHTML(`
              <div class="p-2 font-sans text-sm text-red-600 font-bold">
                Nao foi possivel carregar os dados deste local.
              </div>
            `);
          }
        }
      });
    }

    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    sensors.forEach(sensor => {
      const riskLevel = sensor.alert?.level || 'Nenhum';
      const color = riskLevel === 'Alto' ? '#dc2626' : riskLevel === 'Moderado' ? '#f59e0b' : '#16a34a';

      const popupContent = `
        <div class="font-sans p-1 min-w-[150px]">
          <h3 class="font-bold text-base text-slate-800 border-b pb-1 mb-2">${sensor.location}</h3>
          <div class="space-y-1 text-sm text-slate-600">
            <div class="flex justify-between"><span>Temp:</span> <span class="font-semibold">${sensor.temp.toFixed(1)}C</span></div>
            <div class="flex justify-between"><span>Umid:</span> <span class="font-semibold">${Math.round(sensor.humidity)}%</span></div>
            <div class="flex justify-between"><span>Vento:</span> <span class="font-semibold">${Math.round(sensor.wind_speed)} km/h</span></div>
            ${riskLevel !== 'Nenhum'
              ? `<div class="mt-2 pt-2 border-t font-bold text-center ${riskLevel === 'Alto' ? 'text-red-600' : 'text-yellow-600'}">Risco ${riskLevel}</div>`
              : '<div class="mt-2 pt-2 border-t font-bold text-center text-green-600">Normal</div>'
            }
          </div>
        </div>
      `;

      const markerEl = createDotElement({ color, size: 12, borderColor: '#ffffff' });
      markerEl.title = `Sensor em ${sensor.location} - Risco ${riskLevel}`;

      const marker = new mapboxgl.Marker({ element: markerEl })
        .setLngLat([sensor.coords.lon, sensor.coords.lat])
        .setPopup(new mapboxgl.Popup({ offset: 12 }).setHTML(popupContent))
        .addTo(mapRef.current);

      markersRef.current.push(marker);
    });

    if (userMarkerRef.current) {
      userMarkerRef.current.remove();
      userMarkerRef.current = null;
    }

    if (userLocation) {
      const userEl = createDotElement({
        color: '#2563eb',
        size: 12,
        borderColor: '#ffffff',
        shadow: '0 0 0 6px rgba(59,130,246,0.35)',
      });
      userEl.title = 'Sua localizacao';

      userMarkerRef.current = new mapboxgl.Marker({ element: userEl, anchor: 'center' })
        .setLngLat([userLocation.lon, userLocation.lat])
        .setPopup(new mapboxgl.Popup({ offset: 12 }).setHTML('<div class="font-sans font-bold text-slate-800 p-1">Voce esta aqui</div>'))
        .addTo(mapRef.current);
    }
  }, [sensors, userLocation]);

  useEffect(() => {
    if (!mapRef.current || typeof mapboxgl === 'undefined') return;
    const mapInstance = mapRef.current;

    const clearRouteLayers = () => {
      if (mapInstance.getLayer('route-line-layer')) {
        mapInstance.removeLayer('route-line-layer');
      }
      if (mapInstance.getSource('route-line')) {
        mapInstance.removeSource('route-line');
      }
    };

    const clearHighlightLayers = () => {
      if (mapInstance.getLayer('highlighted-sensors-layer')) {
        mapInstance.removeLayer('highlighted-sensors-layer');
      }
      if (mapInstance.getSource('highlighted-sensors')) {
        mapInstance.removeSource('highlighted-sensors');
      }
    };

    const updateRouteAndHighlight = () => {
      clearRouteLayers();
      clearHighlightLayers();

      routeMarkersRef.current.forEach(marker => marker.remove());
      routeMarkersRef.current = [];

      if (routePath && routePath.length > 1) {
        mapInstance.addSource('route-line', {
          type: 'geojson',
          data: {
            type: 'Feature',
            geometry: {
              type: 'LineString',
              coordinates: routePath.map(point => [point.lon, point.lat]),
            },
          },
        });

        mapInstance.addLayer({
          id: 'route-line-layer',
          type: 'line',
          source: 'route-line',
          paint: {
            'line-color': '#06b6d4',
            'line-width': 4,
            'line-opacity': 0.85,
            'line-dasharray': routePath.length > 2 ? [2, 3] : [1, 0],
          },
        });

        const bounds = new mapboxgl.LngLatBounds();
        routePath.forEach(point => bounds.extend([point.lon, point.lat]));
        mapInstance.fitBounds(bounds, { padding: 30 });
      }

      if (routeStops && routeStops.length) {
        routeStops.forEach(stop => {
          const color = stop.kind === 'start' ? '#2563eb' : stop.kind === 'via' ? '#7c3aed' : '#059669';
          const label = stop.kind === 'start' ? 'Origem' : stop.kind === 'via' ? 'Desvio' : 'Destino';
          const markerEl = createRouteMarkerElement(label, color);
          const marker = new mapboxgl.Marker({ element: markerEl })
            .setLngLat([stop.coords.lon, stop.coords.lat])
            .setPopup(new mapboxgl.Popup({ offset: 12 }).setHTML(`<div class="font-sans text-sm font-semibold">${stop.label}</div>`))
            .addTo(mapInstance);
          routeMarkersRef.current.push(marker);
        });

        if (!routePath || routePath.length <= 1) {
          const bounds = new mapboxgl.LngLatBounds();
          routeStops.forEach(stop => bounds.extend([stop.coords.lon, stop.coords.lat]));
          if (!bounds.isEmpty()) {
            mapInstance.fitBounds(bounds, { padding: 30 });
          }
        }
      }

      if (highlightedSensors && highlightedSensors.length) {
        mapInstance.addSource('highlighted-sensors', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: highlightedSensors.map(sensor => ({
              type: 'Feature',
              geometry: {
                type: 'Point',
                coordinates: [sensor.coords.lon, sensor.coords.lat],
              },
            })),
          },
        });

        mapInstance.addLayer({
          id: 'highlighted-sensors-layer',
          type: 'circle',
          source: 'highlighted-sensors',
          paint: {
            'circle-color': '#fdba74',
            'circle-stroke-color': '#f97316',
            'circle-stroke-width': 2,
            'circle-opacity': 0.3,
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 6, 13, 12, 16, 18],
          },
        });
      }
    };

    if (mapLoadedRef.current) {
      updateRouteAndHighlight();
    } else {
      mapInstance.once('load', updateRouteAndHighlight);
    }

    return () => {
      routeMarkersRef.current.forEach(marker => marker.remove());
      routeMarkersRef.current = [];
      clearRouteLayers();
      clearHighlightLayers();
    };
  }, [routePath, routeStops, highlightedSensors]);

  return (
    <div className="relative h-full w-full">
      <p className="sr-only">
        Mapa interativo. Sensores climaticos e sua localizacao estao marcados. Clique em qualquer lugar do mapa para ver as condicoes climaticas daquele ponto especifico.
      </p>
      <div
        ref={mapContainerRef}
        className={className || 'h-96 md:h-[480px] w-full rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 z-0'}
        aria-hidden="true"
        tabIndex={-1}
      />
    </div>
  );
};

export default MapComponent;
