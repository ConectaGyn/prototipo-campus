
import React, { useEffect, useRef } from 'react';
import type { SensorData } from '../types.ts';
import { getWeatherData, getLocationName } from '../services/weather/openWeather.service.ts';
import { useState } from 'react';

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

const MapComponent: React.FC<MapComponentProps> = ({ sensors, className, userLocation, routePath, routeStops, highlightedSensors }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null); // Para guardar a instancia do mapa
  const markersRef = useRef<any[]>([]); // Para guardar as instancias dos marcadores de sensores
  const userMarkerRef = useRef<any>(null); // Para guardar a instancia do marcador do usuario
  const tempMarkerRef = useRef<any>(null); // Para guardar o marcador temporario de 

  // Helper para criar icones circulares (Bolinhas)
  const getMarkerIcon = (level: string) => {
    let colorClass = 'bg-slate-400';
    let pulseHtml = '';

    if (level === 'Alto') {
      colorClass = 'bg-red-600';
      pulseHtml = '<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>';
    } else if (level === 'Moderado') {
      colorClass = 'bg-yellow-500';
    } else if (level === 'Baixo') {
      colorClass = 'bg-green-500';
    } else if (level === 'Indefinido' || level === 'Nenhum') {
      colorClass = 'bg-slate-500';
    }

    const html = `
      <div class="relative flex items-center justify-center w-6 h-6">
        ${pulseHtml}
        <span class="relative inline-flex rounded-full h-4 w-4 ${colorClass} border-2 border-white shadow-md"></span>
      </div>
    `;

    return L.divIcon({
      className: 'bg-transparent border-none',
      html: html,
      iconSize: [24, 24],
      iconAnchor: [12, 12], // Centro do icone
      popupAnchor: [0, -12]
    });
  };

  // Helper para criar icone do usuario (Bolinha Azul)
  const getUserIcon = () => {
    const html = `
      <div class="relative flex items-center justify-center w-6 h-6">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-300 opacity-50"></span>
        <span class="relative inline-flex rounded-full h-4 w-4 bg-blue-600 border-2 border-white shadow-lg"></span>
      </div>
    `;

    return L.divIcon({
      className: 'bg-transparent border-none',
      html: html,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -12]
    });
  };

  // Helper para criar icone temporario (Bolinha Cinza)
  const getTempIcon = () => {
    const html = `
      <div class="relative flex items-center justify-center w-5 h-5">
         <span class="relative inline-flex rounded-full h-4 w-4 bg-slate-500 border-2 border-white shadow-lg"></span>
      </div>
    `;

    return L.divIcon({
      className: 'bg-transparent border-none',
      html: html,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -12]
    });
  };

  const getRouteMarkerIcon = (type: RouteStopType) => {
    const palette: Record<RouteStopType, { bg: string; label: string }> = {
      start: { bg: 'bg-blue-600', label: 'Origem' },
      via: { bg: 'bg-purple-600', label: 'Desvio' },
      destination: { bg: 'bg-emerald-600', label: 'Destino' },
    };

    const { bg, label } = palette[type];

    const html = `
      <div class="flex flex-col items-center gap-1">
        <span class="text-[10px] font-semibold text-slate-600 bg-white/80 px-1 rounded">${label}</span>
        <div class="relative flex items-center justify-center w-5 h-5">
          <span class="relative inline-flex rounded-full h-4 w-4 ${bg} border-2 border-white shadow-lg"></span>
        </div>
      </div>
    `;

    return L.divIcon({
      className: 'bg-transparent border-none',
      html: html,
      iconSize: [24, 28],
      iconAnchor: [12, 26],
      popupAnchor: [0, -20]
    });
  };

  // Efeito para lidar com cliques fora do mapa
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      // Se o clique nao foi dentro do container do mapa e temos um marcador temporario
      if (mapContainerRef.current && !mapContainerRef.current.contains(event.target as Node)) {
        if (tempMarkerRef.current) {
          tempMarkerRef.current.remove();
          tempMarkerRef.current = null;
        }
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, []);

  useEffect(() => {
    // Garante que o container do mapa e o objeto Leaflet (L) existam
    if (!mapContainerRef.current || typeof L === 'undefined') return;

    // Inicializa o mapa apenas uma vez
    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current, {
        attributionControl: false, 
        zoomControl: true
      }).setView([-16.6869, -49.2648], 12);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(mapRef.current);
      
      mapRef.current.keyboard.disable();

    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

      sensors.forEach(sensor => {
        const marker = L.marker([sensor.coords.lat, sensor.coords.lon], {
          icon: getMarkerIcon('Nenhum'),
          zIndexOffset: 800,
        }).addTo(mapRef.current);

        const initialPopup = `
          <div class="font-sans p-2 min-w-[180px]">
            <h3 class="font-bold text-base text-slate-900 border-b pb-1 mb-2">
              ${sensor.location}
            </h3>
            <div class="text-sm text-slate-600 text-center italic">
            Clique para avaliar o risco neste ponto
            </div>
          </div>
        `;
        
        marker.bindPopup(initialPopup);

        marker.on('click', async () => {
          marker.setPopupContent(`
            <div class="flex items-center gap-2 p-2">
              <div class="w-4 h-4 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin"></div>
              <span class="text-sm font-semibold text-slate-600">Calculando risco...</span>
            </div>
          `);

          try {
            const response = await fetch(
              `${import.meta.env.VITE_API_BASE_URL}/points/${sensor.id}/risk`
            );

            if (!response.ok) throw new Error('Falha ao calcular risco');

            const risk = await response.json();

            marker.setIcon(getMarkerIcon(risk.nivel));

            marker.setPopupContent(`
              <div class="font-sans p-2 min-w-[180px]">
                <h3 class="font-bold text-base text-slate-900 border-b pb-1 mb-2">
                  ${sensor.location}
                </h3>
                <div class="text-center font-bold text-${risk.cor}">
                  Risco ${risk.nivel}
                </div>
                <div class="mt-1 text-xs text-slate-500 text-center">
                  Confiança: ${risk.confianca}
                </div>
              </div>
            `);
          } catch (e) {
            marker.setPopupContent(`
              <div class="p-2 text-sm text-red-600 fonto-bold">
                Não foi possível calcular o risco.
              </div>
            `);
          }
        });

        markersRef.current.push(marker);
      });

    }

    // --- Gerenciamento do Marcador do Usuario ---
    if (userMarkerRef.current) {
      userMarkerRef.current.remove();
      userMarkerRef.current = null;
    }

    if (userLocation) {
      userMarkerRef.current = L.marker([userLocation.lat, userLocation.lon], {
        icon: getUserIcon(),
        zIndexOffset: 1000,
        title: "Sua localizacao"
      })
      .addTo(mapRef.current)
      .bindPopup('<div class="font-sans font-bold text-slate-800 p-1"> Voce esta aqui</div>');
    }

    setTimeout(() => {
       mapRef.current?.invalidateSize();
    }, 100);

  }, [sensors, userLocation]);

  useEffect(() => {
    if (!mapRef.current || typeof L === 'undefined') return;

    const createdMarkers: any[] = [];
    const createdRiskLayers: any[] = [];
    let createdPolyline: any = null;

    if (routePath && routePath.length > 1) {
      const latlngs = routePath.map(point => [point.lat, point.lon]);
      createdPolyline = L.polyline(latlngs, {
        color: '#06b6d4',
        weight: 5,
        opacity: 0.85,
        lineJoin: 'round',
        dashArray: routePath.length > 2 ? '6 8' : undefined
      }).addTo(mapRef.current);

      mapRef.current.fitBounds(createdPolyline.getBounds(), { padding: [30, 30] });
    }

    if (routeStops && routeStops.length) {
      routeStops.forEach(stop => {
        const marker = L.marker([stop.coords.lat, stop.coords.lon], {
          icon: getRouteMarkerIcon(stop.kind),
          zIndexOffset: 900,
          title: stop.label
        })
        .addTo(mapRef.current)
        .bindPopup(`<div class="font-sans text-sm font-semibold">${stop.label}</div>`);
        createdMarkers.push(marker);
      });

      if (!createdPolyline && routeStops.length > 1) {
        const bounds = L.latLngBounds(routeStops.map(stop => [stop.coords.lat, stop.coords.lon]));
        mapRef.current.fitBounds(bounds, { padding: [30, 30] });
      }
    }

    if (highlightedSensors && highlightedSensors.length) {
      highlightedSensors.forEach(sensor => {
        const circle = L.circle([sensor.coords.lat, sensor.coords.lon], {
          radius: 500,
          color: '#f97316',
          fillColor: '#fdba74',
          fillOpacity: 0.25,
          weight: 2
        }).addTo(mapRef.current);
        createdRiskLayers.push(circle);
      });
    }

    return () => {
      createdMarkers.forEach(marker => marker.remove());
      createdRiskLayers.forEach(layer => layer.remove());
      if (createdPolyline) {
        createdPolyline.remove();
      }
    };
  }, [routePath, routeStops, highlightedSensors]);

  return (
    <div className="relative h-full w-full">
      <p className="sr-only">
        Mapa interativo. Sensores climaticos e sua localizacao estao marcados. Clique em qualquer lugar do mapa para ver as condições climaticas daquele ponto especifico.
      </p>
      <div 
        ref={mapContainerRef} 
        className={className || "h-[420px] md:h-[520px] w-full rounded-2xl shadow-md border border-slate-200 dark:border-slate-700"}
        aria-hidden="true" 
        tabIndex={-1}
      />
    </div>
  );
};

export default MapComponent;
