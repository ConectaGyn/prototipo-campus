
import type { RiskLevel } from '../types.ts';

// Contexto de áudio singleton para evitar recriação excessiva
let audioCtx: AudioContext | null = null;

const getAudioContext = () => {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
  return audioCtx;
};

const playTone = (freq: number, type: OscillatorType, duration: number, startTime: number, vol: number = 0.1) => {
  const ctx = getAudioContext();
  const osc = ctx.createOscillator();
  const gainNode = ctx.createGain();

  osc.type = type;
  osc.frequency.setValueAtTime(freq, startTime);
  
  gainNode.gain.setValueAtTime(0, startTime);
  gainNode.gain.linearRampToValueAtTime(vol, startTime + 0.05); // Attack
  gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + duration); // Decay

  osc.connect(gainNode);
  gainNode.connect(ctx.destination);

  osc.start(startTime);
  osc.stop(startTime + duration);
};

export const playRiskSound = (level: RiskLevel) => {
  const ctx = getAudioContext();
  // Resume context if suspended (common browser policy)
  if (ctx.state === 'suspended') {
    ctx.resume();
  }
  
  const now = ctx.currentTime;

  switch (level) {
    case 'Alto':
    case 'Muito Alto':
      // Som de alerta urgente (dois tons rápidos)
      playTone(660, 'square', 0.2, now, 0.1);
      playTone(550, 'square', 0.4, now + 0.25, 0.1);
      break;
    
    case 'Moderado':
      // Som de atenção (tom único)
      playTone(440, 'sine', 0.4, now, 0.1);
      break;
    
    case 'Baixo':
      // Som de confirmação positivo (acorde simples ascendente)
      playTone(523.25, 'sine', 0.3, now, 0.05);      // C5
      playTone(659.25, 'sine', 0.3, now + 0.1, 0.05); // E5
      playTone(783.99, 'sine', 0.4, now + 0.2, 0.05); // G5
      break;
      
    default:
      break;
  }
};
