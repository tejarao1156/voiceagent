'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { MessageSquare, Clock, Search } from 'lucide-react'
import { CallList } from '@/components/CallList'
import { Message } from '@/lib/api'
import { fetchMessages } from '@/lib/api'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export function MessagesSection() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  // Helper function to compare messages and detect changes
  const messagesHaveChanged = (oldMessages: Message[], newMessages: Message[]): boolean => {
    if (oldMessages.length !== newMessages.length) return true
    
    // Create maps for quick lookup
    const oldMap = new Map(oldMessages.map(msg => [msg.id, msg]))
    const newMap = new Map(newMessages.map(msg => [msg.id, msg]))
    
    // Check for new or removed messages
    for (const newMsg of newMessages) {
      const oldMsg = oldMap.get(newMsg.id)
      if (!oldMsg) return true // New message added
      
      // Check if conversation length changed (new messages)
      const oldConvLength = oldMsg.conversation?.length || 0
      const newConvLength = newMsg.conversation?.length || 0
      if (oldConvLength !== newConvLength) return true
    }
    
    // Check for removed messages
    for (const oldMsg of oldMessages) {
      if (!newMap.has(oldMsg.id)) return true // Message removed
    }
    
    return false
  }

  // Load messages from API (background update)
  const loadMessages = async (isInitial: boolean = false) => {
    try {
      // Only show loading on initial load
      if (isInitial) {
        setLoading(true)
      }
      
      const fetchedMessages = await fetchMessages(selectedAgent || undefined)
      
      // Transform API response to match Message interface (already in correct format)
      const transformedMessages: Message[] = fetchedMessages.map((msg: any) => ({
        id: msg.id || msg.conversation_id,
        phoneNumberId: msg.phoneNumberId || msg.agent_id,
        callerNumber: msg.callerNumber || msg.from_number,
        status: 'active' as const, // Messages are always active (ongoing conversations)
        timestamp: msg.timestamp || msg.latest_timestamp,
        conversation: msg.conversation || [],
        conversation_id: msg.conversation_id || msg.id,
        agentNumber: msg.agentNumber || msg.to_number,
        latest_message: msg.latest_message,
        message_count: msg.message_count
      }))
      
      // Only update state if data has actually changed
      setMessages(prevMessages => {
        if (isInitial || messagesHaveChanged(prevMessages, transformedMessages)) {
          return transformedMessages
        }
        return prevMessages // No changes, keep existing state
      })
    } catch (error) {
      console.error('Error fetching messages:', error)
      // Only clear messages on initial load error
      if (isInitial) {
        setMessages([])
      }
    } finally {
      if (isInitial) {
        setLoading(false)
      }
    }
  }

  // Load messages on mount and poll for updates in background
  useEffect(() => {
    // Initial load
    loadMessages(true)
    
    // Poll for updates every 3 seconds (background, no loading state)
    const interval = setInterval(() => {
      loadMessages(false)
    }, 3000)
    
    return () => clearInterval(interval)
  }, [selectedAgent])

  // Filter messages based on search query
  const filteredMessages = useMemo(() => {
    let filtered = messages

    // Filter by search query (search in caller number, latest message, or conversation)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(msg => {
        const callerMatch = msg.callerNumber?.toLowerCase().includes(query)
        const latestMsgMatch = msg.latest_message?.toLowerCase().includes(query)
        const conversationMatch = msg.conversation?.some(conv => 
          conv.text?.toLowerCase().includes(query)
        )
        return callerMatch || latestMsgMatch || conversationMatch
      })
    }

    // Sort by timestamp (most recent first)
    return filtered.sort((a, b) => {
      const timeA = new Date(a.timestamp || 0).getTime()
      const timeB = new Date(b.timestamp || 0).getTime()
      return timeB - timeA
    })
  }, [messages, searchQuery])

  // Get unique agents for filter dropdown
  const uniqueAgents = useMemo(() => {
    const agents = new Set<string>()
    messages.forEach(msg => {
      if (msg.phoneNumberId) {
        agents.add(msg.phoneNumberId)
      }
    })
    return Array.from(agents).sort()
  }, [messages])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800 mb-2">
            Messages
          </h1>
          <p className="text-slate-600">
            View and manage SMS conversations
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search by phone number or message content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white border-slate-300 text-slate-900"
            />
          </div>

          {/* Agent Filter */}
          {uniqueAgents.length > 0 && (
            <div className="sm:w-64">
              <select
                value={selectedAgent || ''}
                onChange={(e) => setSelectedAgent(e.target.value || null)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900 text-sm"
              >
                <option value="">All Agents</option>
                {uniqueAgents.map(agent => (
                  <option key={agent} value={agent}>
                    {agent}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </Card>

      {/* Messages List */}
      {loading ? (
        <Card className="p-8 text-center">
          <div className="flex flex-col items-center gap-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p className="text-slate-600">Loading messages...</p>
          </div>
        </Card>
      ) : filteredMessages.length === 0 ? (
        <Card className="p-8 text-center">
          <MessageSquare className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <p className="text-slate-600">
            {searchQuery || selectedAgent
              ? 'No messages found matching your filters'
              : 'No messages yet. Messages will appear here when users text your registered numbers.'}
          </p>
        </Card>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
            <CallList
              calls={filteredMessages.map(msg => ({
                id: msg.id,
                phoneNumberId: msg.phoneNumberId,
                callerNumber: msg.callerNumber,
                status: 'ongoing' as const, // Messages are always ongoing (active conversations)
                timestamp: msg.timestamp,
                conversation: msg.conversation || []
              }))}
          />
        </motion.div>
      )}

      {/* Stats */}
      {!loading && filteredMessages.length > 0 && (
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            <span>{filteredMessages.length} conversation{filteredMessages.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
      )}
    </div>
  )
}

