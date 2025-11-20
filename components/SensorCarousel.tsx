
import React, { useRef } from 'react';
import type { SensorData } from '../types.ts';
import SensorCard from './SensorCard.tsx';
import { ChevronLeftIcon, ChevronRightIcon } from './Icons.tsx';

interface SensorCarouselProps {
  sensors: SensorData[];
}

const SensorCarousel: React.FC<SensorCarouselProps> = ({ sensors }) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = scrollContainerRef.current.clientWidth * 0.8;
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  return (
    <section className="relative" aria-labelledby="sensors-list-title">
      <h2 id="sensors-list-title" className="text-xl font-semibold mb-4 text-slate-600 dark:text-slate-300">Sensores na Cidade</h2>
      
      <button
        onClick={() => scroll('left')}
        className="absolute top-1/2 -translate-y-1/2 -left-4 bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm rounded-full p-2 shadow-lg hover:bg-white dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all z-10 opacity-75 hover:opacity-100 disabled:opacity-25"
        aria-label="Rolar lista de sensores para a esquerda"
      >
        <ChevronLeftIcon className="w-6 h-6 text-slate-700 dark:text-slate-200" aria-hidden="true" />
      </button>

      <div ref={scrollContainerRef} className="flex overflow-x-auto space-x-4 pb-4 scroll-smooth" role="region" aria-label="Lista de cartões de sensores" tabIndex={0}>
        {/* Hide scrollbar */}
        <style>{`
          .overflow-x-auto::-webkit-scrollbar { 
            display: none; 
          }
          .overflow-x-auto {
            -ms-overflow-style: none;
            scrollbar-width: none;
          }
        `}</style>
        {sensors.map(sensor => (
          <article key={sensor.id} className="flex-shrink-0 w-60 sm:w-64">
            <SensorCard sensor={sensor} />
          </article>
        ))}
      </div>

      <button
        onClick={() => scroll('right')}
        className="absolute top-1/2 -translate-y-1/2 -right-4 bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm rounded-full p-2 shadow-lg hover:bg-white dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all z-10 opacity-75 hover:opacity-100 disabled:opacity-25"
        aria-label="Rolar lista de sensores para a direita"
      >
        <ChevronRightIcon className="w-6 h-6 text-slate-700 dark:text-slate-200" aria-hidden="true" />
      </button>
    </section>
  );
};

export default SensorCarousel;
