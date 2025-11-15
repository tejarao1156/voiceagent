'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Sidebar } from './Sidebar'
import { TopNav } from './TopNav'
import { AgentTable, type Agent } from './AgentTable'
import { RegisteredPhonesTable } from './RegisteredPhonesTable'
import { OutgoingAgent } from './OutgoingAgent'
import { CreateAgentModal } from './CreateAgentModal'
import { RegisterPhoneModal } from './RegisterPhoneModal'
import { AnalyticsDashboard } from './dashboard-statistics'
import { CallsSection } from './CallsSection'
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
  const [agentFilter, setAgentFilter] = useState<'all' | 'active' | 'inactive' | 'phones'>('all')

  // Initialize from URL hash and sync with hash changes (client-side only)
  useEffect(() => {
    setMounted(true)
    
    // Set initial section from hash
    const hash = window.location.hash.replace('#', '')
    if (hash && ['dashboard', 'incoming-agent', 'outgoing-agent', 'calls', 'voice-customization', 'endpoints', 'activity-logs', 'settings'].includes(hash)) {
      setActiveSection(hash)
    } else if (hash === 'ai-agents') {
      // Legacy support: if hash is 'ai-agents', default to 'incoming-agent'
      setActiveSection('incoming-agent')
    }
    
    // Listen for hash changes
    const handleHashChange = () => {
      const newHash = window.location.hash.replace('#', '')
      if (newHash && ['dashboard', 'incoming-agent', 'outgoing-agent', 'calls', 'voice-customization', 'endpoints', 'activity-logs', 'settings'].includes(newHash)) {
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
    direction: 'incoming'
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
      if (editAgent) {
        // Update existing agent - exclude name and phoneNumber
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
      alert(`Failed to ${editAgent ? 'update' : 'create'} agent. Please try again.`)
    }
  }

  const loadAgents = async () => {
    try {
      setLoadingAgents(true)
      console.log('🔍 Loading agents from MongoDB (including deleted to ensure we get all data)...')
      // Fetch all agents from MongoDB including deleted ones, then filter in UI
      const response = await fetch('/agents?include_deleted=true')
      
      if (!response.ok) {
        console.error('❌ Failed to load agents:', response.status, response.statusText)
        setAgents([]) // Clear any existing data - only show MongoDB data
        setLoadingAgents(false)
        return
      }
      
      const result = await response.json()
      console.log('📥 Agents API response:', result)
      
      // Check MongoDB availability from response
      if (result.mongodb_available === false) {
        console.warn('⚠️ MongoDB is not available - showing empty state')
        setAgents([]) // Clear - MongoDB not connected
        setLoadingAgents(false)
        return
      }
      
      // Only use data if MongoDB is available and response is valid
      if (result.success && Array.isArray(result.agents)) {
        // Transform MongoDB agents to UI format
        // Format dates client-side only to avoid hydration mismatch
        const transformedAgents: Agent[] = result.agents
          .map((agent: any) => {
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
          
          // Filter out deleted agents in UI (but we fetched them to ensure we have all data)
          if (agent.isDeleted === true) {
            // Skip deleted agents in UI display
            return null
          }
          
          return {
            id: agent.id,
            name: agent.name,
            direction: (agent.direction === 'inbound' ? 'incoming' : agent.direction) || 'incoming',
            phoneNumber: agent.phoneNumber,
            lastUpdated,
            status: (agent.active === true || agent.active === undefined) ? 'active' : 'idle',
            active: agent.active !== false, // Default to true if undefined/null
            phoneIsDeleted: agent.phoneIsDeleted || false, // Include phone deletion status
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
          .filter((agent: Agent | null) => agent !== null) as Agent[] // Filter out null (deleted) agents
        console.log(`✅ Loaded ${transformedAgents.length} agent(s) from MongoDB`)
        if (transformedAgents.length > 0) {
          console.log('📋 Agent names:', transformedAgents.map(a => a.name))
        }
        setAgents(transformedAgents) // Only set agents from MongoDB
      } else {
        console.warn('⚠️ No agents found in MongoDB response:', result)
        setAgents([]) // Clear - no data in MongoDB
      }
    } catch (error) {
      console.error('❌ Error loading agents from MongoDB:', error)
      setAgents([]) // Clear on error - only show MongoDB data
    } finally {
      setLoadingAgents(false)
    }
  }

  // Filter agents based on active/inactive filter (only incoming agents)
  const filteredAgents = agents.filter(agent => {
    // Only show incoming agents
    if (agent.direction !== 'incoming' && agent.direction !== 'inbound') {
      return false
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
        // Load registered phones for outgoing agent section
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
      const response = await fetch(`/agents/${agent.id}`, {
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
        throw new Error('Failed to update agent')
      }
    } catch (error) {
      console.error('Error toggling agent active status:', error)
      alert('Failed to update agent status. Please try again.')
    }
  }

  const handleDelete = async (agent: Agent) => {
    if (confirm(`Are you sure you want to delete ${agent.name}?`)) {
      try {
        const response = await fetch(`/agents/${agent.id}`, {
          method: 'DELETE',
        })
        
        if (response.ok) {
          // Reload agents from MongoDB after deletion
          await loadAgents()
          alert('Agent deleted successfully!')
        } else {
          throw new Error('Failed to delete agent')
        }
      } catch (error) {
        console.error('Error deleting agent:', error)
        alert('Failed to delete agent. Please try again.')
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
                  Make outbound calls using your registered phone numbers.
                </p>
              </div>

              {/* Outgoing Agent Component */}
              <OutgoingAgent registeredPhones={registeredPhones} />
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

          {mounted && activeSection === 'voice-customization' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <VoiceCustomization />
            </motion.div>
          )}

          {activeSection !== 'incoming-agent' && activeSection !== 'outgoing-agent' && activeSection !== 'dashboard' && activeSection !== 'calls' && activeSection !== 'voice-customization' && (
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
          activeSection={activeSection}
        />

      <RegisterPhoneModal
        open={registerPhoneModalOpen}
        onOpenChange={setRegisterPhoneModalOpen}
        onSuccess={() => {
          // Reload agents and registered phones if in incoming-agent section (to refresh phone dropdown)
          if (activeSection === 'incoming-agent') {
            loadAgents()
            loadRegisteredPhones()
          }
        }}
      />
    </div>
  )
}

