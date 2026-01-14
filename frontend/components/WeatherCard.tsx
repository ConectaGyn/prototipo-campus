
import React from 'react';
import type { CurrentWeather } from '../types.ts';
import { convertWindDegreesToDirection } from '../services/weather/openWeather.service.ts';
import { WeatherIcon, DropletIcon, WindIcon, GaugeIcon, CompassIcon, CloudRainIcon } from './Icons.tsx';
import SpeakButton from './SpeakButton.tsx';

interface WeatherCardProps {
  current: CurrentWeather;
}

const WeatherCard: React.FC<WeatherCardProps> = ({ current }) => {
  const windDirection = convertWindDegreesToDirection(current.wind_deg);
  const ttsText = `Condições locais. Temperatura ${current.temp.toFixed(1)} graus. ${current.weather[0].description}. Umidade ${current.humidity} por cento. Vento ${Math.round(current.wind_speed)} quilômetros por hora.`;

  return (
    <section
      className="bg-white/70 dark:bg-slate-800/70 p-3 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm"
      aria-labelledby="current-conditions-title"
    >
      <div className="flex justify-between items-center mb-2">
        <h2
          id="current-conditions-title"
          className="text-sm font-semibold text-slate-600 dark:text-slate-300"
        >
          Condições Locais
        </h2>
        <SpeakButton
          text={ttsText}
          label="Ouvir condições locais"
          className="scale-90 opacity-70 hover:opacity-100"
        />
      </div>
      <div className="flex items-center gap-3 mb-3">
        <div className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          {current.temp.toFixed(1)}°C
        </div>
        <div className="flex items-center gap-1 text-sm text-cyan-600 dark:text-cyan-400 capitalize">
          <WeatherIcon iconCode={current.weather[0].icon} className="w-5 h-5" />
          <span>{current.weather[0].description}</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        <InfoRow
          icon={<DropletIcon className="w-4 h-4 text-cyan-500" />}
          label="Umidade"
          value={`${current.humidity}%`}
        />
        <InfoRow
          icon={<WindIcon className="w-4 h-4 text-slate-500" />}
          label="Vento"
          value={`${Math.round(current.wind_speed)} km/h`}
        />
        {current.rain?.['1h'] && (
          <InfoRow
            icon={<CloudRainIcon className="w-4 h-4 text-cyan-500" />}
            label="Chuva (1h)"
            value={`${current.rain['1h']} mm`}
          />
        )}
      </div>
    </section>
  );
};
  
const InfoRow: React.FC<{ icon: React.ReactElement; label: string; value: string }> = ({ icon, label, value }) => (
  <div className="flex items-center justify-between gap-2">
    <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
      {icon}
      <span>{label}</span>
    </div>
    <span className="font-medium text-slate-700 dark:text-slate-200">
      {value}
    </span>
  </div>
);


export default WeatherCard;
