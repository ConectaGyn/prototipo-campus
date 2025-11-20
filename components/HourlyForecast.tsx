
import React from 'react';
import type { HourlyForecast as HourlyForecastType } from '../types.ts';
import HourlyForecastItem from './HourlyForecastItem.tsx';

interface HourlyForecastProps {
    hourly: HourlyForecastType[];
}

const HourlyForecast: React.FC<HourlyForecastProps> = ({ hourly }) => {
    return (
        <section className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg" aria-labelledby="hourly-forecast-title">
            <h2 id="hourly-forecast-title" className="text-xl font-semibold mb-4 text-slate-600 dark:text-slate-300">Próximas horas</h2>
            <ul className="flex overflow-x-auto space-x-4 -mx-6 px-6 pb-2">
                {hourly.map(hour => (
                    <li key={hour.dt}>
                        <HourlyForecastItem hour={hour} />
                    </li>
                ))}
            </ul>
             <style>{`
                .dark .overflow-x-auto::-webkit-scrollbar-thumb {
                    background-color: rgba(100, 116, 139, 0.5);
                }
                .dark .overflow-x-auto::-webkit-scrollbar-thumb:hover {
                    background-color: rgba(100, 116, 139, 0.7);
                }
                .light .overflow-x-auto::-webkit-scrollbar-thumb {
                    background-color: rgba(148, 163, 184, 0.5);
                }
                .light .overflow-x-auto::-webkit-scrollbar-thumb:hover {
                    background-color: rgba(148, 163, 184, 0.7);
                }
                .overflow-x-auto::-webkit-scrollbar {
                    height: 8px;
                }
                .overflow-x-auto::-webkit-scrollbar-track {
                    background: transparent;
                }
                .overflow-x-auto::-webkit-scrollbar-thumb {
                    border-radius: 4px;
                }
            `}</style>
        </section>
    );
};

export default HourlyForecast;
