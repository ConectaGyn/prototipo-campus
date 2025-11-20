import React from 'react';
import type { DailyForecast } from '../types.ts';
import { WeatherIcon, DropletIcon } from './Icons.tsx';

interface ForecastItemProps {
  day: DailyForecast;
  isToday: boolean;
}

const ForecastItem: React.FC<ForecastItemProps> = ({ day, isToday }) => {
  const date = new Date(day.dt * 1000);
  const dayName = isToday 
    ? 'Hoje' 
    : date.toLocaleDateString('pt-BR', { weekday: 'long' });

  return (
    <div className={`flex items-center justify-between p-3 rounded-lg ${isToday ? 'bg-cyan-500/10 dark:bg-cyan-500/20' : 'bg-slate-200/50 dark:bg-slate-700/50'}`}>
      <div className="w-2/5 font-medium capitalize text-slate-700 dark:text-slate-200">{dayName}</div>
      <div className="w-1/5 flex justify-start items-center gap-2 text-cyan-600 dark:text-cyan-400 text-sm">
          <DropletIcon className="w-4 h-4" />
          <span>{Math.round(day.pop * 100)}%</span>
      </div>
      <div className="w-1/5 flex justify-center items-center gap-2 text-slate-600 dark:text-slate-300">
        <WeatherIcon iconCode={day.weather[0].icon} className="w-8 h-8" />
      </div>
      <div className="w-1/5 text-right font-semibold text-slate-700 dark:text-slate-200">
        <span className="text-slate-800 dark:text-white">{Math.round(day.temp.max)}°</span>
        <span className="text-slate-500 dark:text-slate-400 ml-2">{Math.round(day.temp.min)}°</span>
      </div>
    </div>
  );
};

export default ForecastItem;