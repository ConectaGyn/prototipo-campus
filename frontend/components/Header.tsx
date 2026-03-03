import React from "react";
import {
  RefreshCwIcon,
  Volume2Icon,
  VolumeXIcon,
  SlidersIcon,
} from "./Icons.tsx";
import ThemeToggle from "./ThemeToggle.tsx";
import appLogo from "../assets/logo.svg";

interface HeaderProps {
  onRefresh: () => void;
  onOpenConfig?: () => void;
  isRefreshing?: boolean;
  theme: "light" | "dark";
  toggleTheme: () => void;
  isSoundEnabled: boolean;
  toggleSound: () => void;
  isSimulationActive?: boolean;
}

const Header: React.FC<HeaderProps> = ({
  onRefresh,
  onOpenConfig,
  isRefreshing,
  theme,
  toggleTheme,
  isSoundEnabled,
  toggleSound,
  isSimulationActive = false,
}) => {
  return (
    <header className="mb-6 lg:mb-8 overflow-hidden rounded-2xl border border-blue-300/20 bg-gradient-to-r from-blue-950 via-blue-900 to-slate-900 shadow-lg dark:border-blue-900/40 dark:from-blue-950 dark:via-blue-900 dark:to-slate-950">
      <div className="flex justify-between items-center gap-4 px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <h1 className="sr-only">ClimaGyn</h1>
          <img src={appLogo} alt="ClimaGyn" className="h-10 sm:h-12 w-auto" />
          <p className="mt-2 text-sm sm:text-base text-cyan-100/95">
            Sistema Integrado de Gestão de Alertas Técnicos Climáticos
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onOpenConfig && (
            <button
              onClick={onOpenConfig}
              className={`p-3 rounded-full focus:outline-none focus:ring-2 focus:ring-cyan-200 transition-colors ${
                isSimulationActive
                  ? "bg-amber-300/20 text-amber-100 hover:bg-amber-300/30"
                  : "bg-white/15 text-white hover:bg-white/25"
              }`}
              aria-label="Configurar simulacao de riscos"
              title={isSimulationActive ? "Simulacao ativa - Configurar" : "Configurar simulacao"}
            >
              <SlidersIcon className="w-5 h-5" />
            </button>
          )}

          <button
            onClick={toggleSound}
            className="p-3 rounded-full bg-white/15 text-white hover:bg-white/25 focus:outline-none focus:ring-2 focus:ring-cyan-200 transition-colors"
            aria-label={isSoundEnabled ? "Desativar sons de notificacao" : "Ativar sons de notificacao"}
            title={isSoundEnabled ? "Silenciar notificacoes" : "Ativar sons"}
          >
            {isSoundEnabled ? (
              <Volume2Icon className="w-5 h-5 text-white" />
            ) : (
              <VolumeXIcon className="w-5 h-5 text-white/80" />
            )}
          </button>

          <ThemeToggle
            theme={theme}
            toggleTheme={toggleTheme}
            className="bg-white/15 hover:bg-white/25 dark:bg-white/15 dark:hover:bg-white/25 focus:ring-cyan-200"
            iconClassName="text-white"
          />

          <button
            onClick={onRefresh}
            className="p-3 rounded-full bg-white/15 text-white hover:bg-white/25 focus:outline-none focus:ring-2 focus:ring-cyan-200 transition-colors"
            aria-label="Atualizar dados climaticos"
            disabled={isRefreshing}
          >
            <RefreshCwIcon className={`w-5 h-5 text-white ${isRefreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t border-white/15 bg-black/10 px-4 py-2 text-xs sm:text-sm text-cyan-100/95 sm:px-5">
        <span className="inline-flex items-center rounded-full bg-white/10 px-2.5 py-1">
          {isRefreshing ? "Atualizando dados..." : "Dados sincronizados"}
        </span>
      </div>
    </header>
  );
};

export default Header;
