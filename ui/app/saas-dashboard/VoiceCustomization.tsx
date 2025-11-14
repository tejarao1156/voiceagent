'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Volume2, Play, Pause, Loader2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Voice {
  name: string
  used: boolean
}

export function VoiceCustomization() {
  const [voices, setVoices] = useState<Voice[]>([])
  const [loading, setLoading] = useState(true)
  const [playingVoice, setPlayingVoice] = useState<string | null>(null)
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null)

  // Load voices from API
  const loadVoices = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/voices')
      if (response.ok) {
        const data = await response.json()
        setVoices(data.voices || [])
      } else {
        console.error('Failed to fetch voices')
        // Fallback to default voices
        setVoices([
          { name: 'alloy', used: false },
          { name: 'echo', used: false },
          { name: 'fable', used: false },
          { name: 'onyx', used: false },
          { name: 'nova', used: false },
          { name: 'shimmer', used: false },
        ])
      }
    } catch (error) {
      console.error('Error fetching voices:', error)
      // Fallback to default voices
      setVoices([
        { name: 'alloy', used: false },
        { name: 'echo', used: false },
        { name: 'fable', used: false },
        { name: 'onyx', used: false },
        { name: 'nova', used: false },
        { name: 'shimmer', used: false },
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadVoices()
  }, [])

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioElement) {
        audioElement.pause()
        audioElement.src = ''
      }
    }
  }, [audioElement])

  // Play voice demo
  const playDemo = async (voiceName: string) => {
    try {
      // Stop current audio if playing
      if (audioElement) {
        audioElement.pause()
        audioElement.src = ''
      }

      setPlayingVoice(voiceName)

      // Generate demo text
      const demoText = `Hello! This is a demonstration of the ${voiceName} voice. How does it sound to you?`

      // Call TTS API
      const response = await fetch('/voice/text-to-speech', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: demoText,
          voice: voiceName,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to generate voice demo')
      }

      const data = await response.json()

      if (data.success && data.audio_base64) {
        // Create audio element and play
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`)
        setAudioElement(audio)

        audio.onended = () => {
          setPlayingVoice(null)
          setAudioElement(null)
        }

        audio.onerror = () => {
          console.error('Error playing audio')
          setPlayingVoice(null)
          setAudioElement(null)
        }

        await audio.play()
      } else {
        throw new Error(data.error || 'Failed to generate audio')
      }
    } catch (error) {
      console.error('Error playing voice demo:', error)
      setPlayingVoice(null)
      alert('Failed to play voice demo. Please try again.')
    }
  }

  // Stop current audio
  const stopDemo = () => {
    if (audioElement) {
      audioElement.pause()
      audioElement.src = ''
      setAudioElement(null)
    }
    setPlayingVoice(null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">
          Voice Customization
        </h1>
        <p className="text-slate-600">
          Preview and test all available TTS voices used in your agents.
        </p>
      </div>

      {/* Info Card */}
      <Card className="p-4 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <Volume2 className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900 mb-1">
              Automated Voice Listing
            </p>
            <p className="text-sm text-blue-700">
              Voices are automatically fetched from your agents in the database. 
              Click the play button to hear a demo of each voice.
            </p>
          </div>
        </div>
      </Card>

      {/* Voices Grid */}
      {loading ? (
        <Card className="p-12">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-600 mx-auto mb-4" />
            <p className="text-slate-600">Loading voices...</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {voices.map((voice) => (
            <Card
              key={voice.name}
              className={cn(
                "p-6 transition-all hover:shadow-lg",
                playingVoice === voice.name && "ring-2 ring-indigo-500 bg-indigo-50"
              )}
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 capitalize">
                    {voice.name}
                  </h3>
                  {voice.used && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 mt-1">
                      Used in agents
                    </span>
                  )}
                </div>
                <Volume2 className="h-6 w-6 text-slate-400" />
              </div>

              <Button
                onClick={() => {
                  if (playingVoice === voice.name) {
                    stopDemo()
                  } else {
                    playDemo(voice.name)
                  }
                }}
                disabled={playingVoice !== null && playingVoice !== voice.name}
                className={cn(
                  "w-full",
                  playingVoice === voice.name
                    ? "bg-indigo-600 hover:bg-indigo-700"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-900"
                )}
              >
                {playingVoice === voice.name ? (
                  <>
                    <Pause className="h-4 w-4 mr-2" />
                    Playing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Play Demo
                  </>
                )}
              </Button>
            </Card>
          ))}
        </div>
      )}

      {voices.length === 0 && !loading && (
        <Card className="p-12">
          <div className="text-center text-slate-500">
            <Volume2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No voices found. Create an agent to see available voices.</p>
          </div>
        </Card>
      )}
    </div>
  )
}

