import React from 'react';
import { SunIcon, MoonIcon } from './Icons.tsx';

interface ThemeToggleProps {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ theme, toggleTheme }) => {
  return (
    <button
      onClick={toggleTheme}
      className="p-3 bg-slate-200/60 dark:bg-slate-700/50 rounded-full hover:bg-slate-300/70 dark:hover:bg-slate-600/70 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:focus:ring-cyan-400 transition-colors"
      aria-label={`Mudar para tema ${theme === 'light' ? 'escuro' : 'claro'}`}
    >
      {theme === 'light' ? (
        <MoonIcon className="w-5 h-5 text-slate-800" />
      ) : (
        <SunIcon className="w-5 h-5 text-yellow-400" />
      )}
    </button>
  );
};

export default ThemeToggle;