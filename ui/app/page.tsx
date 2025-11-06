'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type Status = 'idle' | 'listening' | 'processing' | 'speaking';

interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
  personaId?: string;
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

interface PersonaOption {
  id: string;
  name: string;
  description: string;
}

type PersonaSpeechPreset = {
  rate: number;
  pitch: number;
  decorate: (base: string) => string;
};

const DEFAULT_PERSONAS: PersonaOption[] = [
  {
    id: 'friendly_guide',
    name: 'Friendly Guide',
    description: 'Warm, upbeat helper who keeps things encouraging.',
  },
  {
    id: 'calm_concierge',
    name: 'Calm Concierge',
    description: 'Composed professional with a steady, reassuring presence.',
  },
  {
    id: 'energetic_host',
    name: 'Energetic Host',
    description: 'High-energy emcee who keeps the pace lively.',
  },
  {
    id: 'american_frontdesk',
    name: 'Front Desk Host',
    description: 'Welcoming American restaurant host with warm hospitality.',
  },
  {
    id: 'fine_dining_host',
    name: 'Fine Dining Host',
    description: "Poised maître d' with a refined, international accent.",
  },
];

const PERSONA_SPEECH_PRESETS: Record<string, PersonaSpeechPreset> = {
  friendly_guide: {
    rate: 1.05,
    pitch: 1.1,
    decorate: (base) => `${base} 😊`,
  },
  calm_concierge: {
    rate: 0.95,
    pitch: 0.9,
    decorate: (base) => `Certainly. ${base}`,
  },
  energetic_host: {
    rate: 1.18,
    pitch: 1.05,
    decorate: (base) => `${base} Let's keep the momentum going!`,
  },
  american_frontdesk: {
    rate: 1.02,
    pitch: 1.0,
    decorate: (base) => `Absolutely! ${base} I'll take care of things for you.`,
  },
  fine_dining_host: {
    rate: 0.98,
    pitch: 0.95,
    decorate: (base) => `It would be my pleasure. ${base}`,
  },
};

const DEFAULT_PERSONA_ID = DEFAULT_PERSONAS[0].id;

const RESPONSE_DELAY_MS = 1000;
const API_BASE_URL = 'http://localhost:4002';

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

const getSpeechPreset = (personaId: string): PersonaSpeechPreset => {
  return PERSONA_SPEECH_PRESETS[personaId] || PERSONA_SPEECH_PRESETS[DEFAULT_PERSONA_ID];
};

const generateFallbackResponse = (
  input: string,
  history: TranscriptEntry[],
  personaId: string
): string => {
  const normalized = input.trim().toLowerCase();
  const preset = getSpeechPreset(personaId);

  if (!normalized) {
    return preset.decorate("I didn't quite catch that. Could you try again?");
  }

  if (normalized.includes('hello') || normalized.includes('hi')) {
    return preset.decorate('Hello! What would you like to talk about today?');
  }

  if (normalized.includes('menu')) {
    return preset.decorate('Right now the specials are truffle risotto, grilled salmon, and a berry tart. What sounds good to you?');
  }

  if (normalized.includes('order')) {
    return preset.decorate('Sure thing. Tell me what you would like to order and I will make sure it is ready.');
  }

  if (normalized.includes('thank')) {
    return preset.decorate('You are very welcome. Happy to help whenever you need me!');
  }

  if (history.length >= 4) {
    const lastUserTurn = [...history].reverse().find((entry) => entry.role === 'user');
    if (lastUserTurn) {
    return preset.decorate(`Earlier you mentioned "${lastUserTurn.text}". Would you like to go deeper on that?`);
    }
  }

  const baseResponse = `You said: ${input}. I am still listening, what else should we cover?`;
  return preset.decorate(baseResponse);
};

