
import React from 'react';
import type { CurrentWeather } from '../types.ts';
import { convertWindDegreesToDirection } from '../services/weatherService.ts';
import { WeatherIcon, DropletIcon, WindIcon, GaugeIcon, CompassIcon, CloudRainIcon } from './Icons.tsx';
import SpeakButton from './SpeakButton.tsx';

interface WeatherCardProps {
  current: CurrentWeather;
}

const WeatherCard: React.FC<WeatherCardProps> = ({ current }) => {
  const windDirection = convertWindDegreesToDirection(current.wind_deg);

  const ttsText = `Condições atuais. Temperatura de ${current.temp.toFixed(1)} graus Celsius. ${current.weather[0].description}. Sensação térmica de ${current.feels_like.toFixed(1)} graus. Umidade do ar em ${current.humidity} por cento. Ventos de ${Math.round(current.wind_speed)} quilômetros por hora na direção ${windDirection}.`;

  return (
    <section className="bg-white dark:bg-slate-800 p-6 rounded-xl h-full border border-slate-200 dark:border-slate-700 shadow-lg relative" aria-labelledby="current-conditions-title">
      <div className="flex justify-between items-start mb-4">
        <h2 id="current-conditions-title" className="text-xl font-semibold text-slate-600 dark:text-slate-300">Condições Atuais</h2>
        <SpeakButton text={ttsText} label="Ouvir condições atuais" />
      </div>
      
      <div className="flex flex-col items-center text-center">
        <div className="text-6xl font-bold text-slate-900 dark:text-white mb-2" aria-label={`Temperatura atual: ${current.temp.toFixed(1)} graus Celsius`}>
          {current.temp.toFixed(1)}°C
        </div>
        <div className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400 capitalize text-lg">
          <WeatherIcon iconCode={current.weather[0].icon} className="w-8 h-8"/>
          <span>{current.weather[0].description}</span>
        </div>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Sensação térmica: {current.feels_like.toFixed(1)}°C
        </p>
      </div>
      <dl className="mt-8 space-y-4">
        <InfoRow icon={<DropletIcon className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />} label="Umidade" value={`${current.humidity}%`} />
        <InfoRow icon={<WindIcon className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />} label="Vento" value={`${Math.round(current.wind_speed)} km/h`} />
        <InfoRow icon={<CompassIcon className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />} label="Direção do Vento" value={windDirection} />
        <InfoRow icon={<GaugeIcon className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />} label="Pressão Atmosférica" value={`${current.pressure} hPa`} />
        {current.rain && current.rain['1h'] && (
            <InfoRow icon={<CloudRainIcon className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />} label="Chuva (última hora)" value={`${current.rain['1h']} mm`} />
        )}
      </dl>
    </section>
  );
};

const InfoRow: React.FC<{ icon: React.ReactElement; label: string; value: string }> = ({ icon, label, value }) => (
  <div className="flex justify-between items-center text-base">
    <dt className="flex items-center gap-3">
      <span aria-hidden="true">{icon}</span>
      <span className="text-slate-600 dark:text-slate-300">{label}</span>
    </dt>
    <dd className="font-semibold text-slate-800 dark:text-white">{value}</dd>
  </div>
);

export default WeatherCard;
