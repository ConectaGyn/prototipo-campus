import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { SensorData } from '../types.ts';
import SensorCard from './SensorCard.tsx';
import { getCurrentWeather } from '../services/weather';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  XIcon,
  MapPinIcon,
  WindIcon,
  DropletIcon,
  ThermometerIcon,
} from './Icons.tsx';

interface SensorCarouselProps {
  sensors: SensorData[];
}

const WEATHER_REFRESH_INTERVAL_MS = 180000;

type RiskFilter = 'todos' | 'nao_avaliado' | 'Baixo' | 'Moderado' | 'Alto' | 'Muito Alto';

const SensorCarousel: React.FC<SensorCarouselProps> = ({ sensors }) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [selectedSensor, setSelectedSensor] = useState<SensorData | null>(null);
  const [isLoadingSelectedWeather, setIsLoadingSelectedWeather] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('todos');

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = scrollContainerRef.current.clientWidth * 0.8;
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  useEffect(() => {
    if (!selectedSensor) return;
    const latest = sensors.find((item) => item.id === selectedSensor.id);
    if (!latest) return;

    setSelectedSensor((prev) => {
      if (!prev || prev.id !== latest.id) return prev;
      return {
        ...prev,
        ...latest,
      };
    });
  }, [sensors, selectedSensor?.id]);

  useEffect(() => {
    if (!selectedSensor) return;

    let cancelled = false;
    let inFlight = false;

    const applyCurrentWeather = async (showLoader: boolean) => {
      if (inFlight) return;
      inFlight = true;
      if (showLoader) setIsLoadingSelectedWeather(true);

      try {
        const current = await getCurrentWeather(
          selectedSensor.coords.lat,
          selectedSensor.coords.lon
        );
        if (cancelled) return;

        setSelectedSensor((prev) => {
          if (!prev || prev.id !== selectedSensor.id) return prev;
          return {
            ...prev,
            temp: current.temp,
            humidity: current.humidity,
            wind_speed: current.wind_speed,
            feels_like: current.feels_like,
            pressure: current.pressure,
            rain: current.rain,
          };
        });
      } finally {
        inFlight = false;
        if (!cancelled && showLoader) setIsLoadingSelectedWeather(false);
      }
    };

    const hasWeather =
      typeof selectedSensor.temp === 'number' &&
      typeof selectedSensor.humidity === 'number' &&
      typeof selectedSensor.wind_speed === 'number';

    void applyCurrentWeather(!hasWeather);

    const intervalId = window.setInterval(() => {
      void applyCurrentWeather(false);
    }, WEATHER_REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [selectedSensor?.id, selectedSensor?.coords.lat, selectedSensor?.coords.lon]);

  const filteredSensors = useMemo(() => {
    const search = searchTerm.trim().toLowerCase();

    return sensors.filter((sensor) => {
      const byName = search.length === 0 ? true : sensor.location.toLowerCase().includes(search);

      let byRisk = true;
      if (riskFilter === 'nao_avaliado') {
        byRisk = !sensor.alert?.level;
      } else if (riskFilter !== 'todos') {
        byRisk = sensor.alert?.level === riskFilter;
      }

      return byName && byRisk;
    });
  }, [sensors, searchTerm, riskFilter]);

  const hasRiskCalculated = Boolean(selectedSensor?.alert);

  const getRiskVisual = (sensor: SensorData | null) => {
    const level = sensor?.alert?.level;

    if (level === 'Muito Alto' || level === 'Alto') {
      return {
        border: 'border-red-400 dark:border-red-500',
        bg: 'bg-red-50 dark:bg-red-900/25',
        title: 'text-red-700 dark:text-red-300',
        subtitle: 'text-red-600 dark:text-red-300',
        emoji: '\u{1F6A8}',
      };
    }

    if (level === 'Moderado') {
      return {
        border: 'border-yellow-400 dark:border-yellow-500',
        bg: 'bg-yellow-50 dark:bg-yellow-900/25',
        title: 'text-yellow-800 dark:text-yellow-200',
        subtitle: 'text-yellow-700 dark:text-yellow-300',
        emoji: '\u26A0\uFE0F',
      };
    }

    if (level === 'Baixo') {
      return {
        border: 'border-green-400 dark:border-green-500',
        bg: 'bg-green-50 dark:bg-green-900/25',
        title: 'text-green-800 dark:text-green-200',
        subtitle: 'text-green-700 dark:text-green-300',
        emoji: '\u{1F7E2}',
      };
    }

    return {
      border: 'border-slate-300 dark:border-slate-700',
      bg: 'bg-slate-50 dark:bg-slate-900/30',
      title: 'text-slate-800 dark:text-slate-200',
      subtitle: 'text-slate-600 dark:text-slate-300',
      emoji: '\u2705',
    };
  };

  const riskVisual = getRiskVisual(selectedSensor);

  return (
    <section className="relative" aria-labelledby="sensors-list-title">
      <h2
        id="sensors-list-title"
        className="text-xl font-medium mb-2 text-slate-500 dark:text-slate-400"
      >
        Pontos Monitorados
      </h2>

      <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Buscar ponto por nome"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:focus:ring-cyan-900/40"
          aria-label="Buscar ponto monitorado por nome"
        />

        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value as RiskFilter)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:focus:ring-cyan-900/40"
          aria-label="Filtrar pontos por nivel de risco"
        >
          <option value="todos">Todos os riscos</option>
          <option value="nao_avaliado">Nao avaliados</option>
          <option value="Baixo">Baixo</option>
          <option value="Moderado">Moderado</option>
          <option value="Alto">Alto</option>
          <option value="Muito Alto">Muito Alto</option>
        </select>
      </div>

      <button
        onClick={() => scroll('left')}
        className="absolute top-1/2 -translate-y-1/2 -left-4 bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm rounded-full p-2 shadow-lg hover:bg-white dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all z-10 opacity-75 hover:opacity-100"
        aria-label="Rolar lista de sensores para a esquerda"
      >
        <ChevronLeftIcon className="w-6 h-6 text-slate-700 dark:text-slate-200" />
      </button>

      <div
        ref={scrollContainerRef}
        className="flex overflow-x-auto space-x-2 sm:space-x-4 pb-2 scroll-smooth px-2"
        role="region"
        aria-label="Lista de cartoes de sensores"
        tabIndex={0}
      >
        <style>{`
          .overflow-x-auto::-webkit-scrollbar { display: none; }
          .overflow-x-auto { -ms-overflow-style: none; scrollbar-width: none; }
        `}</style>

        {filteredSensors.map((sensor) => (
          <article key={sensor.id} className="flex-shrink-0 w-[65vw] sm:w-52">
            <SensorCard sensor={sensor} onSelect={setSelectedSensor} />
          </article>
        ))}

        {filteredSensors.length === 0 && (
          <div className="w-full rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500 dark:border-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
            Nenhum ponto encontrado com os filtros selecionados.
          </div>
        )}
      </div>

      <button
        onClick={() => scroll('right')}
        className="absolute top-1/2 -translate-y-1/2 -right-4 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm rounded-full p-2 shadow-md hover:bg-white dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all z-10 opacity-75 hover:opacity-100"
        aria-label="Rolar lista de sensores para a direita"
      >
        <ChevronRightIcon className="w-6 h-6 text-slate-700 dark:text-slate-200" />
      </button>

      {selectedSensor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-md w-full p-4 sm:p-5 relative border border-slate-200 dark:border-slate-700 max-h-[85vh] overflow-y-auto">
            <button
              onClick={() => setSelectedSensor(null)}
              className="absolute top-4 right-4 p-2 rounded-full text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700"
              aria-label="Fechar detalhes do sensor"
            >
              <XIcon className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <MapPinIcon className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Ponto Monitorado</p>
                <h3 className="text-xl font-bold text-slate-800 dark:text-white">{selectedSensor.location}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Lat {selectedSensor.coords.lat.toFixed(4)} | Lon {selectedSensor.coords.lon.toFixed(4)}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
                <ThermometerIcon className="w-5 h-5 text-red-500" />
                <div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">Temperatura</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white">
                    {typeof selectedSensor.temp === 'number'
                      ? `${selectedSensor.temp.toFixed(1)}°C`
                      : isLoadingSelectedWeather
                        ? '...'
                        : '--'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
                <DropletIcon className="w-5 h-5 text-cyan-500" />
                <div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">Umidade</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white">
                    {typeof selectedSensor.humidity === 'number'
                      ? `${selectedSensor.humidity}%`
                      : isLoadingSelectedWeather
                        ? '...'
                        : '--'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
                <WindIcon className="w-5 h-5 text-slate-500" />
                <div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">Vento</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white">
                    {typeof selectedSensor.wind_speed === 'number'
                      ? `${Math.round(selectedSensor.wind_speed)} km/h`
                      : isLoadingSelectedWeather
                        ? '...'
                        : '--'}
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-3 rounded-xl border flex items-center gap-3 mb-4 ${riskVisual.border} ${riskVisual.bg}`}>
              <span className="text-2xl leading-none" aria-hidden="true">{riskVisual.emoji}</span>

              <div>
                <p className={`text-sm font-semibold ${riskVisual.title}`}>
                  {hasRiskCalculated ? `Risco ${selectedSensor.alert!.level}` : 'Risco ainda nao avaliado'}
                </p>
                <p className={`text-xs ${riskVisual.subtitle}`}>
                  {hasRiskCalculated
                    ? selectedSensor.alert!.message
                    : 'Clique no ponto do mapa para calcular o risco deste local.'}
                </p>
              </div>
            </div>

            <div className="text-xs text-slate-500 dark:text-slate-400">
              <p>ID: {selectedSensor.id}</p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default SensorCarousel;
