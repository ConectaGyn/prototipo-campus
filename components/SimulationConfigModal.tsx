
import React, { useState, useEffect } from 'react';
import { XIcon, SlidersIcon, ShuffleIcon } from './Icons.tsx';
import type { SimulationState, SimulationOverride, SimulationIntensity } from '../types.ts';
import { sensorLocations } from '../services/sensorService.ts';

interface SimulationConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentConfig: SimulationState;
  onSave: (config: SimulationState) => void;
}

const SimulationConfigModal: React.FC<SimulationConfigModalProps> = ({ 
  isOpen, 
  onClose, 
  currentConfig,
  onSave 
}) => {
  // Estado local para manipular as configurações antes de salvar
  const [isEnabled, setIsEnabled] = useState(false);
  const [localOverrides, setLocalOverrides] = useState<Record<string, SimulationOverride>>({});
  const [randomTarget, setRandomTarget] = useState<'Caos' | 'Alto' | 'Moderado'>('Caos');

  // Carrega a configuração atual ao abrir o modal
  useEffect(() => {
    if (isOpen) {
      setIsEnabled(currentConfig.isEnabled);
      setLocalOverrides(currentConfig.overrides);
    }
  }, [isOpen, currentConfig]);

  // Fecha o modal ao pressionar ESC
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleOverrideChange = (sensorId: string, field: 'intensity' | 'duration', value: string | number) => {
    setLocalOverrides(prev => {
      const current = prev[sensorId] || { intensity: 'Normal', duration: 60, endTime: 0 };
      
      // Se definir como normal, removemos do mapa de overrides para limpar
      if (field === 'intensity' && value === 'Normal') {
        const next = { ...prev };
        delete next[sensorId];
        return next;
      }

      return {
        ...prev,
        [sensorId]: {
          ...current,
          [field]: value,
          // Atualizamos o endTime logicamente apenas ao salvar, mas mantemos a estrutura
        }
      };
    });
  };

  const handleRandomize = () => {
    const newOverrides: Record<string, SimulationOverride> = {};
    const now = Date.now();

    sensorLocations.forEach(sensor => {
      let intensity: SimulationIntensity = 'Normal';
      const rand = Math.random();

      if (randomTarget === 'Alto') {
        // Foco em risco Alto: 60% Alto, 30% Moderado, 10% Normal
        if (rand < 0.6) intensity = 'Alto';
        else if (rand < 0.9) intensity = 'Moderado';
      } else if (randomTarget === 'Moderado') {
        // Foco em risco Moderado: 60% Moderado, 20% Alto, 20% Normal
        if (rand < 0.6) intensity = 'Moderado';
        else if (rand < 0.8) intensity = 'Alto';
      } else {
        // Caos: Distribuição quase igual
        if (rand < 0.33) intensity = 'Alto';
        else if (rand < 0.66) intensity = 'Moderado';
      }

      // Duração aleatória entre 30s e 90s para parecer orgânico
      const duration = Math.floor(Math.random() * 60) + 30;

      if (intensity !== 'Normal') {
        newOverrides[sensor.id] = {
          intensity,
          duration,
          endTime: 0 // Será calculado no save
        };
      }
    });

    setLocalOverrides(newOverrides);
    setIsEnabled(true); // Ativa a simulação automaticamente ao randomizar
  };

  const handleSave = () => {
    // Ao salvar, recalculamos o endTime baseado na duração escolhida para cada override ativo
    const now = Date.now();
    const updatedOverrides: Record<string, SimulationOverride> = {};

    Object.entries(localOverrides).forEach(([id, override]) => {
      if (override.intensity !== 'Normal') {
        updatedOverrides[id] = {
          ...override,
          endTime: now + (override.duration * 1000)
        };
      }
    });

    onSave({
      isEnabled,
      overrides: updatedOverrides
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="sim-modal-title">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-200 dark:border-slate-700 flex flex-col max-h-[90vh] animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-100 dark:bg-cyan-900/30 rounded-lg text-cyan-600 dark:text-cyan-400">
              <SlidersIcon className="w-6 h-6" />
            </div>
            <div>
                <h2 id="sim-modal-title" className="text-xl font-bold text-slate-800 dark:text-white">Painel de Simulação</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">Configure riscos manualmente por sensor</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-full transition-colors"
            aria-label="Fechar configurações"
          >
            <XIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Master Toggle */}
        <div className="p-4 bg-cyan-50/50 dark:bg-cyan-900/10 border-b border-cyan-100 dark:border-cyan-800/30 flex items-center justify-between shrink-0">
            <div className="flex flex-col">
                <span className="font-semibold text-slate-800 dark:text-slate-200">Simulação Ativa</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">Habilite para aplicar os riscos configurados abaixo.</span>
            </div>
            <button 
                onClick={() => setIsEnabled(!isEnabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 ${isEnabled ? 'bg-cyan-600' : 'bg-slate-300 dark:bg-slate-600'}`}
            >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
        </div>

        {/* Quick Config Section */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-700/50 bg-slate-50/30 dark:bg-slate-800/30 shrink-0">
             <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex flex-col">
                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Configuração Rápida</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">Gerar cenário aleatório para todos.</span>
                </div>
                
                <div className="flex items-center gap-2 w-full sm:w-auto">
                    <select 
                        value={randomTarget}
                        onChange={(e) => setRandomTarget(e.target.value as any)}
                        className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-sm rounded-md focus:ring-cyan-500 focus:border-cyan-500 p-2 w-full sm:w-auto"
                    >
                        <option value="Caos">Caos Total</option>
                        <option value="Alto">Crítico (Maioria Alto)</option>
                        <option value="Moderado">Alerta (Maioria Moderado)</option>
                    </select>

                    <button
                        onClick={handleRandomize}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 rounded-md text-sm font-medium transition-colors"
                    >
                        <ShuffleIcon className="w-4 h-4" />
                        Gerar
                    </button>
                </div>
             </div>
        </div>

        {/* Scrollable List */}
        <div className="p-6 overflow-y-auto flex-grow space-y-4">
          {sensorLocations.map((sensor) => {
            const override = localOverrides[sensor.id];
            const currentIntensity = override?.intensity || 'Normal';
            const currentDuration = override?.duration || 60;

            return (
              <div key={sensor.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg border border-slate-100 dark:border-slate-700/50 bg-slate-50/50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors">
                
                <div className="font-medium text-slate-700 dark:text-slate-200 min-w-[120px]">
                  {sensor.name}
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                  {/* Seletor de Intensidade */}
                  <div className="flex items-center gap-2">
                    <label htmlFor={`intensity-${sensor.id}`} className="sr-only">Risco</label>
                    <select
                        id={`intensity-${sensor.id}`}
                        value={currentIntensity}
                        onChange={(e) => handleOverrideChange(sensor.id, 'intensity', e.target.value)}
                        disabled={!isEnabled}
                        className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-sm rounded-md focus:ring-cyan-500 focus:border-cyan-500 block p-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <option value="Normal">Normal</option>
                        <option value="Moderado">Moderado</option>
                        <option value="Alto">Alto</option>
                    </select>
                  </div>

                  {/* Input de Duração */}
                  <div className="flex items-center gap-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md px-3 py-1.5">
                     <label htmlFor={`duration-${sensor.id}`} className="text-xs text-slate-500 dark:text-slate-400 uppercase font-bold">Tempo (s)</label>
                     <input
                        id={`duration-${sensor.id}`}
                        type="number"
                        min="5"
                        max="600"
                        value={currentDuration}
                        onChange={(e) => handleOverrideChange(sensor.id, 'duration', Number(e.target.value))}
                        disabled={!isEnabled || currentIntensity === 'Normal'}
                        className="w-16 bg-transparent border-none text-sm text-right focus:ring-0 text-slate-700 dark:text-slate-200 p-0 disabled:opacity-50"
                     />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-6 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3 shrink-0">
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-lg font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
              Cancelar
            </button>
          
            <button
                onClick={handleSave}
                className="px-5 py-2.5 rounded-lg font-medium text-white bg-cyan-600 hover:bg-cyan-700 focus:ring-4 focus:ring-cyan-500/30 transition-colors shadow-lg shadow-cyan-500/20"
            >
                Aplicar Configurações
            </button>
        </div>
      </div>
    </div>
  );
};

export default SimulationConfigModal;
