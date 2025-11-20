
import { useState, useCallback, useEffect, useRef } from 'react';

export const useTTS = () => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const cancel = useCallback(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      return;
    }

    if (!activeUtteranceRef.current) {
      return;
    }

    window.speechSynthesis.cancel();
    activeUtteranceRef.current = null;
    setIsSpeaking(false);
  }, []);

  const speak = useCallback((text: string) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      console.warn("API SpeechSynthesis não suportada neste navegador.");
      return;
    }

    // Cancela qualquer fala anterior pendente antes de iniciar uma nova
    if (window.speechSynthesis.speaking || window.speechSynthesis.pending) {
      window.speechSynthesis.cancel();
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'pt-BR';
    utterance.rate = 1;
    utterance.pitch = 1;
    activeUtteranceRef.current = utterance;

    // Tenta encontrar uma voz em Português do Brasil
    const voices = window.speechSynthesis.getVoices();
    const ptVoice = voices.find(v => v.lang === 'pt-BR');
    if (ptVoice) {
      utterance.voice = ptVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => {
      if (activeUtteranceRef.current === utterance) {
        activeUtteranceRef.current = null;
      }
      setIsSpeaking(false);
    };
    utterance.onerror = () => {
      if (activeUtteranceRef.current === utterance) {
        activeUtteranceRef.current = null;
      }
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  // Garante que o listener de vozes seja atualizado (necessário em alguns navegadores)
  useEffect(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = () => {
        // Força re-render ou apenas garante que as vozes carregaram
      };
    }
    return () => {
      if (activeUtteranceRef.current) {
        cancel();
      }
    };
  }, [cancel]);

  return { speak, cancel, isSpeaking };
};
