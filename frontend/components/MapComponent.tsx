
import React, { useEffect, useRef } from 'react';
import type { SensorData } from '../types.ts';
import { getWeatherData, getLocationName } from '../services/weather/openWeather.service.ts';
import { useState } from 'react';


// Declara o objeto L do Leaflet para o TypeScript para evitar erros,
// ja que ele e carregado globalmente a partir de um script.
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
  const criticalMarkersRef = useRef<any[]>([]);

  // Helper para criar icones circulares (Bolinhas)
  const getMarkerIcon = (level: string) => {
    let colorClass = 'bg-green-500';
    let pulseHtml = '';

    if (level === 'Alto') {
      colorClass = 'bg-red-600';
      // Animacao de pulso para risco alto
      pulseHtml = '<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>';
    } else if (level === 'Moderado') {
      colorClass = 'bg-yellow-500';
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

      // Adiciona ouvinte de clique no mapa
      mapRef.current.on('click', async (e: any) => {
        const { lat, lng } = e.latlng;

        // Remove marcador temporario anterior, se existir
        if (tempMarkerRef.current) {
          tempMarkerRef.current.remove();
          tempMarkerRef.current = null;
        }

        // Conteudo de carregamento
        const loadingContent = `
          <div class="flex items-center gap-2 p-2 font-sans">
             <div class="w-4 h-4 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin"></div>
             <span class="text-sm text-slate-600 font-semibold">Buscando dados...</span>
          </div>
        `;

        // Cria o marcador no local clicado
        const marker = L.marker([lat, lng], {
            icon: getTempIcon(),
            zIndexOffset: 500
        }).addTo(mapRef.current)
          .bindPopup(loadingContent)
          .openPopup();

        // Adiciona evento para remover o marcador quando o popup fechar
        // Isso acontece ao clicar no 'X' ou clicar no fundo do mapa
        marker.on('popupclose', () => {
           marker.remove();
           if (tempMarkerRef.current === marker) {
               tempMarkerRef.current = null;
           }
        });

        tempMarkerRef.current = marker;

        try {
             // Busca dados reais da API para o ponto clicado
            const [weatherData, locName] = await Promise.all([
                getWeatherData(lat, lng),
                getLocationName(lat, lng)
            ]);

            const weather = weatherData.current;
            
            const popupContent = `
                <div class="font-sans p-1 min-w-[160px]">
                  <h3 class="font-bold text-base text-slate-900 border-b pb-1 mb-2">${locName}</h3>
                  <div class="space-y-1 text-sm text-slate-700">
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

            marker.setPopupContent(popupContent);

        } catch (error) {
            console.error("Erro ao buscar dados do ponto:", error);
            marker.setPopupContent(`
                <div class="p-2 font-sans text-sm text-red-600 font-bold">
                   Nao foi possivel carregar os dados deste local.
                </div>
            `);
        }
      });
    }
    
    // --- Gerenciamento de Marcadores de Sensores ---
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    sensors.forEach(sensor => {
      const riskLevel = sensor.alert?.level || 'Nenhum';
      
      const popupContent = `
        <div class="font-sans p-2 min-w-[180px]">
          <h3 class="font-bold text-base text-slate-900 border-b pb-1 mb-2">
            ${sensor.location}
          </h3>

          <div class="space-y-1 text-sm text-slate-700">
            <div class="flex justify-between"><span>Temperatura:</span><span class="font-semibold">${sensor.temp.toFixed(1)}°C</span></div>
            <div class="flex justify-between"><span>Umidade:</span><span class="font-semibold">${Math.round(sensor.humidity)}%</span></div>
            <div class="flex justify-between"><span>Vento:</span><span class="font-semibold">${Math.round(sensor.wind_speed)} km/h</span></div>
          </div>

          <div class="mt-3 pt-2 border-t text-center font-bold ${
            riskLevel === 'Alto'
              ? 'text-red-600'
              : riskLevel === 'Moderado'
                ? 'text-yellow-600'
                : 'text-green-600'
          }">
            ${riskLevel !== 'Nenhum' ? `Risco ${riskLevel}` : 'Sem risco'}
          </div>

          <div class="mt-2 text-xs text-slate-400 text-center italic">
            Ponto crítico monitorado
          </div>
        </div>
     `;
      
      const marker = L.marker([sensor.coords.lat, sensor.coords.lon], {
        icon: getMarkerIcon(riskLevel),
        title: `Ponto critico: ${sensor.location}`,
        zIndexOffset: 800,
      })
        .addTo(mapRef.current)
        .bindPopup(popupContent);
        
      markersRef.current.push(marker);
    });

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
