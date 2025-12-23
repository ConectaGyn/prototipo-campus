import React from 'react';
import type { HourlyForecast } from '../types.ts';
import { WeatherIcon, DropletIcon } from './Icons.tsx';

interface HourlyForecastItemProps {
    hour: HourlyForecast;
}

const HourlyForecastItem: React.FC<HourlyForecastItemProps> = ({ hour }) => {
    const time = new Date(hour.dt * 1000).toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit'
    });

    return (
        <div className="flex-shrink-0 flex flex-col items-center justify-between p-3 w-24 h-36 bg-slate-200/50 dark:bg-slate-700/50 rounded-lg text-center">
            <div className="font-semibold text-slate-600 dark:text-slate-300">{time}</div>
            <WeatherIcon iconCode={hour.weather[0].icon} className="w-10 h-10 text-cyan-600 dark:text-cyan-400" />
            <div className="text-lg font-bold text-slate-800 dark:text-white">{Math.round(hour.temp)}°C</div>
            <div className="flex items-center gap-1 text-xs text-cyan-500 dark:text-cyan-300">
                <DropletIcon className="w-3 h-3"/>
                <span>{Math.round(hour.pop * 100)}%</span>
            </div>
        </div>
    );
};

export default HourlyForecastItem;