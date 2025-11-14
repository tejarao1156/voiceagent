'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Phone, ChevronDown, ChevronUp, Clock } from 'lucide-react'
import { Call } from '@/lib/store'
import { Conversation } from './Conversation'
import { cn } from '@/lib/utils'

interface CallListProps {
  calls: Call[]
  onCallUpdate?: (callId: string, updates: Partial<Call>) => void
}

export function CallList({ calls, onCallUpdate }: CallListProps) {
  const [expandedCallId, setExpandedCallId] = useState<string | null>(null)
  const [liveTranscripts, setLiveTranscripts] = useState<Record<string, any[]>>({})

  const toggleCall = (callId: string) => {
    setExpandedCallId(expandedCallId === callId ? null : callId)
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Set up WebSocket connections for active calls
  useEffect(() => {
    const activeCalls = calls.filter(call => call.status === 'ongoing')
    const wsConnections: Record<string, WebSocket> = {}
    
    activeCalls.forEach(call => {
      // Use relative WebSocket URL for proxy support
      const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = typeof window !== 'undefined' ? window.location.host : 'localhost:4002'
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `${wsProtocol}//${wsHost}`
      const url = `${wsUrl}/ws/calls/${call.id}/transcript`
      
      // Skip if WebSocket already exists for this call
      if (wsConnections[call.id]) {
        return
      }
      
      const ws = new WebSocket(url)
      wsConnections[call.id] = ws
      
      ws.onopen = () => {
        console.log(`WebSocket connected for call ${call.id}`)
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'transcript_update') {
            setLiveTranscripts(prev => ({
              ...prev,
              [call.id]: [...(prev[call.id] || []), data.entry]
            }))
            // Update call in parent
            if (onCallUpdate) {
              onCallUpdate(call.id, {
                conversation: [...(call.conversation || []), data.entry]
              })
            }
          } else if (data.type === 'initial') {
            setLiveTranscripts(prev => ({
              ...prev,
              [call.id]: data.transcript || []
            }))
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e)
        }
      }
      
      ws.onerror = (error) => {
        console.error(`WebSocket error for call ${call.id}:`, error)
      }
      
      ws.onclose = () => {
        console.log(`WebSocket closed for call ${call.id}`)
      }
    })
    
    // Cleanup: close all WebSocket connections when component unmounts or calls change
    return () => {
      Object.values(wsConnections).forEach(ws => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close()
        }
      })
    }
  }, [calls, onCallUpdate])

  if (calls.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p className="text-sm">No calls yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {calls.map((call) => {
        const isExpanded = expandedCallId === call.id
        const isOngoing = call.status === 'ongoing'
        
        // Use live transcript if available, otherwise use stored conversation
        const displayConversation = isOngoing && liveTranscripts[call.id]
          ? liveTranscripts[call.id]
          : call.conversation || []

        return (
          <motion.div
            key={call.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "rounded-lg border transition-all overflow-hidden",
              isOngoing
                ? "border-green-500/50 bg-green-500/5 shadow-lg shadow-green-500/20"
                : "border-slate-700/50 bg-slate-800/30"
            )}
          >
            {/* Call Header */}
            <button
              onClick={() => toggleCall(call.id)}
              className="w-full p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
            >
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="flex-shrink-0">
                  {isOngoing ? (
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ repeat: Infinity, duration: 2 }}
                      className="h-3 w-3 rounded-full bg-green-400 shadow-lg shadow-green-400/50"
                    />
                  ) : (
                    <div className="h-3 w-3 rounded-full bg-slate-500" />
                  )}
                </div>
                
                <div className="flex-1 min-w-0 text-left">
                  <div className="flex items-center gap-2 mb-1">
                    <Phone className="h-4 w-4 text-slate-400" />
                    <span className="font-medium text-slate-200 truncate">
                      {call.callerNumber}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span>{new Date(call.timestamp as string | Date).toLocaleString()}</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDuration(call.duration)}
                    </span>
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded-full text-xs font-medium",
                        isOngoing
                          ? "bg-green-500/20 text-green-400"
                          : "bg-slate-700/50 text-slate-400"
                      )}
                    >
                      {isOngoing ? 'Ongoing' : 'Finished'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex-shrink-0 ml-4">
                {isExpanded ? (
                  <ChevronUp className="h-5 w-5 text-slate-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-slate-400" />
                )}
              </div>
            </button>

            {/* Expanded Conversation */}
            <AnimatePresence>
              {isExpanded && displayConversation.length > 0 && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="border-t border-slate-700/50 bg-slate-900/50"
                >
                  <div className="max-h-96 overflow-y-auto">
                    <Conversation messages={displayConversation} isLive={isOngoing} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )
      })}
    </div>
  )
}

