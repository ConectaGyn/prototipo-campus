
import React from 'react';
import type { DailyForecast } from '../types.ts';
import ForecastItem from './ForecastItem.tsx';

interface ForecastListProps {
  daily: DailyForecast[];
}

const ForecastList: React.FC<ForecastListProps> = ({ daily }) => {
  return (
    <section className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg h-full" aria-labelledby="daily-forecast-title">
      <h2 id="daily-forecast-title" className="text-xl font-semibold mb-4 text-slate-600 dark:text-slate-300">Previsão para 5 dias</h2>
      <ul className="space-y-3">
        {daily.map((day, index) => (
          <li key={day.dt}>
            <ForecastItem day={day} isToday={index === 0} />
          </li>
        ))}
      </ul>
    </section>
  );
};

export default ForecastList;
