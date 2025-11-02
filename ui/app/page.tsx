'use client';

import { useEffect, useRef, useState } from 'react';

type Status = 'idle' | 'listening' | 'processing' | 'speaking';

interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

type SpeechRecognitionResult = {
  isFinal: boolean;
  0: {
    transcript: string;
    confidence: number;
  };
};

type SpeechRecognitionEvent = {
  resultIndex: number;
  results: Array<SpeechRecognitionResult>;
};

type SpeechRecognitionErrorEvent = {
  error: string;
  message?: string;
};

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

const RESPONSE_DELAY_MS = 1500;

const getSpeechRecognitionConstructor = (): (() => SpeechRecognitionInstance) | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  const ctor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!ctor) {
    return null;
  }

  return () => new ctor();
};

const generateAgentResponse = (input: string, history: TranscriptEntry[]): string => {
  const normalized = input.trim().toLowerCase();

  if (!normalized) {
    return "I didn't quite catch that. Could you try again?";
  }

  if (normalized.includes('hello') || normalized.includes('hi')) {
    return 'Hello! What would you like to talk about today?';
  }

  if (normalized.includes('menu')) {
    return 'Right now the specials are truffle risotto, grilled salmon, and a berry tart. What sounds good to you?';
  }

  if (normalized.includes('order')) {
    return 'Sure thing. Tell me what you would like to order and I will make sure it is ready.';
  }

  if (normalized.includes('thank')) {
    return 'You are very welcome. Happy to help whenever you need me!';
  }

  if (history.length >= 4) {
    const lastUserTurn = [...history].reverse().find((entry) => entry.role === 'user');
    if (lastUserTurn) {
      return `Earlier you mentioned "${lastUserTurn.text}". Would you like to go deeper on that?`;
    }
  }

  return `You said: ${input}. I am still listening, what else should we cover?`;
};

