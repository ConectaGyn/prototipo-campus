import React from 'react';
import type { SensorData } from '../types.ts';
import SensorCard from './SensorCard.tsx';

interface SensorListProps {
  sensors: SensorData[];
}

const SensorList: React.FC<SensorListProps> = ({ sensors }) => {
  return (
    <div className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg">
      <h2 className="text-xl font-semibold mb-4 text-slate-600 dark:text-slate-300">Sensores na Cidade</h2>
      {sensors.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {sensors.map(sensor => (
            <SensorCard key={sensor.id} sensor={sensor} />
          ))}
        </div>
      ) : (
        <p className="text-slate-500 dark:text-slate-400">Aguardando dados dos sensores...</p>
      )}
    </div>
  );
};

export default SensorList;