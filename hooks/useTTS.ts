import { useState, useCallback, useEffect, useRef } from 'react';

export const useTTS = () => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const pendingTextRef = useRef<string | null>(null);

  const cancel = useCallback(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    if (!activeUtteranceRef.current) return;

    window.speechSynthesis.cancel();
    activeUtteranceRef.current = null;
    pendingTextRef.current = null;
    setIsSpeaking(false);
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (typeof window === 'undefined' || !window.speechSynthesis) {
        console.warn('API SpeechSynthesis nao suportada neste navegador.');
        return;
      }

      // If already speaking same text, keep going
      if (activeUtteranceRef.current && activeUtteranceRef.current.text === text && isSpeaking) {
        return;
      }

      // If speaking other text, queue this one
      if (isSpeaking) {
        pendingTextRef.current = text;
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'pt-BR';
      utterance.rate = 1;
      utterance.pitch = 1;
      activeUtteranceRef.current = utterance;

      // Pick a pt-BR voice if available
      const voices = window.speechSynthesis.getVoices();
      const ptVoice = voices.find((v) => v.lang === 'pt-BR');
      if (ptVoice) utterance.voice = ptVoice;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => {
        if (activeUtteranceRef.current === utterance) {
          activeUtteranceRef.current = null;
        }
        setIsSpeaking(false);
        if (pendingTextRef.current) {
          const nextText = pendingTextRef.current;
          pendingTextRef.current = null;
          setTimeout(() => speak(nextText), 0);
        }
      };
      utterance.onerror = () => {
        if (activeUtteranceRef.current === utterance) {
          activeUtteranceRef.current = null;
        }
        pendingTextRef.current = null;
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    },
    [isSpeaking]
  );

  useEffect(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = () => {
        /* noop: ensures voices load */
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