export default function Home() {
  const [status, setStatus] = useState<Status>('idle');
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isBrowserSupported, setBrowserSupported] = useState<boolean | null>(null);
  const [liveUserTranscript, setLiveUserTranscript] = useState('');
  const [liveAssistantUtterance, setLiveAssistantUtterance] = useState('');
  const [personaOptions, setPersonaOptions] = useState<PersonaOption[]>(DEFAULT_PERSONAS);
  const [selectedPersona, setSelectedPersona] = useState<string>(DEFAULT_PERSONA_ID);
  const [personaNotice, setPersonaNotice] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStartingSession, setIsStartingSession] = useState(false);

  const activePersona = useMemo<PersonaOption>(() => {
    return personaOptions.find((option) => option.id === selectedPersona) || personaOptions[0];
  }, [personaOptions, selectedPersona]);

  const activeSpeechPreset = useMemo<PersonaSpeechPreset>(() => {
    return getSpeechPreset(selectedPersona);
  }, [selectedPersona]);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const isRecognitionActiveRef = useRef(false);
  const shouldListenRef = useRef(false);
  const pendingResponseTimerRef = useRef<number | null>(null);
  const lastUserUtteranceRef = useRef<string>('');
  const accumulatedTranscriptRef = useRef<string>('');
  const isSpeakingRef = useRef(false);
  const currentUtteranceRef = useRef<HTMLAudioElement | SpeechSynthesisUtterance | null>(null);
  const sessionPersonaRef = useRef<string | null>(null);
  const sessionDataRef = useRef<Record<string, any> | null>(null);
  const pendingSessionPromiseRef = useRef<Promise<string | null> | null>(null);
  const transcriptsRef = useRef<TranscriptEntry[]>([]);

  const buildApiUrl = (path: string, params?: Record<string, string | undefined>) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) {
          searchParams.append(key, value);
        }
      });
    }

    const query = searchParams.toString();
    return query ? `${API_BASE_URL}${path}?${query}` : `${API_BASE_URL}${path}`;
  };

  const createConversationSession = async (personaId: string): Promise<string> => {
    const response = await fetch(
      buildApiUrl('/conversation/start', { persona: personaId }),
      {
        method: 'POST',
      }
    );

    if (!response.ok) {
      throw new Error(`Conversation session failed with status ${response.status}`);
    }

    const data = await response.json();
    const newSessionId = data.session_id as string;
    setSessionId(newSessionId);
    sessionPersonaRef.current = (data.persona as string | undefined) || personaId;
    sessionDataRef.current = data.session_data ?? null;
    return newSessionId;
  };

  const ensureConversationSession = async (): Promise<string | null> => {
    if (sessionId && sessionPersonaRef.current === selectedPersona) {
      return sessionId;
    }

    if (pendingSessionPromiseRef.current) {
      try {
        return await pendingSessionPromiseRef.current;
      } catch {
        return null;
      }
    }

    const promise = createConversationSession(selectedPersona).finally(() => {
      pendingSessionPromiseRef.current = null;
    });

    pendingSessionPromiseRef.current = promise;
    return promise;
  };

  const stopConversation = useCallback(() => {
    shouldListenRef.current = false;

    clearPendingResponseTimer();

    // Stop any audio playback
    if (currentUtteranceRef.current) {
      if (currentUtteranceRef.current instanceof HTMLAudioElement) {
        currentUtteranceRef.current.pause();
        currentUtteranceRef.current.currentTime = 0;
      } else if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
        window.speechSynthesis.cancel();
      }
    }
    currentUtteranceRef.current = null;

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
  }, []);

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
    let cancelled = false;

    const loadPersonas = async () => {
      try {
        const response = await fetch(buildApiUrl('/personas'));
        if (!response.ok) {
          throw new Error(`Persona fetch failed: ${response.status}`);
        }

        const data = await response.json();
        if (!Array.isArray(data) || data.length === 0) {
          return;
        }

        if (!cancelled) {
          const normalized: PersonaOption[] = data.map((item: any) => ({
            id: item.id,
            name: item.name ?? item.id,
            description: item.description ?? '',
          }));

          setPersonaOptions(normalized);

          if (!normalized.some((option) => option.id === selectedPersona)) {
            setSelectedPersona(normalized[0].id);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setPersonaNotice('Using built-in persona presets (API unavailable).');
        }
        console.debug('Persona fetch failed, using defaults:', err);
      }
    };

    loadPersonas();

    return () => {
      cancelled = true;
    };
  }, [selectedPersona]);

  useEffect(() => {
    transcriptsRef.current = transcripts;
  }, [transcripts]);

  useEffect(() => {
    stopConversation();
    setTranscripts([]);
    setLiveAssistantUtterance('');
    setLiveUserTranscript('');
    setSessionId(null);
    setIsStartingSession(false);
    sessionPersonaRef.current = null;
    sessionDataRef.current = null;
    pendingSessionPromiseRef.current = null;
  }, [selectedPersona, stopConversation]);

  useEffect(() => {
    return () => {
      stopConversation();
    };
  }, [stopConversation]);

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
      // If recognition starts while AI is speaking, stop AI immediately
      // (This can happen if user starts speaking)
      if (isSpeakingRef.current) {
        // Stop audio playback
        if (currentUtteranceRef.current) {
          if (currentUtteranceRef.current instanceof HTMLAudioElement) {
            currentUtteranceRef.current.pause();
            currentUtteranceRef.current.currentTime = 0;
          } else if (typeof window !== 'undefined' && window.speechSynthesis) {
            window.speechSynthesis.cancel();
            window.speechSynthesis.cancel();
          }
        }
        currentUtteranceRef.current = null;
        isSpeakingRef.current = false;
        setLiveAssistantUtterance('');
        setStatus('listening');
        clearPendingResponseTimer();
      } else {
        setStatus('listening');
      }
      // Don't clear accumulated transcript here - it might restart during continuous recognition
      // We only clear when we process the transcript
    };

    recognition.onend = () => {
      isRecognitionActiveRef.current = false;
      
      // Fallback: If we have accumulated text but no timer is running, process it
      // (This handles cases where the timer might not have fired)
      const completeTranscript = accumulatedTranscriptRef.current.trim();
      
      if (completeTranscript && shouldListenRef.current && !pendingResponseTimerRef.current) {
        // Clear accumulated transcript
        accumulatedTranscriptRef.current = '';
        setLiveUserTranscript('');
        
        // Add to conversation history
        setTranscripts((prev) => [
          ...prev,
          {
            role: 'user',
            text: completeTranscript,
            timestamp: new Date(),
          },
        ]);
        
        setStatus('processing');
        
        // Process immediately since we're already past the delay point
        void deliverAgentResponse(completeTranscript);
      }
      
      // Allow restarting even while AI is speaking to support interruption
      if (shouldListenRef.current) {
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
    // Allow listening even while AI is speaking to support interruption
    const recognition = initialiseRecognition();

    try {
      recognition.start();
      isRecognitionActiveRef.current = true;
      if (!isSpeakingRef.current) {
        setStatus('listening');
      }
    } catch (err) {
      console.debug('Speech recognition start() ignored:', err);
    }
  };

  const restartListening = () => {
    window.setTimeout(() => {
      // Allow restarting even while AI is speaking to support interruption
      if (shouldListenRef.current && !isRecognitionActiveRef.current) {
        startListening();
      }
    }, 200);
  };

  const handleRecognitionResult = (event: SpeechRecognitionEvent) => {
    if (!event.results) {
      return;
    }

    // FIRST: Check if user is speaking while AI is speaking (interruption)
    // Check BOTH interim and final results - ANY speech detection = interrupt immediately
    let hasAnySpeech = false;
    let interruptDetected = false;

    // Check ALL results first to detect any speech
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result[0]) {
        const transcriptText = result[0].transcript;
        // ANY transcript text (even a single character) means user is speaking
        if (transcriptText && transcriptText.trim().length > 0) {
          hasAnySpeech = true;
          
          // If AI is speaking and we detect ANY user speech, interrupt IMMEDIATELY
          if (isSpeakingRef.current) {
            interruptDetected = true;
            break; // Stop checking, we need to interrupt NOW
          }
        }
      }
    }

    // CRITICAL: If user starts speaking while AI is speaking, stop AI IMMEDIATELY
    // Do this BEFORE processing any transcripts
    if (interruptDetected) {
      // Force stop audio playback immediately
      if (currentUtteranceRef.current) {
        if (currentUtteranceRef.current instanceof HTMLAudioElement) {
          currentUtteranceRef.current.pause();
          currentUtteranceRef.current.currentTime = 0;
        } else if (typeof window !== 'undefined' && window.speechSynthesis) {
          window.speechSynthesis.cancel();
          window.speechSynthesis.cancel();
          window.speechSynthesis.cancel();
        }
      }
      // Clear the current utterance reference
      currentUtteranceRef.current = null;
      isSpeakingRef.current = false;
      setLiveAssistantUtterance(''); // Clear the live utterance display immediately
      setStatus('listening');
      clearPendingResponseTimer(); // Cancel any pending responses
      // Clear old accumulated transcript since user is starting a new utterance
      accumulatedTranscriptRef.current = '';
      // Force UI update
      setLiveUserTranscript('');
    }

    // NOW: Process and accumulate transcripts (only if not interrupted)
    let currentTranscript = '';
    let hasFinalTranscript = false;

    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result[0]) {
        const transcriptText = result[0].transcript;
        
        if (result.isFinal) {
          currentTranscript += transcriptText;
          hasFinalTranscript = true;
          // Only accumulate if we didn't just interrupt (or if interrupt already handled)
          accumulatedTranscriptRef.current += transcriptText + ' ';
        } else {
          // Show interim results as user is speaking
          setLiveUserTranscript(transcriptText);
        }
      }
    }

    // When we get a final transcript, start/reset a timer
    // If no more speech comes within the delay period, process the accumulated transcript
    if (hasFinalTranscript && accumulatedTranscriptRef.current.trim()) {
      clearPendingResponseTimer();
      
      // Wait for user to finish speaking (1 second of silence)
      pendingResponseTimerRef.current = window.setTimeout(() => {
        pendingResponseTimerRef.current = null;
        
        if (!shouldListenRef.current) {
          return;
        }
        
        const completeTranscript = accumulatedTranscriptRef.current.trim();
        
        if (completeTranscript) {
          // Clear accumulated transcript
          accumulatedTranscriptRef.current = '';
          setLiveUserTranscript('');
          
          // Add to conversation history
          setTranscripts((prev) => [
            ...prev,
            {
              role: 'user',
              text: completeTranscript,
              timestamp: new Date(),
            },
          ]);
          
          setStatus('processing');
          
          // Process the complete transcript
          void deliverAgentResponse(completeTranscript);
        }
      }, RESPONSE_DELAY_MS);
    }
  };

  const deliverAgentResponse = async (userUtterance: string) => {
    if (!shouldListenRef.current) {
      return;
    }

    try {
      setStatus('processing');

      const ensuredSessionId = await ensureConversationSession();
      if (!ensuredSessionId) {
        throw new Error('Unable to establish a conversation session.');
      }

      const response = await fetch(buildApiUrl('/conversation/process'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: userUtterance,
          session_id: ensuredSessionId,
          persona: selectedPersona,
        }),
      });

      if (!response.ok) {
        throw new Error(`Conversation processing failed with status ${response.status}`);
      }

      const data = await response.json();
      let assistantText = typeof data.response === 'string' ? (data.response as string).trim() : '';
      if (!assistantText) {
        assistantText = generateFallbackResponse(
          userUtterance,
          transcriptsRef.current,
          selectedPersona
        );
      }

      if (!shouldListenRef.current) {
        return;
      }

      sessionDataRef.current = data.session_data ?? sessionDataRef.current;
      if (data.persona) {
        sessionPersonaRef.current = data.persona as string;
      }

      setTranscripts((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: assistantText,
          timestamp: new Date(),
          personaId: (data.persona as string | undefined) || selectedPersona,
        },
      ]);

      setLiveAssistantUtterance(assistantText);
      speakResponse(assistantText, activeSpeechPreset);
    } catch (err) {
      if (!shouldListenRef.current) {
        return;
      }

      console.error('Failed to fetch agent response:', err);
      const fallback = generateFallbackResponse(
        userUtterance,
        transcriptsRef.current,
        selectedPersona
      );

      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong while generating the response.'
      );

      setTranscripts((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: fallback,
          timestamp: new Date(),
          personaId: selectedPersona,
        },
      ]);

      setLiveAssistantUtterance(fallback);
      speakResponse(fallback, activeSpeechPreset);
    }
  };

  const speakResponse = async (text: string, preset: PersonaSpeechPreset) => {
    if (typeof window === 'undefined') {
      setError('Audio playback is not supported in this browser.');
      return;
    }

    // Cancel any existing speech immediately
    if (currentUtteranceRef.current) {
      if (currentUtteranceRef.current instanceof HTMLAudioElement) {
        currentUtteranceRef.current.pause();
        currentUtteranceRef.current.currentTime = 0;
      }
      currentUtteranceRef.current = null;
    }
    isSpeakingRef.current = false;

    // Keep recognition active while speaking to allow interruption
    // Don't stop recognition - let it continue listening
    const recognition = recognitionRef.current;
    if (recognition && !isRecognitionActiveRef.current && shouldListenRef.current) {
      // Only start recognition if it's not already active
      startListening();
    }

    try {
      // Call backend TTS API
      const apiUrl = buildApiUrl('/voice/text-to-speech');
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          persona: selectedPersona,
        }),
      });

      if (!response.ok) {
        throw new Error(`TTS API error: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (!data.success || !data.audio_base64) {
        throw new Error(data.error || 'TTS generation failed');
      }

      // Decode base64 audio
      const audioBytes = Uint8Array.from(atob(data.audio_base64), c => c.charCodeAt(0));
      
      // Determine audio format from response or default to wav
      const audioFormat = data.format || 'wav';
      const mimeType = audioFormat === 'mp3' ? 'audio/mpeg' : 'audio/wav';
      
      const audioBlob = new Blob([audioBytes], { type: mimeType });
      const audioUrl = URL.createObjectURL(audioBlob);

      // Create audio element
      const audio = new Audio(audioUrl);
      currentUtteranceRef.current = audio as any; // Store reference for cancellation
      
      // Apply playback rate (pitch is not supported by HTML5 Audio, but rate is)
      audio.playbackRate = preset.rate || 1.0;
      
      // Preload the audio to ensure it's ready
      audio.preload = 'auto';
      
      // Wait for audio to be ready before playing
      await new Promise<void>((resolve, reject) => {
        const cleanup = () => {
          audio.removeEventListener('canplaythrough', onCanPlay);
          audio.removeEventListener('error', onError);
          clearTimeout(timeoutId);
        };
        
        const onCanPlay = () => {
          cleanup();
          resolve();
        };
        
        const onError = (e: Event) => {
          cleanup();
          reject(new Error('Audio loading failed'));
        };
        
        audio.addEventListener('canplaythrough', onCanPlay);
        audio.addEventListener('error', onError);
        
        // If already can play, resolve immediately
        if (audio.readyState >= 3) { // HAVE_FUTURE_DATA or HAVE_ENOUGH_DATA
          cleanup();
          resolve();
          return;
        }
        
        // Timeout after 5 seconds
        const timeoutId = setTimeout(() => {
          cleanup();
          reject(new Error('Audio loading timeout'));
        }, 5000);
        
        // Force load
        audio.load();
      });

      audio.onplay = () => {
        // Only set speaking if this audio is still the current one
        if (currentUtteranceRef.current === audio) {
          isSpeakingRef.current = true;
          setStatus('speaking');
          // Ensure recognition is active for interruption
          if (recognition && !isRecognitionActiveRef.current && shouldListenRef.current) {
            startListening();
          }
        }
      };

      audio.onended = () => {
        // Only process if this is still the current audio
        if (currentUtteranceRef.current === audio) {
          isSpeakingRef.current = false;
          currentUtteranceRef.current = null;
          setLiveAssistantUtterance('');
          URL.revokeObjectURL(audioUrl); // Clean up
          if (shouldListenRef.current) {
            // Keep listening if not already active
            if (!isRecognitionActiveRef.current) {
              restartListening();
            }
            setStatus('listening');
          } else {
            setStatus('idle');
          }
        }
      };

      audio.onerror = (event) => {
        console.error('Audio playback error', event);
        if (currentUtteranceRef.current === audio) {
          isSpeakingRef.current = false;
          currentUtteranceRef.current = null;
          setLiveAssistantUtterance('');
          URL.revokeObjectURL(audioUrl); // Clean up
          if (shouldListenRef.current) {
            if (!isRecognitionActiveRef.current) {
              restartListening();
            }
            setStatus('listening');
          } else {
            setStatus('idle');
          }
        }
      };

      // Start playing - handle autoplay restrictions
      try {
        const playPromise = audio.play();
        if (playPromise !== undefined) {
          await playPromise;
        }
      } catch (playError: any) {
        // Handle autoplay restrictions
        if (playError.name === 'NotAllowedError' || playError.name === 'NotSupportedError') {
          console.error('Audio autoplay blocked:', playError);
          // User interaction required - try to play again after a short delay
          // or show a message to the user
          throw new Error(
            'Audio playback blocked by browser. Please interact with the page to enable audio.'
          );
        }
        throw playError;
      }
      
    } catch (error) {
      console.error('TTS error:', error);
      setError(`Failed to generate speech: ${error instanceof Error ? error.message : 'Unknown error'}`);
      isSpeakingRef.current = false;
      currentUtteranceRef.current = null;
      if (shouldListenRef.current) {
        if (!isRecognitionActiveRef.current) {
          restartListening();
        }
        setStatus('listening');
      } else {
        setStatus('idle');
      }
    }
  };

  const startConversation = async () => {
    if (status !== 'idle' || isStartingSession) {
      return;
    }

    if (isBrowserSupported === false) {
      setError('Your browser does not support the Web Speech API required for this voice agent.');
      return;
    }

    setError(null);
    setIsStartingSession(true);
    shouldListenRef.current = true;
    clearPendingResponseTimer();
    accumulatedTranscriptRef.current = ''; // Clear any previous transcript
    setStatus('processing');

    try {
      const ensuredSessionId = await ensureConversationSession();
      if (!ensuredSessionId) {
        throw new Error('Unable to create a conversation session.');
      }

      startListening();
    } catch (err: any) {
      console.error('Failed to start conversation:', err);
      setError(err.message || 'Failed to start conversation');
      shouldListenRef.current = false;
      stopConversation();
    } finally {
      setIsStartingSession(false);
    }
  };

  const handleInterruptClick = () => {
    if (isSpeakingRef.current) {
      // Stop audio playback
      if (currentUtteranceRef.current) {
        if (currentUtteranceRef.current instanceof HTMLAudioElement) {
          currentUtteranceRef.current.pause();
          currentUtteranceRef.current.currentTime = 0;
        } else if (typeof window !== 'undefined' && window.speechSynthesis) {
          window.speechSynthesis.cancel();
        }
      }
      currentUtteranceRef.current = null;
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
              Speak naturally. The agent listens, waits 1 second after you finish, and responds aloud. Interrupt any time to take back the mic.
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

          <section className="mb-8">
            <label className="block text-sm font-semibold uppercase tracking-wide text-slate-300 mb-2">
              Persona
            </label>
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <select
                value={selectedPersona}
                onChange={(event) => setSelectedPersona(event.target.value)}
                className="w-full sm:w-64 rounded-2xl border border-slate-600 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400/40"
              >
                {personaOptions.map((persona) => (
                  <option key={persona.id} value={persona.id}>
                    {persona.name}
                  </option>
                ))}
              </select>
              <div className="text-xs text-slate-400 flex-1">
                {activePersona?.description || 'Choose how the assistant should sound and respond.'}
              </div>
            </div>
            {personaNotice && (
              <p className="mt-2 text-xs text-amber-300">{personaNotice}</p>
            )}
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
              disabled={status !== 'idle' || isStartingSession}
              className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition ${
                status === 'idle' && !isStartingSession
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
                Click "Start conversation" and begin speaking. The agent will wait for a 1 second pause before replying.
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
                        {entry.role === 'user'
                          ? 'You'
                          : personaOptions.find((option) => option.id === entry.personaId)?.name || 'Assistant'}
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