export default function Home() {
  const [status, setStatus] = useState<Status>('idle');
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isBrowserSupported, setBrowserSupported] = useState<boolean | null>(null);
  const [liveUserTranscript, setLiveUserTranscript] = useState('');
  const [liveAssistantUtterance, setLiveAssistantUtterance] = useState('');

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const isRecognitionActiveRef = useRef(false);
  const shouldListenRef = useRef(false);
  const pendingResponseTimerRef = useRef<number | null>(null);
  const lastUserUtteranceRef = useRef<string>('');
  const isSpeakingRef = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined') {
      setBrowserSupported(null);
      return;
    }

    const recognitionCtor = getSpeechRecognitionConstructor();
    const synthesisSupported = 'speechSynthesis' in window;
    setBrowserSupported(Boolean(recognitionCtor && synthesisSupported));
  }, []);

  useEffect(() => {
    return () => {
      stopConversation();
    };
  }, []);

  const clearPendingResponseTimer = () => {
    if (pendingResponseTimerRef.current !== null) {
      window.clearTimeout(pendingResponseTimerRef.current);
      pendingResponseTimerRef.current = null;
    }
  };

  const initialiseRecognition = (): SpeechRecognitionInstance => {
    if (recognitionRef.current) {
      return recognitionRef.current;
    }

    const recognitionCtor = getSpeechRecognitionConstructor();
    if (!recognitionCtor) {
      throw new Error('Speech recognition is not supported in this browser.');
    }

    const recognition = recognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onresult = handleRecognitionResult;
    recognition.onstart = () => {
      isRecognitionActiveRef.current = true;
      if (!isSpeakingRef.current) {
        setStatus('listening');
      }
    };

    recognition.onend = () => {
      isRecognitionActiveRef.current = false;
      if (shouldListenRef.current && !isSpeakingRef.current) {
        restartListening();
      }
    };

    recognition.onerror = (event) => {
      const err = event as SpeechRecognitionErrorEvent;
      if (err.error === 'no-speech' || err.error === 'aborted') {
        if (shouldListenRef.current && !isSpeakingRef.current) {
          restartListening();
        }
        return;
      }

      console.error('Speech recognition error', err);
      setError(err.message || err.error || 'Speech recognition error');
    };

    recognitionRef.current = recognition;
    return recognition;
  };

  const startListening = () => {
    if (isSpeakingRef.current) {
      return;
    }

    const recognition = initialiseRecognition();

    try {
      recognition.start();
      isRecognitionActiveRef.current = true;
    } catch (err) {
      console.debug('Speech recognition start() ignored:', err);
    }
  };

  const restartListening = () => {
    window.setTimeout(() => {
      if (shouldListenRef.current && !isRecognitionActiveRef.current && !isSpeakingRef.current) {
        startListening();
      }
    }, 200);
  };

  const handleRecognitionResult = (event: SpeechRecognitionEvent) => {
    if (!event.results) {
      return;
    }

    let finalTranscript = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result[0]) {
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          setLiveUserTranscript(result[0].transcript);
        }
      }
    }

    const cleanedTranscript = finalTranscript.trim();
    if (!cleanedTranscript) {
      return;
    }

    setLiveUserTranscript('');

    if (isSpeakingRef.current) {
      window.speechSynthesis.cancel();
      isSpeakingRef.current = false;
    }

    clearPendingResponseTimer();
    lastUserUtteranceRef.current = cleanedTranscript;
    setTranscripts((prev) => [
      ...prev,
      {
        role: 'user',
        text: cleanedTranscript,
        timestamp: new Date(),
      },
    ]);

    setStatus('processing');

    pendingResponseTimerRef.current = window.setTimeout(() => {
      pendingResponseTimerRef.current = null;
      deliverAgentResponse(lastUserUtteranceRef.current);
    }, RESPONSE_DELAY_MS);
  };

  const deliverAgentResponse = (userUtterance: string) => {
    const response = generateAgentResponse(userUtterance, transcripts);
    setTranscripts((prev) => [
      ...prev,
      {
        role: 'assistant',
        text: response,
        timestamp: new Date(),
      },
    ]);

    setLiveAssistantUtterance(response);
    speakResponse(response);
  };

  const speakResponse = (text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setError('Speech synthesis is not supported in this browser.');
      return;
    }

    window.speechSynthesis.cancel();

    const recognition = recognitionRef.current;
    if (recognition && isRecognitionActiveRef.current) {
      recognition.stop();
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.pitch = 1;
    utterance.rate = 1;
    utterance.onstart = () => {
      isSpeakingRef.current = true;
      setStatus('speaking');
    };

    utterance.onend = () => {
      isSpeakingRef.current = false;
      setLiveAssistantUtterance('');
      if (shouldListenRef.current) {
        restartListening();
      } else {
        setStatus('idle');
      }
    };

    utterance.onerror = (event) => {
      console.error('Speech synthesis error', event);
      isSpeakingRef.current = false;
      setLiveAssistantUtterance('');
      if (shouldListenRef.current) {
        restartListening();
      } else {
        setStatus('idle');
      }
    };

    window.speechSynthesis.speak(utterance);
  };

  const startConversation = () => {
    if (status !== 'idle') {
      return;
    }

    if (isBrowserSupported === false) {
      setError('Your browser does not support the Web Speech API required for this voice agent.');
      return;
    }

    try {
      setError(null);
      shouldListenRef.current = true;
      clearPendingResponseTimer();
      startListening();
    } catch (err: any) {
      console.error('Failed to start conversation:', err);
      setError(err.message || 'Failed to start conversation');
      stopConversation();
    }
  };

  const stopConversation = () => {
    shouldListenRef.current = false;

    clearPendingResponseTimer();

    if (typeof window !== 'undefined') {
      window.speechSynthesis.cancel();
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.debug('Speech recognition stop() ignored:', err);
      }
    }

    isRecognitionActiveRef.current = false;
    isSpeakingRef.current = false;
    setStatus('idle');
  };

  const handleInterruptClick = () => {
    if (isSpeakingRef.current) {
      window.speechSynthesis.cancel();
      isSpeakingRef.current = false;
      setStatus('listening');
      if (shouldListenRef.current) {
        restartListening();
      }
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-700 text-white">
      <div className="max-w-3xl mx-auto py-12 px-6">
        <div className="bg-slate-800/70 backdrop-blur rounded-3xl border border-slate-700 shadow-2xl p-8">
          <header className="mb-8">
            <h1 className="text-4xl font-bold leading-tight">🎧 Local Voice Agent Playground</h1>
            <p className="text-slate-300 mt-2">
              Speak naturally. The agent listens, waits 1.5 seconds after you finish, and responds aloud. Interrupt any time to take back the mic.
            </p>
          </header>

          <section className="mb-6">
            <div className="flex items-center gap-3">
              <span
                className={`inline-flex h-3 w-3 rounded-full shadow transition-colors duration-300 ${
                  status === 'speaking'
                    ? 'bg-emerald-400 animate-pulse'
                    : status === 'processing'
                    ? 'bg-amber-300 animate-pulse'
                    : status === 'listening'
                    ? 'bg-sky-400 animate-pulse'
                    : 'bg-slate-500'
                }`}
              />
              <span className="uppercase tracking-wide text-xs font-semibold text-slate-300">
                {status === 'idle' && 'Idle'}
                {status === 'listening' && 'Listening'}
                {status === 'processing' && 'Thinking'}
                {status === 'speaking' && 'Speaking'}
              </span>
            </div>
          </section>

          {isBrowserSupported === false && (
            <div className="mb-6 rounded-xl border border-red-400/40 bg-red-500/10 p-4 text-red-100">
              <strong className="block font-semibold">Browser not supported</strong>
              <p className="text-sm mt-1">
                Your browser does not support the Web Speech API. Please try Chrome on desktop for the best experience.
              </p>
            </div>
          )}

          {error && (
            <div className="mb-6 rounded-xl border border-red-400/40 bg-red-500/10 p-4 text-red-100">
              <strong className="block font-semibold">Something went wrong</strong>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          <section className="mb-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={startConversation}
              disabled={status !== 'idle'}
              className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition ${
                status === 'idle'
                  ? 'bg-emerald-500 text-white hover:bg-emerald-400'
                  : 'bg-slate-600 text-slate-300 cursor-not-allowed'
              }`}
            >
              <span>🎙️</span>
              Start conversation
            </button>

            <button
              type="button"
              onClick={stopConversation}
              disabled={status === 'idle'}
              className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition ${
                status !== 'idle'
                  ? 'bg-rose-500 text-white hover:bg-rose-400'
                  : 'bg-slate-600 text-slate-300 cursor-not-allowed'
              }`}
            >
              <span>⏹️</span>
              Stop
            </button>

            <button
              type="button"
              onClick={handleInterruptClick}
              disabled={!isSpeakingRef.current}
              className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition ${
                isSpeakingRef.current
                  ? 'bg-amber-500 text-white hover:bg-amber-400'
                  : 'bg-slate-600 text-slate-300 cursor-not-allowed'
              }`}
            >
              <span>✋</span>
              Interrupt response
            </button>
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 mb-6">
            <h2 className="text-lg font-semibold text-slate-200 mb-4">Live Activity</h2>
            <div className="space-y-3 text-sm">
              <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 px-4 py-3">
                <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400 mb-1">
                  <span className="font-semibold text-slate-200">You are saying</span>
                  <span className="text-slate-500">real-time</span>
                </div>
                <p className={`text-slate-100 ${liveUserTranscript ? 'opacity-100' : 'opacity-40'}`}>
                  {liveUserTranscript || 'Silence...'}
                </p>
              </div>
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
                <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400 mb-1">
                  <span className="font-semibold text-slate-200">Assistant is saying</span>
                  <span className="text-slate-500">real-time</span>
                </div>
                <p className={`text-slate-100 ${liveAssistantUtterance ? 'opacity-100' : 'opacity-40'}`}>
                  {liveAssistantUtterance || 'Waiting...'}
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-200">Conversation</h2>
              <span className="text-xs uppercase tracking-widest text-slate-400">
                {transcripts.length === 0 ? 'waiting' : `${transcripts.length} turns`}
              </span>
            </div>

            {transcripts.length === 0 ? (
              <p className="text-sm text-slate-400">
                Click “Start conversation” and begin speaking. The agent will wait for a 1.5 second pause before replying.
              </p>
            ) : (
              <div className="max-h-96 space-y-3 overflow-y-auto pr-2">
                {transcripts.map((entry, index) => (
                  <article
                    key={`${entry.role}-${entry.timestamp.getTime()}-${index}`}
                    className={`flex flex-col gap-2 rounded-2xl px-4 py-3 text-sm shadow-sm transition ${
                      entry.role === 'user'
                        ? 'ml-10 bg-sky-500/10 text-sky-100 border border-sky-500/20'
                        : 'mr-10 bg-emerald-500/10 text-emerald-100 border border-emerald-500/20'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
                      <span className="font-semibold text-slate-300">
                        {entry.role === 'user' ? 'You' : 'Assistant'}
                      </span>
                      <span>{entry.timestamp.toLocaleTimeString()}</span>
                    </div>
                    <p className="leading-relaxed text-slate-100">{entry.text}</p>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
