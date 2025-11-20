
import React, { useEffect, useRef } from 'react';
import type { RiskAlert } from '../types.ts';
import { playRiskSound } from '../utils/soundUtils.ts';
import SpeakButton from './SpeakButton.tsx';
import { useTTS } from '../hooks/useTTS.ts';

interface AlertCardProps {
  alert: RiskAlert;
  soundEnabled: boolean;
}

const AlertCard: React.FC<AlertCardProps> = ({ alert, soundEnabled }) => {
  const prevAlertLevel = useRef<string | null>(null);
  const { speak } = useTTS();

  useEffect(() => {
    // Toca o som se o nível do alerta mudou em relação ao anterior (ou na montagem inicial)
    // e se o som estiver habilitado.
    if (soundEnabled && alert.level !== prevAlertLevel.current) {
      playRiskSound(alert.level);
      
      // Se o nível for crítico (Alto ou Moderado), lê o alerta automaticamente após o som
      if (alert.level === 'Alto' || alert.level === 'Moderado') {
        // Texto simplificado: "Atenção." + Mensagem completa (que já contém níveis e locais)
        const autoSpeakText = `Atenção. ${alert.message}`;
        
        // Pequeno delay (1.2s) para não sobrepor o som de alerta inicial
        setTimeout(() => {
          speak(autoSpeakText);
        }, 1200);
      }

      prevAlertLevel.current = alert.level;
    }
  }, [alert, soundEnabled, speak]);

  const alertText = `Atenção. Nível de risco ${alert.level}. ${alert.message}`;

  return (
    <div 
      role="alert" 
      aria-live="assertive"
      className={`relative p-6 rounded-xl shadow-lg flex items-center space-x-6 border-2 ${alert.color}`}
    >
      <div className="flex-shrink-0" aria-hidden="true">
        {alert.icon}
      </div>
      <div className="flex-grow">
        <div className="text-xl font-bold text-white">
            <span className="sr-only">Nível de Risco: </span>
            {alert.level}
        </div>
        <p className="text-white/90 pr-8">{alert.message}</p>
      </div>
      <div className="absolute top-4 right-4">
        <SpeakButton 
            text={alertText} 
            className="text-white hover:text-white hover:bg-white/20 dark:text-white dark:hover:bg-white/20 focus:ring-white" 
            label="Ouvir alerta"
        />
      </div>
    </div>
  );
};

export default AlertCard;
