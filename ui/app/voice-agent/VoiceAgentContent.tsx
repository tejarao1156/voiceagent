'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Square, Volume2, Settings, AlertCircle } from 'lucide-react'
import { Conversation } from '@/components/Conversation'
import { ConversationMessage } from '@/lib/store'

// Constants
const API_BASE_URL = '' // Use relative URLs for proxy
const RESPONSE_DELAY_MS = 800 // Pause detection delay
const DEFAULT_PROMPT = "You are a friendly and helpful voice agent. Your role is to engage in natural, helpful conversations with users, provide useful information and assistance, and be conversational and natural."

// Status types
type Status = 'idle' | 'listening' | 'processing' | 'speaking'

// Speech Recognition types
interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  abort: () => void
  onresult: (event: SpeechRecognitionEvent) => void
  onstart: () => void
  onend: () => void
  onerror: (event: SpeechRecognitionErrorEvent) => void
}

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognitionErrorEvent {
  error: string
  message: string
}

declare global {
  interface Window {
    SpeechRecognition: {
      new (): SpeechRecognition
    }
    webkitSpeechRecognition: {
      new (): SpeechRecognition
    }
  }
}

export default function VoiceAgentContent() {
  // State management
  const [status, setStatus] = useState<Status>('idle')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [selectedPrompt, setSelectedPrompt] = useState(DEFAULT_PROMPT)
  const [transcripts, setTranscripts] = useState<ConversationMessage[]>([])
  const [liveUserTranscript, setLiveUserTranscript] = useState('')
  const [liveAssistantUtterance, setLiveAssistantUtterance] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [browserSupported, setBrowserSupported] = useState(true)
  const [audioUnlocked, setAudioUnlocked] = useState(false)

  // Recognition state
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const isRecognitionActiveRef = useRef(false)
  const shouldListenRef = useRef(false)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const isSpeakingRef = useRef(false)
  const isProcessingRef = useRef(false)
  const hasInterruptedRef = useRef(false)
  const accumulatedTranscriptRef = useRef('')
  const pendingResponseTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Check browser support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setBrowserSupported(false)
      setError('Your browser does not support speech recognition. Please use Chrome or Edge.')
      return
    }

    // Initialize recognition
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      isRecognitionActiveRef.current = true
      if (shouldListenRef.current) {
        setStatus('listening')
      }
    }

    recognition.onend = () => {
      isRecognitionActiveRef.current = false
      // Auto-restart if we should still be listening
      if (shouldListenRef.current && !isSpeakingRef.current) {
        setTimeout(() => {
          if (shouldListenRef.current && !isRecognitionActiveRef.current && !isSpeakingRef.current) {
            recognition.start()
          }
        }, 50)
      } else if (!shouldListenRef.current) {
        setStatus('idle')
      }
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('Recognition error:', event.error)
      if (event.error === 'no-speech') {
        // This is normal, just restart
        if (shouldListenRef.current && !isRecognitionActiveRef.current) {
          setTimeout(() => recognition.start(), 100)
        }
      } else if (event.error === 'not-allowed') {
        setError('Microphone permission denied. Please allow microphone access.')
        setStatus('idle')
        shouldListenRef.current = false
      } else {
        setError(`Recognition error: ${event.error}`)
      }
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      handleRecognitionResult(event)
    }

    recognitionRef.current = recognition
  }, [])

  // Handle recognition results
  const handleRecognitionResult = useCallback((event: SpeechRecognitionEvent) => {
    if (!event.results) return

    // Check for interrupt first
    if (isSpeakingRef.current && !hasInterruptedRef.current) {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result[0] && result[0].transcript.trim().length > 0) {
          handleInterruptDetected()
          break
        }
      }
    }

    // Process transcript results
    let hasFinalTranscript = false
    let hasInterimSpeech = false

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i]
      if (!result[0]) continue

      const transcriptText = result[0].transcript

      if (result.isFinal) {
        if (transcriptText.trim()) {
          accumulatedTranscriptRef.current += transcriptText + ' '
          hasFinalTranscript = true
        }
      } else {
        if (transcriptText.trim()) {
          setLiveUserTranscript(transcriptText)
          hasInterimSpeech = true
        }
      }
    }

    // Schedule response after pause
    if (hasFinalTranscript && accumulatedTranscriptRef.current.trim()) {
      scheduleResponse()
    } else if (hasInterimSpeech) {
      clearPendingTimer()
    }
  }, [])

  // Schedule response after pause
  const scheduleResponse = useCallback(() => {
    clearPendingTimer()

    const completeTranscript = accumulatedTranscriptRef.current.trim()
    if (!completeTranscript) return

    pendingResponseTimerRef.current = setTimeout(() => {
      pendingResponseTimerRef.current = null

      if (!shouldListenRef.current || isProcessingRef.current || isSpeakingRef.current) return

      const transcript = accumulatedTranscriptRef.current.trim()
      if (transcript) {
        // Add to transcript history
        setTranscripts(prev => [...prev, {
          role: 'user',
          text: transcript,
          timestamp: new Date()
        }])

        // Clear state
        accumulatedTranscriptRef.current = ''
        setLiveUserTranscript('')

        // Process the transcript
        processTranscript(transcript)
      }
    }, RESPONSE_DELAY_MS)
  }, [])

  // Clear pending timer
  const clearPendingTimer = useCallback(() => {
    if (pendingResponseTimerRef.current) {
      clearTimeout(pendingResponseTimerRef.current)
      pendingResponseTimerRef.current = null
    }
  }, [])

  // Handle interrupt
  const handleInterruptDetected = useCallback(() => {
    if (!isSpeakingRef.current) return

    console.log('🔴 Interrupt detected - stopping AI')
    hasInterruptedRef.current = true
    stopAudio()
    setStatus('listening')
    clearPendingTimer()

    // Clear accumulated transcript
    accumulatedTranscriptRef.current = ''
    setLiveUserTranscript('')
  }, [])

  // Unlock audio
  const unlockAudio = useCallback(async () => {
    if (!audioUnlocked) {
      try {
        const silentAudio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=')
        silentAudio.volume = 0
        await silentAudio.play()
        silentAudio.pause()
        setAudioUnlocked(true)
      } catch (e) {
        console.warn('Could not unlock audio:', e)
      }
    }
  }, [audioUnlocked])

  // Start conversation
  const startConversation = useCallback(async () => {
    try {
      setError(null)
      await unlockAudio()

      // Create session
      const promptParam = encodeURIComponent(selectedPrompt.trim() || DEFAULT_PROMPT)
      const response = await fetch(`${API_BASE_URL}/conversation/start?prompt=${promptParam}`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error('Failed to start conversation')
      }

      const data = await response.json()
      setSessionId(data.session_id)

      // Start listening
      shouldListenRef.current = true
      if (recognitionRef.current && !isRecognitionActiveRef.current) {
        recognitionRef.current.start()
      }
    } catch (err: any) {
      setError(err.message || 'Failed to start conversation')
      setStatus('idle')
    }
  }, [selectedPrompt, unlockAudio])

  // Stop conversation
  const stopConversation = useCallback(() => {
    shouldListenRef.current = false
    clearPendingTimer()
    stopAudio()

    if (recognitionRef.current && isRecognitionActiveRef.current) {
      recognitionRef.current.stop()
    }

    setStatus('idle')
    setLiveUserTranscript('')
    setLiveAssistantUtterance('')
    accumulatedTranscriptRef.current = ''
  }, [clearPendingTimer])

  // Process transcript
  const processTranscript = useCallback(async (transcript: string) => {
    if (isProcessingRef.current) return

    isProcessingRef.current = true
    setStatus('processing')

    try {
      const response = await fetch(`${API_BASE_URL}/conversation/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: transcript,
          session_id: sessionId,
          prompt: selectedPrompt.trim() || DEFAULT_PROMPT
        })
      })

      if (!response.ok) {
        throw new Error('Failed to process conversation')
      }

      const data = await response.json()
      const assistantText = data.response.trim()

      // Add to conversation history
      setTranscripts(prev => [...prev, {
        role: 'assistant',
        text: assistantText,
        timestamp: new Date()
      }])

      // Display live utterance
      setLiveAssistantUtterance(assistantText)

      // Convert to speech and play
      await speakResponse(assistantText)
    } catch (err: any) {
      setError(err.message || 'Failed to process conversation')
      setStatus('listening')
    } finally {
      isProcessingRef.current = false
    }
  }, [sessionId, selectedPrompt])

  // Speak response
  const speakResponse = useCallback(async (text: string) => {
    if (!audioUnlocked) {
      await unlockAudio()
    }

    try {
      const response = await fetch(`${API_BASE_URL}/voice/text-to-speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      })

      if (!response.ok) {
        throw new Error('Failed to generate speech')
      }

      const data = await response.json()

      if (!data.audio_base64) {
        throw new Error('No audio data received')
      }

      // Decode base64 audio
      const audioBytes = Uint8Array.from(atob(data.audio_base64), c => c.charCodeAt(0))
      const audioFormat = data.format || 'wav'
      const mimeType = audioFormat === 'mp3' ? 'audio/mpeg' : 'audio/wav'

      // Create audio element and play
      const audioBlob = new Blob([audioBytes], { type: mimeType })
      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)

      // Handle audio playback
      audio.onplay = () => {
        if (currentAudioRef.current === audio) {
          isSpeakingRef.current = true
          hasInterruptedRef.current = false
          setStatus('speaking')

          // Start recognition with delay for interrupt detection only
          setTimeout(() => {
            if (isSpeakingRef.current && shouldListenRef.current && !isRecognitionActiveRef.current && recognitionRef.current) {
              recognitionRef.current.start()
            }
          }, 300)
        }
      }

      audio.onended = () => {
        if (currentAudioRef.current === audio) {
          isSpeakingRef.current = false
          hasInterruptedRef.current = false
          currentAudioRef.current = null
          setLiveAssistantUtterance('')
          URL.revokeObjectURL(audioUrl)

          if (shouldListenRef.current) {
            if (!isRecognitionActiveRef.current && recognitionRef.current) {
              setTimeout(() => {
                if (shouldListenRef.current && !isRecognitionActiveRef.current && !isSpeakingRef.current && recognitionRef.current) {
                  recognitionRef.current.start()
                }
              }, 50)
            }
            setStatus('listening')
          } else {
            setStatus('idle')
          }
        }
      }

      audio.onerror = (e) => {
        console.error('Audio playback error:', e)
        setError('Failed to play audio')
        setStatus('listening')
      }

      currentAudioRef.current = audio
      await audio.play()
    } catch (err: any) {
      setError(err.message || 'Failed to speak response')
      setStatus('listening')
    }
  }, [audioUnlocked, unlockAudio])

  // Stop audio
  const stopAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current.currentTime = 0
      currentAudioRef.current = null
    }
    isSpeakingRef.current = false
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldListenRef.current = false
      clearPendingTimer()
      stopAudio()
      if (recognitionRef.current && isRecognitionActiveRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [clearPendingTimer, stopAudio])

  // Status indicator component
  const StatusIndicator = ({ status }: { status: Status }) => {
    const getStatusColor = () => {
      switch (status) {
        case 'idle': return 'bg-slate-500'
        case 'listening': return 'bg-blue-500'
        case 'processing': return 'bg-yellow-500'
        case 'speaking': return 'bg-green-500'
      }
    }

    const isPulsing = status !== 'idle'

    return (
      <div className="flex items-center gap-3">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()} ${isPulsing ? 'animate-pulse' : ''}`} />
        <span className="text-sm font-medium text-slate-300 capitalize">{status}</span>
      </div>
    )
  }

  return (
    <div className="p-8 min-h-screen bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-slate-800/70 backdrop-blur rounded-3xl border border-slate-700 shadow-2xl p-8 mb-6">
          <header className="mb-6">
            <h1 className="text-4xl font-bold leading-tight mb-2">🎤 Voice Agent Chat</h1>
            <p className="text-slate-300">
              Real-time speech-to-speech conversation with AI
            </p>
          </header>

          {/* Status */}
          <div className="mb-6">
            <StatusIndicator status={status} />
          </div>

          {/* Error Display */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-3"
              >
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-red-300">{error}</p>
                  <button
                    onClick={() => setError(null)}
                    className="text-xs text-red-400 hover:text-red-300 mt-1"
                  >
                    Dismiss
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Browser Support Warning */}
          {!browserSupported && (
            <div className="mb-4 p-4 bg-yellow-500/20 border border-yellow-500/50 rounded-lg">
              <p className="text-sm text-yellow-300">
                Your browser does not support speech recognition. Please use Chrome or Edge.
              </p>
            </div>
          )}

          {/* Controls */}
          <div className="flex gap-3 mb-6">
            {status === 'idle' ? (
              <button
                onClick={startConversation}
                disabled={!browserSupported}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Mic className="h-5 w-5" />
                Start Conversation
              </button>
            ) : (
              <button
                onClick={stopConversation}
                className="flex items-center gap-2 px-6 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 rounded-lg font-medium transition-all"
              >
                <Square className="h-5 w-5" />
                Stop Conversation
              </button>
            )}
          </div>

          {/* Custom Prompt */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Custom Prompt (Optional)
            </label>
            <textarea
              value={selectedPrompt}
              onChange={(e) => setSelectedPrompt(e.target.value)}
              placeholder={DEFAULT_PROMPT}
              className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={4}
              disabled={status !== 'idle'}
            />
            <p className="text-xs text-slate-500 mt-2">
              Customize the AI's behavior and personality. Leave empty to use default.
            </p>
          </div>
        </div>

        {/* Live Transcription */}
        {(liveUserTranscript || liveAssistantUtterance) && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-slate-800/70 backdrop-blur rounded-2xl border border-slate-700 p-6 mb-6"
          >
            <h3 className="text-sm font-medium text-slate-400 mb-3">Live Transcription</h3>
            {liveUserTranscript && (
              <div className="mb-3">
                <p className="text-xs text-slate-500 mb-1">You (speaking...)</p>
                <p className="text-slate-200 italic">{liveUserTranscript}</p>
              </div>
            )}
            {liveAssistantUtterance && (
              <div>
                <p className="text-xs text-slate-500 mb-1">AI (speaking...)</p>
                <p className="text-slate-200 italic">{liveAssistantUtterance}</p>
              </div>
            )}
          </motion.div>
        )}

        {/* Conversation History */}
        {transcripts.length > 0 && (
          <div className="bg-slate-800/70 backdrop-blur rounded-2xl border border-slate-700 shadow-2xl p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Volume2 className="h-5 w-5" />
              Conversation History
            </h3>
            <div className="max-h-96 overflow-y-auto">
              <Conversation messages={transcripts} />
            </div>
          </div>
        )}

        {/* Empty State */}
        {transcripts.length === 0 && status === 'idle' && (
          <div className="text-center py-12 text-slate-500">
            <Mic className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium mb-2">Ready to start</p>
            <p className="text-sm">Click "Start Conversation" to begin talking with the AI</p>
          </div>
        )}
      </div>
    </div>
  )
}
