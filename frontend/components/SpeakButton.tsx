
import React from 'react';
import { PlayCircleIcon, StopCircleIcon } from './Icons.tsx';
import { useTTS } from '../hooks/useTTS.ts';

interface SpeakButtonProps {
  text: string;
  className?: string;
  label?: string;
}

const SpeakButton: React.FC<SpeakButtonProps> = ({ text, className, label = "Ouvir informações" }) => {
  const { speak, cancel, isSpeaking } = useTTS();

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // Previne cliques acidentais se o card for clicável
    if (isSpeaking) {
      cancel();
    } else {
      speak(text);
    }
  };

  return (
    <button
      onClick={handleClick}
      className={`p-2 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
        isSpeaking 
          ? 'text-red-600 hover:text-red-700 bg-red-100 dark:bg-red-900/30 focus:ring-red-500' 
          : 'text-cyan-600 hover:text-cyan-700 hover:bg-cyan-50 dark:text-cyan-400 dark:hover:bg-cyan-900/30 focus:ring-cyan-500'
      } ${className || ''}`}
      aria-label={isSpeaking ? "Parar leitura" : label}
      title={isSpeaking ? "Parar leitura" : label}
    >
      {isSpeaking ? (
        <StopCircleIcon className="w-6 h-6" />
      ) : (
        <PlayCircleIcon className="w-6 h-6" />
      )}
    </button>
  );
};

export default SpeakButton;
