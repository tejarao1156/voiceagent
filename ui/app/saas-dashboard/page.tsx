'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Sidebar } from './Sidebar'
import { TopNav } from './TopNav'
import { AgentTable, type Agent } from './AgentTable'
import { RegisteredPhonesTable } from './RegisteredPhonesTable'
import { OutgoingAgent } from './OutgoingAgent'
import { MakeCallForm } from './MakeCallForm'
import { CreateAgentModal } from './CreateAgentModal'
import { RegisterPhoneModal } from './RegisterPhoneModal'
import { AnalyticsDashboard } from './dashboard-statistics'
import { CallsSection } from './CallsSection'
import { MessagesSection } from './MessagesSection'
import { VoiceCustomization } from './VoiceCustomization'
import { Button } from '@/components/ui/button'
import { fetchRegisteredPhones } from '@/lib/api'

export default function SaaSDashboard() {
  // Check URL hash or default to dashboard - use client-side only to avoid hydration mismatch
  const [activeSection, setActiveSection] = useState('dashboard')
  const [mounted, setMounted] = useState(false)
  const [registeredPhones, setRegisteredPhones] = useState<any[]>([])
  const [loadingPhones, setLoadingPhones] = useState(false)
  const [agents, setAgents] = useState<Agent[]>([]) // Start with empty array - load from MongoDB
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [registerPhoneModalOpen, setRegisterPhoneModalOpen] = useState(false)
  const [editAgent, setEditAgent] = useState<Agent | null>(null)
  const [loadingAgents, setLoadingAgents] = useState(false)
  const [agentFilter, setAgentFilter] = useState<'all' | 'active' | 'inactive' | 'phones' | 'make-call'>('all')
  const [outgoingAgentFilter, setOutgoingAgentFilter] = useState<'make-call'>('make-call')

  // Initialize from URL hash and sync with hash changes (client-side only)
  useEffect(() => {
    setMounted(true)
    
    // Set initial section from hash
    const hash = window.location.hash.replace('#', '')
    if (hash && ['dashboard', 'incoming-agent', 'outgoing-agent', 'messaging-agent', 'calls', 'messages', 'voice-customization', 'endpoints', 'activity-logs', 'settings'].includes(hash)) {
      setActiveSection(hash)
    } else if (hash === 'ai-agents') {
      // Legacy support: if hash is 'ai-agents', default to 'incoming-agent'
      setActiveSection('incoming-agent')
    }
    
    // Listen for hash changes
    const handleHashChange = () => {
      const newHash = window.location.hash.replace('#', '')
      if (newHash && ['dashboard', 'incoming-agent', 'outgoing-agent', 'messaging-agent', 'calls', 'messages', 'voice-customization', 'endpoints', 'activity-logs', 'settings'].includes(newHash)) {
        setActiveSection(newHash)
      } else if (newHash === 'ai-agents') {
        // Legacy support: if hash is 'ai-agents', default to 'incoming-agent'
        setActiveSection('incoming-agent')
      }
    }

    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const handleCreateAgent = async (data: {
    name: string
    direction: 'incoming' | 'outgoing' | 'messaging'
    phoneNumber: string
    sttModel: string
    inferenceModel: string
    ttsModel: string
    ttsVoice: string
    systemPrompt: string
    greeting: string
    temperature: number
    maxTokens: number
    active: boolean
    twilioAccountSid?: string
    twilioAuthToken?: string
  }) => {
    try {
      // Check if this is a messaging agent - use message_agent API
      const isMessagingAgent = data.direction === 'messaging'
      
      if (editAgent) {
        // Update existing agent
        if (isMessagingAgent) {
          // Update message agent
          const updateData = {
            systemPrompt: data.systemPrompt,
            greeting: data.greeting,
            inferenceModel: data.inferenceModel,
            temperature: data.temperature,
            maxTokens: data.maxTokens,
            active: data.active,
          }

          const response = await fetch(`/api/message-agents/${editAgent.id}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData),
          })

          if (!response.ok) {
            throw new Error('Failed to update message agent')
          }
        } else {
          // Update regular agent - exclude name and phoneNumber
          const updateData = {
            direction: data.direction,
            sttModel: data.sttModel,
            inferenceModel: data.inferenceModel,
            ttsModel: data.ttsModel,
            ttsVoice: data.ttsVoice,
            systemPrompt: data.systemPrompt,
            greeting: data.greeting,
            temperature: data.temperature,
            maxTokens: data.maxTokens,
            active: data.active,
            twilioAccountSid: data.twilioAccountSid,
            twilioAuthToken: data.twilioAuthToken,
          }

          const response = await fetch(`/agents/${editAgent.id}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData),
          })

          if (!response.ok) {
            throw new Error('Failed to update agent')
          }
        }

        // Close modal and reset edit state
        setCreateModalOpen(false)
        setEditAgent(null)
        
        // Reload agents from MongoDB after a short delay to ensure DB write is complete
        setTimeout(async () => {
          await loadAgents()
        }, 500)
        
        alert('Agent updated successfully!')
      } else {
        // Create new agent
        if (isMessagingAgent) {
          // Create message agent using message_agent API
          const messageAgentData = {
            name: data.name,
            phoneNumber: data.phoneNumber,
            systemPrompt: data.systemPrompt,
            greeting: data.greeting,
            inferenceModel: data.inferenceModel,
            temperature: data.temperature,
            maxTokens: data.maxTokens,
            active: data.active,
          }

          const response = await fetch('/api/message-agents', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(messageAgentData),
          })

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to create message agent' }))
            throw new Error(errorData.detail || 'Failed to create message agent')
          }

          const result = await response.json()
        } else {
          // Create regular agent
          const response = await fetch('/agents', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          })

          if (!response.ok) {
            throw new Error('Failed to create agent')
          }

          const result = await response.json()
        }
        
        // Close modal
        setCreateModalOpen(false)
        
        // Reload agents from MongoDB after a short delay to ensure DB write is complete
        setTimeout(async () => {
          await loadAgents()
        }, 500)
        
        alert('Agent created successfully!')
      }
    } catch (error) {
      console.error(`Error ${editAgent ? 'updating' : 'creating'} agent:`, error)
      const errorMessage = error instanceof Error ? error.message : `Failed to ${editAgent ? 'update' : 'create'} agent. Please try again.`
      alert(errorMessage)
    }
  }

  const loadAgents = async () => {
    try {
      setLoadingAgents(true)
      console.log('🔍 Loading agents from MongoDB (including deleted to ensure we get all data)...')
      
      // Fetch regular agents and message agents in parallel
      const [regularAgentsResponse, messageAgentsResponse] = await Promise.all([
        fetch('/agents?include_deleted=true').catch((err) => {
          console.error('❌ Error fetching regular agents:', err)
          return { ok: false, json: async () => ({ success: true, agents: [], mongodb_available: false, error: err.message }) }
        }),
        fetch('/api/message-agents?include_deleted=true').catch((err) => {
          console.error('❌ Error fetching message agents:', err)
          return { ok: false, json: async () => ({ success: true, agents: [], mongodb_available: false, error: err.message }) }
        })
      ])
      
      const allAgents: Agent[] = []
      
      // Process regular agents
      if (regularAgentsResponse.ok) {
        try {
          const result = await regularAgentsResponse.json()
          console.log('📥 Regular Agents API response:', result)
          
          if (result.mongodb_available !== false && result.success && Array.isArray(result.agents)) {
          const transformedAgents: Agent[] = result.agents
            .map((agent: any) => {
              // Filter out deleted agents and messaging agents (messaging agents come from message_agent collection)
              if (agent.isDeleted === true || agent.direction === 'messaging') {
                return null
              }
              
              let lastUpdated = 'Unknown'
              if (agent.updated_at && typeof window !== 'undefined') {
                try {
                  const date = new Date(agent.updated_at)
                  lastUpdated = date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  }) + ' ' + date.toLocaleTimeString('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true,
                  })
                } catch (e) {
                  lastUpdated = agent.updated_at
                }
              }
              
              // Normalize direction (handle legacy 'inbound' value)
              let normalizedDirection: 'incoming' | 'outgoing' | 'messaging' = 'incoming'
              if (agent.direction === 'inbound' || agent.direction === 'incoming') {
                normalizedDirection = 'incoming'
              } else if (agent.direction === 'outgoing') {
                normalizedDirection = 'outgoing'
              }
              
              return {
                id: agent.id,
                name: agent.name,
                direction: normalizedDirection,
                phoneNumber: agent.phoneNumber,
                lastUpdated,
                status: (agent.active === true || agent.active === undefined) ? 'active' : 'idle',
                active: agent.active !== false,
                phoneIsDeleted: agent.phoneIsDeleted || false,
                sttModel: agent.sttModel,
                inferenceModel: agent.inferenceModel,
                ttsModel: agent.ttsModel,
                ttsVoice: agent.ttsVoice,
                systemPrompt: agent.systemPrompt,
                greeting: agent.greeting,
                temperature: agent.temperature,
                maxTokens: agent.maxTokens,
                twilioAccountSid: agent.twilioAccountSid,
                twilioAuthToken: agent.twilioAuthToken,
              }
            })
            .filter((agent: Agent | null) => agent !== null) as Agent[]
          
          allAgents.push(...transformedAgents)
          }
        } catch (error) {
          console.error('❌ Error parsing regular agents response:', error)
        }
      } else {
        const status = 'status' in regularAgentsResponse ? regularAgentsResponse.status : 'unknown'
        console.warn('⚠️ Regular agents fetch failed or returned non-ok status:', status)
      }
      
      // Process message agents
      if (messageAgentsResponse.ok) {
        try {
          const result = await messageAgentsResponse.json()
          console.log('📥 Message Agents API response:', result)
          
          if (result.mongodb_available !== false && result.success && Array.isArray(result.agents)) {
          const transformedAgents: Agent[] = result.agents
            .map((agent: any) => {
              // Filter out deleted message agents
              if (agent.isDeleted === true) {
                return null
              }
              
              let lastUpdated = 'Unknown'
              if (agent.updated_at && typeof window !== 'undefined') {
                try {
                  const date = new Date(agent.updated_at)
                  lastUpdated = date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  }) + ' ' + date.toLocaleTimeString('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true,
                  })
                } catch (e) {
                  lastUpdated = agent.updated_at
                }
              }
              
              return {
                id: agent.id,
                name: agent.name,
                direction: 'messaging' as const,
                phoneNumber: agent.phoneNumber,
                lastUpdated,
                status: (agent.active === true || agent.active === undefined) ? 'active' : 'idle',
                active: agent.active !== false,
                phoneIsDeleted: false, // Message agents always have registered phones
                sttModel: undefined, // Not used for messaging
                inferenceModel: agent.inferenceModel,
                ttsModel: undefined, // Not used for messaging
                ttsVoice: undefined, // Not used for messaging
                systemPrompt: agent.systemPrompt,
                greeting: agent.greeting,
                temperature: agent.temperature,
                maxTokens: agent.maxTokens,
                twilioAccountSid: undefined,
                twilioAuthToken: undefined,
              }
            })
            .filter((agent: Agent | null) => agent !== null) as Agent[]
          
          allAgents.push(...transformedAgents)
          }
        } catch (error) {
          console.error('❌ Error parsing message agents response:', error)
        }
      } else {
        const status = 'status' in messageAgentsResponse ? messageAgentsResponse.status : 'unknown'
        console.warn('⚠️ Message agents fetch failed or returned non-ok status:', status)
      }
      
      console.log(`✅ Loaded ${allAgents.length} agent(s) from MongoDB (regular + message agents)`)
      if (allAgents.length > 0) {
        console.log('📋 Agent names:', allAgents.map(a => `${a.name} (${a.direction})`))
      }
      setAgents(allAgents)
    } catch (error) {
      console.error('❌ Error loading agents from MongoDB:', error)
      setAgents([]) // Clear on error - only show MongoDB data
    } finally {
      setLoadingAgents(false)
    }
  }

  // Filter agents based on active/inactive filter and direction
  const filteredAgents = agents.filter(agent => {
    // Filter by direction based on active section
    if (activeSection === 'incoming-agent') {
      // Only show incoming agents (handle both 'incoming' and legacy 'inbound')
      // Type assertion needed because 'inbound' might come from MongoDB but isn't in TypeScript type
      const direction = agent.direction as string
      const isIncoming = direction === 'incoming' || direction === 'inbound'
      if (!isIncoming) {
        return false
      }
    } else if (activeSection === 'outgoing-agent') {
      // Only show outgoing agents
      if (agent.direction !== 'outgoing') {
        return false
      }
    } else if (activeSection === 'messaging-agent') {
      // Only show messaging agents
      if (agent.direction !== 'messaging') {
        return false
      }
    }
    
    // Filter by active/inactive status
    const isActive = agent.active !== false
    if (agentFilter === 'active') return isActive === true
    if (agentFilter === 'inactive') return isActive === false
    return true // 'all' shows everything (after direction filter)
  })

  // Load registered phones (fetch ALL phones, not just active)
  const loadRegisteredPhones = async () => {
    try {
      setLoadingPhones(true)
      console.log('🔍 Fetching registered phones from MongoDB...')
      // Fetch all phones regardless of active status
      const phones = await fetchRegisteredPhones(false)
      console.log(`✅ Loaded ${phones.length} registered phone(s) from MongoDB:`, phones)
      setRegisteredPhones(phones)
      if (phones.length === 0) {
        console.warn('⚠️ No phones found in MongoDB. Make sure you have registered at least one phone number.')
      }
    } catch (error) {
      console.error('❌ Error loading registered phones:', error)
      setRegisteredPhones([])
      // Show user-friendly error
      alert(`Failed to load registered phones: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoadingPhones(false)
    }
  }

  // Load agents on mount and when section changes (client-side only to avoid hydration issues)
  useEffect(() => {
    if (mounted) {
      if (activeSection === 'incoming-agent') {
        // Always clear agents first to ensure we only show MongoDB data
        setAgents([])
        loadAgents()
        // Always load registered phones (for dropdown in CreateAgentModal and phones tab)
        loadRegisteredPhones()
      } else if (activeSection === 'outgoing-agent') {
        // Always clear agents first to ensure we only show MongoDB data
        setAgents([])
        loadAgents()
        // Load registered phones for outgoing agent section
        loadRegisteredPhones()
      } else if (activeSection === 'messaging-agent') {
        // Always clear agents first to ensure we only show MongoDB data
        setAgents([])
        loadAgents()
        // Load registered phones for messaging agent section
        loadRegisteredPhones()
      } else {
        // Clear agents when leaving agent sections - only show data when in those sections
        setAgents([])
      }
    }
  }, [mounted, activeSection])
  
  // Reload phones when phones tab is selected
  useEffect(() => {
    if (mounted && activeSection === 'incoming-agent' && agentFilter === 'phones') {
      console.log('📞 Phones tab selected, loading registered phones...')
      loadRegisteredPhones()
    }
  }, [mounted, activeSection, agentFilter])

  const handleEdit = (agent: Agent) => {
    setEditAgent(agent)
    setCreateModalOpen(true)
  }

  const handleToggleActive = async (agent: Agent, active: boolean) => {
    // Prevent toggling if phone is deleted
    if (agent.phoneIsDeleted) {
      alert('Cannot toggle active status. The associated phone number has been deleted.')
      return
    }
    
    try {
      // Check if this is a messaging agent
      const isMessagingAgent = agent.direction === 'messaging'
      const endpoint = isMessagingAgent 
        ? `/api/message-agents/${agent.id}`
        : `/agents/${agent.id}`
      
      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active }),
      })

      if (response.ok) {
        // Reload agents from MongoDB
        await loadAgents()
        console.log(`Agent ${agent.name} ${active ? 'activated' : 'deactivated'}`)
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to update agent' }))
        throw new Error(errorData.detail || 'Failed to update agent')
      }
    } catch (error) {
      console.error('Error toggling agent active status:', error)
      const errorMessage = error instanceof Error ? error.message : 'Failed to update agent status. Please try again.'
      alert(errorMessage)
    }
  }

  const handleDelete = async (agent: Agent) => {
    if (confirm(`Are you sure you want to delete ${agent.name}?`)) {
      try {
        // Check if this is a messaging agent
        const isMessagingAgent = agent.direction === 'messaging'
        const endpoint = isMessagingAgent 
          ? `/api/message-agents/${agent.id}`
          : `/agents/${agent.id}`
        
        const response = await fetch(endpoint, {
          method: 'DELETE',
        })
        
        if (response.ok) {
          // Reload agents from MongoDB after deletion
          await loadAgents()
          alert('Agent deleted successfully!')
        } else {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to delete agent' }))
          throw new Error(errorData.detail || 'Failed to delete agent')
        }
      } catch (error) {
        console.error('Error deleting agent:', error)
        const errorMessage = error instanceof Error ? error.message : 'Failed to delete agent. Please try again.'
        alert(errorMessage)
      }
    }
  }

  const handleDeletePhone = async (phone: any) => {
    if (confirm(`Are you sure you want to delete phone number ${phone.phoneNumber}? This action cannot be undone.`)) {
      try {
        console.log(`🗑️ Deleting phone ${phone.id} (${phone.phoneNumber})`)
        const response = await fetch(`/api/phones/${phone.id}`, {
          method: 'DELETE',
        })
        
        if (response.ok) {
          const result = await response.json()
          console.log('✅ Phone deleted:', result)
          // Reload phones from MongoDB after deletion
          await loadRegisteredPhones()
          alert('Phone number deleted successfully!')
        } else {
          const errorData = await response.json().catch(() => ({ detail: response.statusText }))
          throw new Error(errorData.detail || 'Failed to delete phone')
        }
      } catch (error) {
        console.error('❌ Error deleting phone:', error)
        alert(`Failed to delete phone number. ${error instanceof Error ? error.message : 'Please try again.'}`)
      }
    }
  }


  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar activeSection={activeSection} onSectionChange={setActiveSection} />
      
      <div className="ml-60">
        <TopNav
          activeTab=""
          onTabChange={() => {}}
          onCreateAgent={() => setCreateModalOpen(true)}
          onRegisterPhone={() => setRegisterPhoneModalOpen(true)}
          activeSection={activeSection}
        />

        <main className="p-6">
          {mounted && activeSection === 'incoming-agent' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              {/* Header */}
              <div className="mb-6">
                <h1 className="text-2xl font-semibold text-slate-800 mb-2">
                  Incoming Agent
                </h1>
                <p className="text-slate-600">
                  Create and manage Voice Agents for your Business.
                </p>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 mb-6 border-b border-slate-200">
                <button
                  onClick={() => setAgentFilter('all')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    agentFilter === 'all'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  All Agents
                </button>
                <button
                  onClick={() => setAgentFilter('active')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    agentFilter === 'active'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  Active Agents
                </button>
                <button
                  onClick={() => setAgentFilter('inactive')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    agentFilter === 'inactive'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  Inactive Agents
                </button>
                <button
                  onClick={() => setAgentFilter('phones')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    agentFilter === 'phones'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  Registered Phone Numbers
                </button>
              </div>

              {/* Content based on selected tab */}
              {agentFilter === 'phones' ? (
                <RegisteredPhonesTable
                  phones={registeredPhones}
                  onCopy={(text, field) => {
                    console.log(`Copied ${field}:`, text)
                  }}
                  onDelete={handleDeletePhone}
                />
              ) : (
                <AgentTable
                  agents={filteredAgents}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onToggleActive={handleToggleActive}
                />
              )}
            </motion.div>
          )}

          {mounted && activeSection === 'messaging-agent' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              {/* Header */}
              <div className="mb-6">
                <h1 className="text-2xl font-semibold text-slate-800 mb-2">
                  Messaging Agent
                </h1>
                <p className="text-slate-600">
                  Create and manage Messaging Agents for SMS conversations.
                </p>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 mb-6 border-b border-slate-200">
                <button
                  onClick={() => setAgentFilter('all')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    agentFilter === 'all'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  All Agents
                </button>
                <button
                  onClick={() => setAgentFilter('active')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    agentFilter === 'active'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  Active Agents
                </button>
                <button
                  onClick={() => setAgentFilter('inactive')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    agentFilter === 'inactive'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  Inactive Agents
                </button>
              </div>

              {/* Content based on selected tab */}
              {agentFilter !== 'phones' && agentFilter !== 'make-call' && (
                <AgentTable
                  agents={filteredAgents}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onToggleActive={handleToggleActive}
                />
              )}
            </motion.div>
          )}

          {mounted && activeSection === 'outgoing-agent' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              {/* Header */}
              <div className="mb-6">
                <h1 className="text-2xl font-semibold text-slate-800 mb-2">
                  Outgoing Agent
                </h1>
                <p className="text-slate-600">
                  Create and manage Outgoing Agents for making outbound calls.
                </p>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 mb-6 border-b border-slate-200">
                <button
                  onClick={() => setOutgoingAgentFilter('make-call')}
                  className={cn(
                    "px-4 py-2 text-sm font-medium transition-colors",
                    outgoingAgentFilter === 'make-call'
                      ? "text-indigo-600 border-b-2 border-indigo-600"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  Make a Call
                </button>
              </div>

              {/* Content based on selected tab */}
              {outgoingAgentFilter === 'make-call' && (
                <MakeCallForm registeredPhones={registeredPhones} />
              )}
            </motion.div>
          )}

          {mounted && activeSection === 'dashboard' && (
            <div>
              <div className="mb-6">
                <h1 className="text-2xl font-semibold text-slate-800 mb-2">
                  Analytics Dashboard
                </h1>
                <p className="text-slate-600">
                  View call statistics, duration metrics, and performance analytics.
                </p>
              </div>
              <AnalyticsDashboard />
            </div>
          )}

          {mounted && activeSection === 'calls' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <CallsSection />
            </motion.div>
          )}

          {mounted && activeSection === 'messages' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <MessagesSection />
            </motion.div>
          )}

          {mounted && activeSection === 'voice-customization' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <VoiceCustomization />
            </motion.div>
          )}

          {activeSection !== 'incoming-agent' && activeSection !== 'outgoing-agent' && activeSection !== 'messaging-agent' && activeSection !== 'dashboard' && activeSection !== 'calls' && activeSection !== 'messages' && activeSection !== 'voice-customization' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <h1 className="text-2xl font-semibold text-slate-800 mb-2">
                {activeSection
                  .split('-')
                  .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ')}
              </h1>
              <p className="text-slate-600">This section is coming soon...</p>
            </motion.div>
          )}
        </main>
      </div>

      <CreateAgentModal
          open={createModalOpen}
          onOpenChange={(open) => {
            setCreateModalOpen(open)
            if (!open) {
              setEditAgent(null) // Reset edit agent when modal closes
            }
          }}
          onSubmit={handleCreateAgent}
          editAgent={editAgent}
          activeSection={activeSection as 'incoming-agent' | 'outgoing-agent' | 'messaging-agent'}
        />

      <RegisterPhoneModal
        open={registerPhoneModalOpen}
        onOpenChange={setRegisterPhoneModalOpen}
        activeSection={activeSection}
        onSuccess={() => {
          // Reload agents and registered phones if in incoming-agent section (to refresh phone dropdown)
          if (activeSection === 'incoming-agent' || activeSection === 'messaging-agent') {
            loadAgents()
            loadRegisteredPhones()
          }
        }}
      />
    </div>
  )
}

