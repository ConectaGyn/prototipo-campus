import React, { useRef, useState } from 'react';
import type { SensorData } from '../types.ts';
import SensorCard from './SensorCard.tsx';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  XIcon,
  MapPinIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  WindIcon,
  DropletIcon,
  ThermometerIcon,
} from './Icons.tsx';

interface SensorCarouselProps {
  sensors: SensorData[];
}

const SensorCarousel: React.FC<SensorCarouselProps> = ({ sensors }) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [selectedSensor, setSelectedSensor] = useState<SensorData | null>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = scrollContainerRef.current.clientWidth * 0.8;
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  const hasRiskCalculated = Boolean(selectedSensor?.alert);

  return (
    <section className="relative" aria-labelledby="sensors-list-title">
      <h2
        id="sensors-list-title"
        className="text-xl font-medium mb-2 text-slate-500 dark:text-slate-400"
      >
        Pontos Monitorados
      </h2>

      {/* Botão esquerda */}
      <button
        onClick={() => scroll('left')}
        className="absolute top-1/2 -translate-y-1/2 -left-4 bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm rounded-full p-2 shadow-lg hover:bg-white dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all z-10 opacity-75 hover:opacity-100"
        aria-label="Rolar lista de sensores para a esquerda"
      >
        <ChevronLeftIcon className="w-6 h-6 text-slate-700 dark:text-slate-200" />
      </button>

      {/* Lista */}
      <div
        ref={scrollContainerRef}
        className="flex overflow-x-auto space-x-2 sm:space-x-4 pb-2 scroll-smooth px-2"
        role="region"
        aria-label="Lista de cartões de sensores"
        tabIndex={0}
      >
        <style>{`
          .overflow-x-auto::-webkit-scrollbar { display: none; }
          .overflow-x-auto { -ms-overflow-style: none; scrollbar-width: none; }
        `}</style>

        {sensors.map(sensor => (
          <article key={sensor.id} className="flex-shrink-0 w-[65vw] sm:w-52">
            <SensorCard sensor={sensor} onSelect={setSelectedSensor} />
          </article>
        ))}
      </div>

      {/* Botão direita */}
      <button
        onClick={() => scroll('right')}
        className="absolute top-1/2 -translate-y-1/2 -right-4 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm rounded-full p-2 shadow-md hover:bg-white dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all z-10 opacity-75 hover:opacity-100"
        aria-label="Rolar lista de sensores para a direita"
      >
        <ChevronRightIcon className="w-6 h-6 text-slate-700 dark:text-slate-200" />
      </button>

      {/* Modal */}
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

            {/* Cabeçalho */}
            <div className="flex items-center gap-3 mb-4">
              <MapPinIcon className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Ponto Monitorado
                </p>
                <h3 className="text-xl font-bold text-slate-800 dark:text-white">
                  {selectedSensor.location}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Lat {selectedSensor.coords.lat.toFixed(4)} | Lon{' '}
                  {selectedSensor.coords.lon.toFixed(4)}
                </p>
              </div>
            </div>

            {/* Clima */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
                <ThermometerIcon className="w-5 h-5 text-red-500" />
                <div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Temperatura
                  </p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white">
                    {typeof selectedSensor.temp === 'number'
                      ? `${selectedSensor.temp.toFixed(1)}°C`
                      : '--'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
                <DropletIcon className="w-5 h-5 text-cyan-500" />
                <div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Umidade
                  </p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white">
                    {typeof selectedSensor.humidity === 'number'
                      ? `${selectedSensor.humidity}%`
                      : '--'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
                <WindIcon className="w-5 h-5 text-slate-500" />
                <div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Vento
                  </p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white">
                    {typeof selectedSensor.wind_speed === 'number'
                      ? `${Math.round(selectedSensor.wind_speed)} km/h`
                      : '--'}
                  </p>
                </div>
              </div>
            </div>

            {/* Bloco de risco (ajustado) */}
            <div
              className={`p-3 rounded-xl border flex items-center gap-3 mb-4 ${
                hasRiskCalculated
                  ? 'border-amber-400 bg-amber-50 dark:border-amber-500 dark:bg-amber-900/30'
                  : 'border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/30'
              }`}
            >
              {hasRiskCalculated ? (
                <AlertTriangleIcon className="w-6 h-6 text-amber-500" />
              ) : (
                <CheckCircleIcon className="w-6 h-6 text-slate-400" />
              )}

              <div>
                <p className="text-sm font-semibold text-slate-800 dark:text-white">
                  {hasRiskCalculated
                    ? `Risco ${selectedSensor.alert!.level}`
                    : 'Risco ainda não avaliado'}
                </p>
                <p className="text-xs text-slate-600 dark:text-slate-300">
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
