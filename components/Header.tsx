
import React from 'react';
import { RefreshCwIcon, Volume2Icon, VolumeXIcon, SlidersIcon } from './Icons.tsx';
import ThemeToggle from './ThemeToggle.tsx';

interface HeaderProps {
  onRefresh: () => void;
  onOpenConfig: () => void;
  locationName: string;
  isRefreshing?: boolean;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  isSoundEnabled: boolean;
  toggleSound: () => void;
  isSimulationActive: boolean;
}

const Header: React.FC<HeaderProps> = ({ 
  onRefresh, 
  onOpenConfig,
  locationName, 
  isRefreshing, 
  theme, 
  toggleTheme,
  isSoundEnabled,
  toggleSound,
  isSimulationActive
}) => {
  return (
    <header className="flex justify-between items-center mb-6 lg:mb-8">
      <div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white tracking-tight">ClimaGyn</h1>
        <p className="text-lg text-cyan-600 dark:text-cyan-400">{locationName || 'Buscando localização...'}</p>
      </div>
      <div className="flex items-center gap-2">
        
        <button
          onClick={onOpenConfig}
          className={`p-3 rounded-full focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-colors ${
            isSimulationActive 
              ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-800/60'
              : 'bg-slate-200/60 dark:bg-slate-700/50 text-slate-800 dark:text-slate-200 hover:bg-slate-300/70 dark:hover:bg-slate-600/70'
          }`}
          aria-label="Configurar Simulação de Riscos"
          title={isSimulationActive ? "Simulação Ativa - Configurar" : "Configurar Simulação"}
        >
          <SlidersIcon className="w-5 h-5" />
        </button>

        <button
          onClick={toggleSound}
          className="p-3 bg-slate-200/60 dark:bg-slate-700/50 rounded-full hover:bg-slate-300/70 dark:hover:bg-slate-600/70 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:focus:ring-cyan-400 transition-colors"
          aria-label={isSoundEnabled ? "Desativar sons de notificação" : "Ativar sons de notificação"}
          title={isSoundEnabled ? "Silenciar notificações" : "Ativar sons"}
        >
        {isSoundEnabled ? (
          <Volume2Icon className="w-5 h-5 text-slate-800 dark:text-slate-200" />
        ) : (
          <VolumeXIcon className="w-5 h-5 text-slate-500 dark:text-slate-400" />
        )}
      </button>

      <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        
        <button
          onClick={onRefresh}
          className="p-3 bg-slate-200/60 dark:bg-slate-700/50 rounded-full hover:bg-slate-300/70 dark:hover:bg-slate-600/70 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:focus:ring-cyan-400 transition-colors"
          aria-label="Atualizar dados climáticos"
          disabled={isRefreshing}
        >
          <RefreshCwIcon className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </header>
  );
};

export default Header;
