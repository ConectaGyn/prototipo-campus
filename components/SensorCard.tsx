
import React from 'react';
import type { SensorData } from '../types.ts';
import { ThermometerIcon, DropletIcon, WindIcon, AlertTriangleIcon, CheckCircleIcon } from './Icons.tsx';
import SpeakButton from './SpeakButton.tsx';

interface SensorCardProps {
  sensor: SensorData;
  onSelect?: (sensor: SensorData) => void;
}

const SensorCard: React.FC<SensorCardProps> = ({ sensor, onSelect }) => {
  const { alert, location, temp, humidity, wind_speed } = sensor;
  const riskLevel = alert?.level || 'Nenhum';

  // Texto para leitura em voz alta
  const ttsText = `Sensor em ${location}. Risco ${riskLevel}. Temperatura ${temp.toFixed(1)} graus. Umidade ${Math.round(humidity)} por cento. Vento ${Math.round(wind_speed)} quilômetros por hora.`;

  // Configurações visuais baseadas no nível de risco
  const getRiskStyles = () => {
    switch (riskLevel) {
      case 'Alto':
        return {
          container: 'bg-red-50 dark:bg-red-900/30 border-red-500 dark:border-red-500',
          badge: 'bg-red-500 text-white',
          text: 'text-red-700 dark:text-red-200',
        };
      case 'Moderado':
        return {
          container: 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-500 dark:border-yellow-500',
          badge: 'bg-yellow-500 text-white',
          text: 'text-yellow-700 dark:text-yellow-200',
        };
      default:
        return {
          container: 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700',
          badge: 'bg-green-500 text-white',
          text: 'text-slate-600 dark:text-slate-400',
        };
    }
  };

  const styles = getRiskStyles();

  return (
    <div
      className={`relative p-3 sm:p-4 rounded-xl border shadow-sm transition-all duration-300 flex flex-col h-full w-full justify-between ${styles.container} ${onSelect ? 'cursor-pointer hover:shadow-lg focus-within:ring-2 focus-within:ring-cyan-500 focus:outline-none' : ''}`}
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : -1}
      onClick={() => onSelect?.(sensor)}
      onKeyDown={(e) => {
        if (!onSelect) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(sensor);
        }
      }}
    >
      
      <div>
        {/* Cabecalho: Local e Badge */}
        <div className="flex justify-between items-center mb-2 gap-2">
            <h3 className="font-bold text-sm text-slate-800 dark:text-slate-100 truncate flex-1" title={location}>
            {location}
            </h3>
            <div className={`shrink-0 px-2 py-0.5 rounded-full text-[10px] font-bold shadow-sm uppercase tracking-wide ${styles.badge}`}>
                {riskLevel === 'Nenhum' ? 'Normal' : riskLevel}
            </div>
        </div>

        {/* Bloco Principal: Temperatura e Acoes */}
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 dark:border-slate-700/50">
            <div className="flex items-center gap-1.5">
                <ThermometerIcon className="w-5 h-5 text-slate-400 dark:text-slate-500" />
                <span className="text-2xl font-bold text-slate-900 dark:text-white">{temp.toFixed(1)}°C</span>
            </div>
            <SpeakButton text={ttsText} label={`Ouvir dados de ${location}`} className="p-1.5 w-7 h-7 text-slate-400 hover:text-cyan-600 hover:bg-slate-100 dark:hover:bg-slate-700" />
        </div>

        {/* Bloco Secundario: Umidade e Vento lado a lado */}
        <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 p-1.5 rounded-lg">
                <DropletIcon className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
                <span>{Math.round(humidity)}%</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 p-1.5 rounded-lg">
                <WindIcon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>{Math.round(wind_speed)} km/h</span>
            </div>
        </div>
      </div>

      {/* Alerta Compacto (Aparece so se houver risco) */}
      {alert && riskLevel !== 'Nenhum' && (
        <div className={`mt-2 text-[10px] p-1.5 rounded border border-opacity-20 bg-opacity-10 ${styles.text} border-current leading-tight font-medium`}>
          {alert.message}
        </div>
      )}
      
    </div>
  );
};

export default SensorCard;
