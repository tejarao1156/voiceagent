'use client'

import { useState, useEffect, useRef, KeyboardEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  Phone,
  MessageSquare,
  Users,
  Settings,
  Mic,
  BarChart3,
  Globe,
  Zap,
  Cpu,
  Radio,
  Command,
  Sun,
  Bell,
  Search,
  MoreHorizontal,
  PhoneIncoming,
  PhoneOutgoing,
  Clock,
  Calendar,
  Play,
  Pause,
  Send,
  User,
  Bot,
  History,
  Volume2,
  Link,
  FileText,
  Copy,
  Check,
  CheckCircle2,
  Filter,
  Edit,
  Trash2,
  Plus,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  DollarSign
} from 'lucide-react'

// --- Components ---

const LightGlassCard = ({ children, className = "", delay = 0 }: { children: React.ReactNode, className?: string, delay?: number }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5, delay }}
    className={`relative overflow-hidden rounded-2xl border border-white/60 bg-white/60 p-6 backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-shadow duration-300 ${className}`}
  >
    <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-blue-400/10 blur-3xl" />
    <div className="absolute -bottom-24 -left-24 h-48 w-48 rounded-full bg-purple-400/10 blur-3xl" />
    <div className="relative z-10">{children}</div>
  </motion.div>
)

const StatCard = ({ icon: Icon, label, value, trend, color, delay }: any) => (
  <LightGlassCard delay={delay} className="group hover:bg-white/80 transition-colors duration-300">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <h3 className="mt-2 text-3xl font-bold text-slate-800 tracking-tight">{value}</h3>
      </div>
      <div className={`rounded-xl p-3 bg-gradient-to-br ${color} text-white shadow-lg shadow-blue-500/10 group-hover:scale-110 transition-transform duration-300`}>
        <Icon className="h-6 w-6" />
      </div>
    </div>
    <div className="mt-4 flex items-center text-sm">
      <span className="text-emerald-600 font-semibold flex items-center bg-emerald-50 px-2 py-0.5 rounded-full">
        <Activity className="mr-1 h-3 w-3" />
        {trend}
      </span>
      <span className="ml-2 text-slate-400">vs last month</span>
    </div>
  </LightGlassCard>
)

const NavItem = ({ icon: Icon, label, active, onClick }: any) => (
  <button
    onClick={onClick}
    className={`relative flex w-full items-center space-x-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 ${active
      ? 'bg-white text-blue-600 shadow-md shadow-slate-200/50'
      : 'text-slate-500 hover:bg-white/50 hover:text-slate-800'
      }`}
  >
    <Icon className={`h-5 w-5 ${active ? 'text-blue-600' : 'text-slate-400'}`} />
    <span>{label}</span>
    {active && (
      <motion.div
        layoutId="activeNavLight"
        className="absolute left-0 h-6 w-1 rounded-r-full bg-blue-500"
      />
    )}
  </button>
)

// --- Views ---

const DashboardView = () => {
  const [activeAgents, setActiveAgents] = useState<any[]>([])

  useEffect(() => {
    fetch('/agents').then(res => res.json()).then(data => {
      const active = (data.agents || []).filter((a: any) => a.active)
      setActiveAgents(active)
    }).catch(e => console.error(e))
  }, [])

  return (
    <div className="space-y-8">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={Phone} label="Total Calls" value="0" trend="0%" color="from-blue-500 to-cyan-500" delay={0.1} />
        <StatCard icon={Clock} label="Avg. Duration" value="0s" trend="0%" color="from-violet-500 to-fuchsia-500" delay={0.2} />
        <StatCard icon={Zap} label="Active Agents" value={activeAgents.length.toString()} trend="0" color="from-emerald-500 to-teal-500" delay={0.3} />
        <StatCard icon={DollarSign} label="Cost / Min" value="$0.00" trend="0%" color="from-orange-500 to-red-500" delay={0.4} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Live Activity Feed */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-bold text-slate-800">Active Agents</h3>
            <button className="text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors">View All</button>
          </div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="space-y-4">
            {activeAgents.length === 0 ? (
              <div className="text-center py-10 text-slate-400 bg-white/50 rounded-xl border border-slate-100">
                <p>No active agents found.</p>
              </div>
            ) : (
              activeAgents.map((agent, i) => (
                <div key={i} className="group flex items-center justify-between rounded-xl border border-slate-100 bg-white/50 p-4 transition-all hover:bg-white hover:shadow-md hover:shadow-slate-200/50 hover:border-white">
                  <div className="flex items-center space-x-4">
                    <div className="relative">
                      <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 p-[2px]">
                        <div className="h-full w-full rounded-full bg-white flex items-center justify-center">
                          <Cpu className="h-6 w-6 text-blue-600" />
                        </div>
                      </div>
                      <div className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-800 group-hover:text-blue-600 transition-colors">{agent.name}</h4>
                      <p className="text-xs text-slate-500 font-medium">{agent.role || 'Voice Agent'}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-8">
                    <button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors">
                      <MoreHorizontal className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </motion.div>

          <div className="mt-8">
            <h3 className="text-lg font-bold text-slate-800 mb-4">Real-time Analytics</h3>
            <LightGlassCard className="h-72 flex items-center justify-center border-dashed border-slate-300 bg-white/40">
              <div className="text-center">
                <div className="h-16 w-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Activity className="h-8 w-8 text-blue-500" />
                </div>
                <p className="text-slate-500 font-medium">Interactive Chart Visualization Area</p>
                <p className="text-sm text-slate-400 mt-1">Data is flowing in real-time...</p>
              </div>
            </LightGlassCard>
          </div>
        </div>

        {/* Right Panel */}
        <div className="space-y-6">
          <LightGlassCard delay={0.6} className="!bg-gradient-to-b !from-white !to-blue-50/50">
            <h3 className="text-lg font-bold text-slate-800 mb-6">System Health</h3>
            <div className="space-y-6">
              <div className="text-center text-slate-500 text-sm">System Operational</div>
            </div>
          </LightGlassCard>

          <LightGlassCard delay={0.7}>
            <h3 className="text-lg font-bold text-slate-800 mb-4">Recent Events</h3>
            <div className="text-center text-slate-400 text-sm py-4">No recent events</div>
          </LightGlassCard>
        </div>
      </div>
    </div>
  )
}





const LogsView = () => {
  const [calls, setCalls] = useState<any[]>([])
  const [selectedCall, setSelectedCall] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<'all' | 'ongoing' | 'finished'>('all')

  // Load calls
  const loadCalls = async () => {
    try {
      const response = await fetch('/api/calls')
      if (response.ok) {
        const result = await response.json()
        if (result.calls) {
          setCalls(result.calls)
          // Update selected call if it exists (for live updates)
          if (selectedCall) {
            const updatedCall = result.calls.find((c: any) => c.call_sid === selectedCall.call_sid)
            if (updatedCall) setSelectedCall(updatedCall)
          }
        }
      }
    } catch (error) {
      console.error('Error loading calls:', error)
    }
  }

  // Initial load and polling
  useEffect(() => {
    loadCalls()
    const interval = setInterval(loadCalls, 3000) // Poll every 3 seconds
    return () => clearInterval(interval)
  }, [selectedCall]) // Re-bind if selectedCall changes to keep it updated

  const filteredCalls = calls.filter(call => {
    if (filter === 'all') return true
    return call.status === filter
  })

  return (
    <div className="h-[calc(100vh-140px)] flex space-x-6">
      {/* Left Sidebar: Call List */}
      <div className="w-1/3 flex flex-col space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-slate-800">Call Logs</h2>
          <div className="flex space-x-2 bg-white p-1 rounded-lg border border-slate-200">
            {['all', 'ongoing', 'finished'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f as any)}
                className={`px-3 py-1 text-xs font-bold rounded-md capitalize transition-colors ${filter === f ? 'bg-blue-100 text-blue-700' : 'text-slate-500 hover:bg-slate-50'
                  }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-hide">
          {filteredCalls.length === 0 ? (
            <div className="text-center py-10 text-slate-400">No calls found</div>
          ) : (
            filteredCalls.map((call) => (
              <div
                key={call.call_sid}
                onClick={() => setSelectedCall(call)}
                className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 ${selectedCall?.call_sid === call.call_sid
                  ? 'bg-blue-50 border-blue-200 shadow-md ring-1 ring-blue-200'
                  : 'bg-white border-slate-100 hover:border-blue-200 hover:shadow-sm'
                  }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center space-x-2">
                    {call.status === 'ongoing' ? (
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                      </span>
                    ) : (
                      <div className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                    )}
                    <span className={`text-xs font-bold uppercase tracking-wider ${call.status === 'ongoing' ? 'text-emerald-600' : 'text-slate-500'
                      }`}>
                      {call.status}
                    </span>
                    {call.is_scheduled && (
                      <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 border border-purple-200 flex items-center">
                        <Calendar className="h-3 w-3 mr-1" />
                        SCHEDULED
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-slate-400">
                    {call.timestamp ? new Date(call.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-slate-800">{call.to_number || 'Unknown'}</p>
                    <p className="text-xs text-slate-500 mt-0.5">From: {call.from_number}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-medium text-slate-600">
                      {call.duration ? `${Number(call.duration).toFixed(0)}s` : '0s'}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Panel: Transcript */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        {selectedCall ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-slate-800 text-lg">
                  {selectedCall.to_number}
                </h3>
                <div className="flex items-center space-x-2 text-sm text-slate-500">
                  <span>{selectedCall.timestamp ? new Date(selectedCall.timestamp).toLocaleString() : 'N/A'}</span>
                  <span>•</span>
                  <span>Duration: {selectedCall.duration ? `${Number(selectedCall.duration).toFixed(0)}s` : '0s'}</span>
                  {selectedCall.is_scheduled && (
                    <>
                      <span>•</span>
                      <span className="text-purple-600 font-medium flex items-center" title={`Batch ID: ${selectedCall.scheduled_call_id}`}>
                        <Calendar className="h-3 w-3 mr-1" />
                        Scheduled Call
                      </span>
                    </>
                  )}
                </div>
              </div>
              {selectedCall.status === 'ongoing' && (
                <div className="flex items-center space-x-2 px-3 py-1.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold animate-pulse">
                  <Activity className="h-3 w-3" />
                  <span>LIVE CALL</span>
                </div>
              )}
            </div>

            {/* Transcript */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/30">
              {selectedCall.conversation && selectedCall.conversation.length > 0 ? (
                selectedCall.conversation.map((msg: any, idx: number) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm ${msg.role === 'user'
                        ? 'bg-blue-600 text-white rounded-tr-none'
                        : 'bg-white text-slate-700 border border-slate-100 rounded-tl-none'
                        }`}
                    >
                      <p>{msg.text}</p>
                      <p className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-slate-400'
                        }`}>
                        {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                  <MessageSquare className="h-12 w-12 mb-3 opacity-20" />
                  <p>No transcript available yet</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-400">
            <History className="h-16 w-16 mb-4 opacity-20" />
            <p className="text-lg font-medium">Select a call to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}

// Messaging Agents Management View
const MessagingAgentsView = () => {
  const [agents, setAgents] = useState<any[]>([])
  const [registeredPhones, setRegisteredPhones] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingPhones, setLoadingPhones] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [editAgent, setEditAgent] = useState<any | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'inactive' | 'phones'>('all')
  const [expandedSections, setExpandedSections] = useState({ basic: true, aiModels: false, behavior: false, advanced: false })
  const [registerPhoneModalOpen, setRegisterPhoneModalOpen] = useState(false)
  const [registrationSuccess, setRegistrationSuccess] = useState<any>(null)

  const [agentForm, setAgentForm] = useState({
    name: '',
    phoneNumber: '',
    systemPrompt: '',
    greeting: '',
    inferenceModel: 'gpt-4o-mini',
    temperature: 0.7,
    maxTokens: 500,
    active: true,
  })

  const [phoneForm, setPhoneForm] = useState({
    phoneNumber: '',
    provider: 'twilio',
    twilioAccountSid: '',
    twilioAuthToken: '',
  })

  // Load messaging agents
  const loadAgents = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/message-agents')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.agents)) {
          setAgents(result.agents.filter((a: any) => !a.isDeleted))
        }
      }
    } catch (error) {
      console.error('Error loading messaging agents:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load registered phones (only 'messages' type for messaging agents)
  const loadRegisteredPhones = async () => {
    try {
      setLoadingPhones(true)
      const response = await fetch('/api/phones?type=messages')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.phones)) {
          setRegisteredPhones(result.phones.filter((p: any) => !p.isDeleted))
        }
      }
    } catch (error) {
      console.error('Error loading phones:', error)
    } finally {
      setLoadingPhones(false)
    }
  }

  useEffect(() => {
    loadAgents()
    loadRegisteredPhones()
  }, [])

  // Handle create/update agent
  const handleSaveAgent = async () => {
    try {
      const endpoint = editAgent ? `/api/message-agents/${editAgent.id}` : '/api/message-agents'
      const method = editAgent ? 'PUT' : 'POST'

      const response = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...agentForm, direction: 'messaging' }),
      })

      if (response.ok) {
        setCreateModalOpen(false)
        setEditAgent(null)
        setAgentForm({
          name: '',
          phoneNumber: '',
          systemPrompt: '',
          greeting: '',
          inferenceModel: 'gpt-4o-mini',
          temperature: 0.7,
          maxTokens: 500,
          active: true,
        })
        setTimeout(() => loadAgents(), 500)
      }
    } catch (error) {
      console.error('Error saving messaging agent:', error)
    }
  }

  // Handle delete agent
  const handleDeleteAgent = async (agentId: string) => {
    if (confirm('Are you sure you want to delete this messaging agent?')) {
      try {
        const response = await fetch(`/api/message-agents/${agentId}`, { method: 'DELETE' })
        if (response.ok) {
          loadAgents()
        }
      } catch (error) {
        console.error('Error deleting messaging agent:', error)
      }
    }
  }

  // Handle toggle active
  const handleToggleActive = async (agent: any, active: boolean) => {
    try {
      const response = await fetch(`/api/message-agents/${agent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active }),
      })
      if (response.ok) {
        loadAgents()
      }
    } catch (error) {
      console.error('Error toggling messaging agent:', error)
    }
  }

  // Handle register phone
  const handleRegisterPhone = async () => {
    try {
      const response = await fetch('/api/phones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...phoneForm, type: 'messages' }),
      })

      if (response.ok) {
        const result = await response.json()
        setRegistrationSuccess(result)
        // setRegisterPhoneModalOpen(false) // Don't close, show success
        setPhoneForm({
          phoneNumber: '',
          provider: 'twilio',
          twilioAccountSid: '',
          twilioAuthToken: '',
        })
        loadRegisteredPhones()
      }
    } catch (error) {
      console.error('Error registering phone:', error)
    }
  }

  // Handle delete phone
  const handleDeletePhone = async (phoneId: string) => {
    if (confirm('Are you sure you want to delete this phone number?')) {
      try {
        console.log('Deleting phone:', phoneId)
        const response = await fetch(`/api/phones/${phoneId}`, { method: 'DELETE' })
        console.log('Delete response status:', response.status)

        if (response.ok) {
          const result = await response.json()
          console.log('Delete result:', result)
          alert('Phone number deleted successfully!')
          loadRegisteredPhones()
        } else {
          const errorText = await response.text()
          console.error('Delete failed:', response.status, errorText)
          alert(`Failed to delete phone number: ${errorText}`)
        }
      } catch (error) {
        console.error('Error deleting phone:', error)
        alert(`Error deleting phone number: ${error}`)
      }
    }
  }

  // Filter agents
  const filteredAgents = agents.filter(agent => {
    if (activeTab === 'active') return agent.active !== false
    if (activeTab === 'inactive') return agent.active === false
    return true
  })

  return (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Messaging Agents</h2>
          <p className="text-slate-600">Create and manage SMS/Messaging Agents for your Business.</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setCreateModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105 flex items-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Create Messaging Agent</span>
          </button>
          <button
            onClick={() => setRegisterPhoneModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-white text-slate-700 text-sm font-bold shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 transition-colors flex items-center space-x-2"
          >
            <Phone className="h-4 w-4" />
            <span>Register Phone</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 border-b border-slate-200">
        {[
          { id: 'all', label: 'All Agents' },
          { id: 'active', label: 'Active Agents' },
          { id: 'inactive', label: 'Inactive Agents' },
          { id: 'phones', label: 'Registered Phone Numbers' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === tab.id
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-600 hover:text-slate-900'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'phones' ? (
        <LightGlassCard className="!p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <th className="p-4">Phone Number</th>
                  <th className="p-4">Provider</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Created</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="text-sm text-slate-700 font-medium divide-y divide-slate-100">
                {registeredPhones.map((phone, i) => (
                  <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                    <td className="p-4 font-mono">{phone.phoneNumber}</td>
                    <td className="p-4 capitalize">{phone.provider}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">
                        Active
                      </span>
                    </td>
                    <td className="p-4 text-slate-500">
                      {phone.created_at ? new Date(phone.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleDeletePhone(phone.id)}
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
                {registeredPhones.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-500">
                      No registered phone numbers yet. Click "Register Phone" to add one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </LightGlassCard>
      ) : (
        <LightGlassCard className="!p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <th className="p-4">Agent Name</th>
                  <th className="p-4">Phone Number</th>
                  <th className="p-4">Model</th>
                  <th className="p-4">Active</th>
                  <th className="p-4">Last Updated</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="text-sm text-slate-700 font-medium divide-y divide-slate-100">
                {filteredAgents.map((agent, i) => (
                  <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                    <td className="p-4">
                      <div className="flex flex-col gap-1.5">
                        <span className="font-bold text-slate-900">{agent.name}</span>
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold w-fit ${agent.active !== false ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                          }`}>
                          {agent.active !== false ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </td>
                    <td className="p-4 font-mono text-slate-600">{agent.phoneNumber}</td>
                    <td className="p-4 text-slate-600">{agent.inferenceModel || 'gpt-4o-mini'}</td>
                    <td className="p-4">
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={agent.active !== false}
                          onChange={(e) => handleToggleActive(agent, e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        <span className="ml-3 text-sm font-medium text-slate-700">
                          {agent.active !== false ? 'Active' : 'Inactive'}
                        </span>
                      </label>
                    </td>
                    <td className="p-4 text-slate-500">
                      {agent.updated_at ? new Date(agent.updated_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => {
                            setEditAgent(agent)
                            setAgentForm({
                              name: agent.name,
                              phoneNumber: agent.phoneNumber,
                              systemPrompt: agent.systemPrompt || '',
                              greeting: agent.greeting || '',
                              inferenceModel: agent.inferenceModel || 'gpt-4o-mini',
                              temperature: agent.temperature || 0.7,
                              maxTokens: agent.maxTokens || 500,
                              active: agent.active !== false,
                            })
                            setCreateModalOpen(true)
                          }}
                          className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteAgent(agent.id)}
                          className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredAgents.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No messaging agents found. Click "Create Messaging Agent" to add one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </LightGlassCard>
      )}

      {/* Create/Edit Agent Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="p-6 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold text-slate-900">
                    {editAgent ? 'Edit Messaging Agent' : 'Create New Messaging Agent'}
                  </h3>
                  <p className="text-sm text-slate-600 mt-1">
                    Configure your SMS messaging agent with custom behavior settings
                  </p>
                </div>
                <button
                  onClick={() => {
                    setCreateModalOpen(false)
                    setEditAgent(null)
                  }}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-slate-600" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              {/* Basic Information */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, basic: !prev.basic }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Settings className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">Basic Information</span>
                  </div>
                  {expandedSections.basic ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.basic && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Agent Name *</label>
                      <input
                        type="text"
                        value={agentForm.name}
                        onChange={(e) => setAgentForm({ ...agentForm, name: e.target.value })}
                        placeholder="e.g., Customer Support Bot"
                        disabled={!!editAgent}
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none disabled:bg-slate-100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Phone Number *</label>
                      {editAgent ? (
                        <input
                          type="text"
                          value={agentForm.phoneNumber}
                          readOnly
                          className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-600 shadow-sm ring-1 ring-slate-200"
                        />
                      ) : (
                        <select
                          value={agentForm.phoneNumber}
                          onChange={(e) => setAgentForm({ ...agentForm, phoneNumber: e.target.value })}
                          className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                          <option value="">Select a registered phone number</option>
                          {registeredPhones.map(phone => (
                            <option key={phone.id} value={phone.phoneNumber}>{phone.phoneNumber}</option>
                          ))}
                        </select>
                      )}
                    </div>
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={agentForm.active}
                        onChange={(e) => setAgentForm({ ...agentForm, active: e.target.checked })}
                        className="h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-slate-700">Active (Enable agent to receive messages)</span>
                    </label>
                  </div>
                )}
              </div>

              {/* AI Model Configuration */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, aiModels: !prev.aiModels }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Bot className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">AI Model Configuration</span>
                  </div>
                  {expandedSections.aiModels ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.aiModels && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Inference Model *</label>
                      <select
                        value={agentForm.inferenceModel}
                        onChange={(e) => setAgentForm({ ...agentForm, inferenceModel: e.target.value })}
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring- blue-500 outline-none"
                      >
                        <option value="gpt-4o-mini">gpt-4o-mini (Fast, Cost-effective)</option>
                        <option value="gpt-4o">gpt-4o (More Capable)</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              {/* Behavior Configuration */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, behavior: !prev.behavior }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">Behavior Configuration</span>
                  </div>
                  {expandedSections.behavior ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.behavior && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">System Prompt *</label>
                      <textarea
                        value={agentForm.systemPrompt}
                        onChange={(e) => setAgentForm({ ...agentForm, systemPrompt: e.target.value })}
                        placeholder="You are a helpful customer support agent..."
                        rows={4}
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Greeting Message</label>
                      <input
                        type="text"
                        value={agentForm.greeting}
                        onChange={(e) => setAgentForm({ ...agentForm, greeting: e.target.value })}
                        placeholder="Hi! How can I help you today?"
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Advanced Configuration */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, advanced: !prev.advanced }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">Advanced Configuration</span>
                  </div>
                  {expandedSections.advanced ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.advanced && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">
                        Temperature: {agentForm.temperature.toFixed(1)}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={agentForm.temperature}
                        onChange={(e) => setAgentForm({ ...agentForm, temperature: parseFloat(e.target.value) })}
                        className="w-full"
                      />
                      <p className="text-xs text-slate-500 mt-1">Controls response randomness (0.0 = deterministic, 2.0 = creative)</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Max Tokens</label>
                      <input
                        type="number"
                        min="1"
                        max="4000"
                        value={agentForm.maxTokens}
                        onChange={(e) => setAgentForm({ ...agentForm, maxTokens: parseInt(e.target.value) || 500 })}
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                      <p className="text-xs text-slate-500 mt-1">Maximum response length (1-4000 tokens)</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="p-6 border-t border-slate-200 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setCreateModalOpen(false)
                  setEditAgent(null)
                }}
                className="px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAgent}
                className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
              >
                {editAgent ? 'Update Agent' : 'Create Agent'}
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Register Phone Modal */}
      {registerPhoneModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl shadow-2xl max-w-lg w-full"
          >
            <div className="p-6 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Phone className="h-6 w-6 text-blue-600" />
                  <div>
                    <h3 className="text-2xl font-bold text-slate-900">
                      {registrationSuccess ? 'Registration Successful!' : 'Register Phone Number'}
                    </h3>
                    <p className="text-sm text-slate-600 mt-1">
                      {registrationSuccess
                        ? 'Configure these webhooks in your Twilio Console'
                        : 'Register your Twilio phone number with credentials to use it for messaging agents'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setRegisterPhoneModalOpen(false)
                    setRegistrationSuccess(null)
                  }}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-slate-600" />
                </button>
              </div>
            </div>

            {registrationSuccess ? (
              <div className="p-6 space-y-6">
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3">
                  <div className="p-2 bg-emerald-100 rounded-full shrink-0">
                    <Check className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <h4 className="font-bold text-emerald-900">Phone Number Registered</h4>
                    <p className="text-sm text-emerald-700 mt-1">
                      {registrationSuccess.message || "Your phone number has been successfully registered."}
                    </p>
                  </div>
                </div>

                {registrationSuccess.webhookConfiguration?.instructions?.includes("automatically") ? (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                    <p className="text-sm text-blue-800 font-medium">
                      ✨ Great news! We detected ngrok and automatically configured your Twilio webhook.
                    </p>
                    <p className="text-xs text-blue-600 mt-1">
                      You don't need to do anything else.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-bold text-slate-700 mb-2">
                        A MESSAGE COMES IN (Webhook)
                      </label>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono text-slate-600 break-all">
                          {registrationSuccess.webhookConfiguration?.smsWebhookUrl || registrationSuccess.smsWebhookUrl}
                        </code>
                        <button
                          onClick={() => navigator.clipboard.writeText(registrationSuccess.webhookConfiguration?.smsWebhookUrl || registrationSuccess.smsWebhookUrl)}
                          className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Copy URL"
                        >
                          <Copy className="h-5 w-5" />
                        </button>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Set this URL in Twilio Console → Phone Numbers → Manage → Active Numbers → [Your Number] → Messaging → "A MESSAGE COMES IN" (Webhook)
                      </p>
                    </div>
                  </div>
                )}

                <div className="pt-4 border-t border-slate-200 flex justify-end">
                  <button
                    onClick={() => {
                      setRegisterPhoneModalOpen(false)
                      setRegistrationSuccess(null)
                    }}
                    className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Provider *</label>
                    <select
                      value={phoneForm.provider}
                      onChange={(e) => setPhoneForm({ ...phoneForm, provider: e.target.value })}
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      <option value="twilio">Twilio</option>
                    </select>
                    <p className="text-xs text-slate-500 mt-1">Select the phone service provider (currently only Twilio is supported)</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Phone Number *</label>
                    <input
                      type="tel"
                      value={phoneForm.phoneNumber}
                      onChange={(e) => setPhoneForm({ ...phoneForm, phoneNumber: e.target.value })}
                      placeholder="+1 555 123 4567"
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-500 mt-1">Your Twilio phone number in E.164 format</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Twilio Account SID *</label>
                    <input
                      type="text"
                      value={phoneForm.twilioAccountSid}
                      onChange={(e) => setPhoneForm({ ...phoneForm, twilioAccountSid: e.target.value })}
                      placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-mono text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-500 mt-1">Found in Twilio Console → Dashboard → Account Info</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Twilio Auth Token *</label>
                    <input
                      type="password"
                      value={phoneForm.twilioAuthToken}
                      onChange={(e) => setPhoneForm({ ...phoneForm, twilioAuthToken: e.target.value })}
                      placeholder="Enter your Twilio Auth Token"
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-mono text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-500 mt-1">Found in Twilio Console → Dashboard → Account Info → Auth Token</p>
                  </div>
                </div>

                <div className="p-6 border-t border-slate-200 flex justify-end space-x-3">
                  <button
                    onClick={() => setRegisterPhoneModalOpen(false)}
                    className="px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRegisterPhone}
                    className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
                  >
                    Register Phone
                  </button>
                </div>
              </>
            )}
          </motion.div>
        </div>
      )}
    </div>
  )
}

const MessagesView = () => {
  const [conversations, setConversations] = useState<any[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [messageText, setMessageText] = useState('')
  const [sending, setSending] = useState(false)

  const fetchConversations = () => {
    fetch('/api/messages')
      .then(res => res.json())
      .then(data => {
        setConversations(data.messages || [])
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }

  useEffect(() => {
    fetchConversations()

    const intervalId = setInterval(() => {
      fetchConversations()
    }, 5000)

    return () => clearInterval(intervalId)
  }, [])

  const handleSendMessage = async () => {
    if (!messageText.trim() || !selectedConversation || sending) return

    const fromNumber = selectedConversation.agentNumber
    const toNumber = selectedConversation.callerNumber

    if (!fromNumber || !toNumber) {
      alert('Missing phone number information')
      return
    }

    setSending(true)
    try {
      const response = await fetch('/api/messages/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from: fromNumber,
          to: toNumber,
          body: messageText.trim()
        })
      })

      const data = await response.json()
      
      if (response.ok && data.success) {
        setMessageText('')
        // Refresh conversations to show the new message
        setTimeout(() => {
          fetchConversations()
        }, 500)
      } else {
        alert(data.detail || 'Failed to send message')
      }
    } catch (error) {
      console.error('Error sending message:', error)
      alert('Failed to send message. Please try again.')
    } finally {
      setSending(false)
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const selectedConversation = conversations.find(c => 
    c.conversation_id === selectedId || c.id === selectedId
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-140px)] text-slate-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (conversations.length === 0) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-140px)] text-slate-400">
        <div className="text-center">
          <MessageSquare className="h-16 w-16 mx-auto mb-4 opacity-20" />
          <h3 className="text-lg font-bold text-slate-600">Messages</h3>
          <p>No message history available.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-140px)]">
      {/* Conversation List */}
      <div className="lg:col-span-1 bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden flex flex-col shadow-sm">
        <div className="p-4 border-b border-slate-100 bg-white/40">
          <h3 className="font-bold text-slate-800">Conversations</h3>
        </div>
        <div className="overflow-y-auto flex-1">
          {conversations.map((conv) => {
            const convId = conv.conversation_id || conv.id;
            return (
            <div
              key={convId}
              onClick={() => setSelectedId(convId)}
              className={`p-4 border-b border-slate-50 cursor-pointer hover:bg-white/80 transition-colors ${selectedId === convId ? 'bg-blue-50/50 border-l-4 border-l-blue-500' : 'border-l-4 border-l-transparent'}`}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded uppercase tracking-wider">Customer</span>
                    <span className="text-xs text-slate-400">{conv.timestamp ? new Date(conv.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</span>
                  </div>
                  <span className="font-bold text-slate-800 text-sm">{conv.callerNumber || 'Unknown'}</span>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-slate-400 font-medium">Agent:</span>
                    <span className="text-[10px] text-slate-500 font-mono">{conv.agentNumber || 'Unknown'}</span>
                  </div>
                </div>
              </div>
              <p className="text-sm text-slate-500 truncate italic">"{conv.latest_message || 'No messages'}"</p>
            </div>
            );
          })}
        </div>
      </div>

      {/* Chat View */}
      <div className="lg:col-span-2 bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden flex flex-col shadow-sm">
        {selectedConversation ? (
          <>
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-white/40">
              <div className="flex items-center space-x-3">
                <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
                  <User className="h-6 w-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded uppercase tracking-wider">Customer</span>
                  </div>
                  <h3 className="font-bold text-slate-800 text-base">{selectedConversation.callerNumber || 'Unknown'}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded uppercase tracking-wider">Agent</span>
                    <span className="text-xs text-slate-600 font-mono">{selectedConversation.agentNumber || 'Unknown'}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30">
              {selectedConversation.conversation && selectedConversation.conversation.length > 0 ? (
                selectedConversation.conversation.map((msg: any, idx: number) => {
                // Determine if this is a customer message or agent message
                // Priority order for maximum compatibility:
                // 1. role field: "user" or "customer" = customer message, "assistant" = agent message
                // 2. direction field: "inbound" = customer message, "outbound" = agent message
                // 3. sender field: "customer" = customer message
                const role = msg.role?.toLowerCase() || '';
                const direction = msg.direction?.toLowerCase() || '';
                const sender = msg.sender?.toLowerCase() || '';
                
                // Determine message source based on priority:
                // 1. Check role first (most reliable)
                // 2. Then check direction
                // 3. Then check sender
                // Default to agent if unclear (for backward compatibility)
                let messageFromCustomer = false;
                
                if (role === 'user' || role === 'customer') {
                  messageFromCustomer = true;
                } else if (role === 'assistant' || role === 'agent') {
                  messageFromCustomer = false;
                } else if (direction === 'inbound') {
                  messageFromCustomer = true;
                } else if (direction === 'outbound') {
                  messageFromCustomer = false;
                } else if (sender === 'customer') {
                  messageFromCustomer = true;
                }
                // If none of the above match, default to agent (false)
                
                return (
                  <div key={idx} className={`flex ${messageFromCustomer ? 'justify-start' : 'justify-end'}`}>
                    <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                      messageFromCustomer
                        ? 'bg-slate-200/80 text-slate-900 rounded-tl-none shadow-sm border border-slate-300/50'
                        : 'bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-tr-none shadow-md shadow-blue-500/30'
                    }`}>
                      <p className="text-sm leading-relaxed">{msg.text || msg.body || ''}</p>
                      <p className={`text-[10px] mt-1.5 ${messageFromCustomer ? 'text-slate-500' : 'text-blue-100'}`}>
                        {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                      </p>
                    </div>
                  </div>
                );
              })
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                  <MessageSquare className="h-12 w-12 mb-3 opacity-20" />
                  <p>No messages in this conversation yet</p>
                </div>
              )}
            </div>
            <div className="p-4 bg-white/60 border-t border-slate-100 backdrop-blur-md">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Type a message..."
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={sending}
                  className="w-full pl-4 pr-12 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white/80 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={!messageText.trim() || sending}
                  className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {sending ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <div className="h-16 w-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              <MessageSquare className="h-8 w-8 text-slate-300" />
            </div>
            <p className="font-medium">Select a conversation to view messages</p>
          </div>
        )}
      </div>
    </div>
  )
}

const VoiceCustomizationView = () => {
  const [playingVoice, setPlayingVoice] = useState<string | null>(null)

  const voices = [
    { name: 'alloy', used: true, description: 'Balanced and neutral' },
    { name: 'echo', used: false, description: 'Clear and articulate' },
    { name: 'fable', used: true, description: 'Warm and friendly' },
    { name: 'onyx', used: false, description: 'Deep and authoritative' },
    { name: 'nova', used: true, description: 'Energetic and bright' },
    { name: 'shimmer', used: false, description: 'Soft and gentle' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Voice Customization</h2>
        <p className="text-slate-600">Preview and test all available TTS voices used in your agents.</p>
      </div>

      {/* Info Card */}
      <LightGlassCard delay={0.1} className="!bg-gradient-to-b !from-blue-50/50 !to-white">
        <div className="flex items-start gap-3">
          <Volume2 className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900 mb-1">Automated Voice Listing</p>
            <p className="text-sm text-blue-700">
              Voices are automatically fetched from your agents. Click the play button to hear a demo.
            </p>
          </div>
        </div>
      </LightGlassCard>

      {/* Voices Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {voices.map((voice, i) => (
          <LightGlassCard
            key={voice.name}
            delay={i * 0.1}
            className={`group hover:bg-white/80 transition-all ${playingVoice === voice.name ? 'ring-2 ring-blue-500 !bg-blue-50/50' : ''}`}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 capitalize">{voice.name}</h3>
                <p className="text-xs text-slate-500 mt-1">{voice.description}</p>
                {voice.used && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 mt-2">
                    Used in agents
                  </span>
                )}
              </div>
              <Volume2 className={`h-6 w-6 ${playingVoice === voice.name ? 'text-blue-600' : 'text-slate-400'}`} />
            </div>

            <button
              onClick={() => setPlayingVoice(playingVoice === voice.name ? null : voice.name)}
              className={`w-full rounded-xl py-3 font-bold text-sm transition-all flex items-center justify-center space-x-2 ${playingVoice === voice.name
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30 hover:bg-blue-700'
                : 'bg-slate-100 text-slate-900 hover:bg-slate-200'
                }`}
            >
              {playingVoice === voice.name ? (
                <>
                  <Pause className="h-4 w-4" />
                  <span>Playing...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  <span>Play Demo</span>
                </>
              )}
            </button>
          </LightGlassCard>
        ))}
      </div>
    </div>
  )
}

const EndpointsView = () => {
  const [copiedEndpoint, setCopiedEndpoint] = useState<string | null>(null)
  const [baseUrl, setBaseUrl] = useState('https://api.dodash.ai')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setBaseUrl(window.location.origin)
    }
  }, [])

  const endpoints = [
    {
      name: 'Voice Call Webhook',
      url: `${baseUrl}/webhooks/twilio/incoming`,
      status: 'active',
      description: 'Receives incoming call events from Twilio'
    },
    {
      name: 'SMS Webhook',
      url: `${baseUrl}/webhooks/twilio/sms`,
      status: 'active',
      description: 'Receives incoming SMS messages'
    },
    {
      name: 'Status Callback',
      url: `${baseUrl}/webhooks/twilio/status`,
      status: 'active',
      description: 'Receives call status updates'
    },
    {
      name: 'API Base URL',
      url: `${baseUrl}`,
      status: 'configured',
      description: 'Main API endpoint for agent management'
    },
  ]

  const handleCopy = (url: string, name: string) => {
    setCopiedEndpoint(name)
    setTimeout(() => setCopiedEndpoint(null), 2000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Endpoints & Webhooks</h2>
        <p className="text-slate-600">Manage API endpoints and webhook URLs for your voice agents.</p>
      </div>

      {/* Info Card */}
      <LightGlassCard delay={0.1} className="!bg-gradient-to-b !from-purple-50/50 !to-white">
        <div className="flex items-start gap-3">
          <Globe className="h-5 w-5 text-purple-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-purple-900 mb-1">Webhook Configuration</p>
            <p className="text-sm text-purple-700">
              These URLs are used by Twilio to send call and message events to your system.
            </p>
          </div>
        </div>
      </LightGlassCard>

      {/* Endpoints List */}
      <div className="space-y-4">
        {endpoints.map((endpoint, i) => (
          <LightGlassCard key={i} delay={i * 0.1} className="hover:bg-white/80 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <Link className="h-5 w-5 text-slate-400" />
                  <h3 className="text-lg font-semibold text-slate-900">{endpoint.name}</h3>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold capitalize ${endpoint.status === 'active' ? 'bg-emerald-100 text-emerald-700' :
                    'bg-blue-100 text-blue-700'
                    }`}>
                    {endpoint.status}
                  </span>
                </div>
                <p className="text-sm text-slate-500 mb-3">{endpoint.description}</p>
                <div className="flex items-center space-x-2 bg-slate-50 rounded-lg p-3 border border-slate-200">
                  <code className="flex-1 text-xs font-mono text-slate-700">{endpoint.url}</code>
                  <button
                    onClick={() => handleCopy(endpoint.url, endpoint.name)}
                    className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-blue-600 transition-colors"
                  >
                    {copiedEndpoint === endpoint.name ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </LightGlassCard>
        ))}
      </div>

      {/* Test Webhook Section */}
      <LightGlassCard delay={0.5}>
        <h3 className="text-lg font-bold text-slate-800 mb-4">Test Webhook</h3>
        <p className="text-sm text-slate-600 mb-4">Send a test event to verify your webhook configuration.</p>
        <button className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105">
          Send Test Event
        </button>
      </LightGlassCard>
    </div>
  )
}

const ActivityLogsView = () => {
  const [activities, setActivities] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [callsRes, msgsRes] = await Promise.all([
          fetch('/api/calls'),
          fetch('/api/messages')
        ])

        let combined: any[] = []

        if (callsRes.ok) {
          const callsData = await callsRes.json()
          if (callsData.calls) {
            combined = combined.concat(callsData.calls.map((c: any) => ({
              type: 'call',
              id: c.call_sid,
              timestamp: c.timestamp || c.start_time || new Date().toISOString(),
              details: c
            })))
          }
        }

        if (msgsRes.ok) {
          const msgsData = await msgsRes.json()
          if (msgsData.messages) {
            combined = combined.concat(msgsData.messages.map((m: any) => ({
              type: 'message',
              id: m.conversation_id,
              timestamp: m.timestamp || new Date().toISOString(),
              details: m
            })))
          }
        }

        combined.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        setActivities(combined)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // Auto-refresh every 5 seconds to show updated call status
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="flex justify-center p-10"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div></div>

  if (activities.length === 0) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-140px)] text-slate-400">
        <div className="text-center">
          <Activity className="h-16 w-16 mx-auto mb-4 opacity-20" />
          <h3 className="text-lg font-bold text-slate-600">Activity Logs</h3>
          <p>No recent activity.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-800">Activity Timeline</h2>
        <span className="text-sm text-slate-500">Recent system events</span>
      </div>

      <div className="relative border-l-2 border-slate-200 ml-4 space-y-8 pb-10">
        {activities.map((item, i) => (
          <div key={i} className="relative pl-8">
            <div className={`absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 border-white shadow-sm ${item.type === 'call' ? 'bg-emerald-500' : 'bg-blue-500'
              }`} />

            <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center space-x-2">
                  {item.type === 'call' ? <Phone className="h-4 w-4 text-emerald-600" /> : <MessageSquare className="h-4 w-4 text-blue-600" />}
                  <span className="font-bold text-slate-700 capitalize">{item.type === 'call' ? 'Voice Call' : 'Message Conversation'}</span>
                </div>
                <span className="text-xs text-slate-400">{new Date(item.timestamp).toLocaleString()}</span>
              </div>

              {item.type === 'call' ? (
                <div className="text-sm text-slate-600">
                  <p>Call with <span className="font-semibold">{item.details.to_number || 'Unknown'}</span></p>
                  <p className="text-xs text-slate-400 mt-1">Duration: {item.details.duration ? Number(item.details.duration).toFixed(0) : 0}s • Status: {item.details.status}</p>
                </div>
              ) : (
                <div className="text-sm text-slate-600">
                  <p>Conversation with <span className="font-semibold">{item.details.callerNumber || 'Unknown'}</span></p>
                  <p className="text-xs text-slate-400 mt-1 italic">"{item.details.latest_message}"</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const SettingsView = () => {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Settings</h2>
        <p className="text-slate-600">Manage your account and system configuration.</p>
      </div>

      {/* Account Information */}
      <LightGlassCard delay={0.1}>
        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center space-x-2">
          <User className="h-5 w-5 text-blue-600" />
          <span>Account Information</span>
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Company Name</label>
            <input
              type="text"
              defaultValue="DoDash AI"
              className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Email Address</label>
            <input
              type="email"
              defaultValue="admin@dodash.ai"
              className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Plan</label>
            <div className="flex items-center space-x-3">
              <span className="px-4 py-2 rounded-full bg-blue-100 text-blue-700 text-sm font-bold">Pro Plan</span>
              <button className="text-sm text-blue-600 font-bold hover:text-blue-700">Upgrade</button>
            </div>
          </div>
        </div>
      </LightGlassCard>

      {/* API Configuration */}
      <LightGlassCard delay={0.2}>
        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center space-x-2">
          <Globe className="h-5 w-5 text-purple-600" />
          <span>API Configuration</span>
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">API Key</label>
            <div className="flex items-center space-x-2">
              <input
                type="password"
                defaultValue="sk_live_abc123xyz789"
                className="flex-1 rounded-xl border-none bg-white px-4 py-3 text-sm font-mono text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
              />
              <button className="px-4 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors">
                Show
              </button>
              <button className="px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-colors">
                Regenerate
              </button>
            </div>
          </div>
        </div>
      </LightGlassCard>

      {/* Voice Settings */}
      <LightGlassCard delay={0.3}>
        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center space-x-2">
          <Volume2 className="h-5 w-5 text-emerald-600" />
          <span>Default Voice Settings</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">TTS Model</label>
            <select className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none">
              <option>OpenAI TTS</option>
              <option>Google Cloud TTS</option>
              <option>ElevenLabs</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Default Voice</label>
            <select className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none">
              <option>alloy</option>
              <option>echo</option>
              <option>fable</option>
              <option>nova</option>
              <option>shimmer</option>
              <option>onyx</option>
            </select>
          </div>
        </div>
      </LightGlassCard>

      {/* Notifications */}
      <LightGlassCard delay={0.4}>
        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center space-x-2">
          <Bell className="h-5 w-5 text-amber-600" />
          <span>Notification Preferences</span>
        </h3>
        <div className="space-y-3">
          {[
            { label: 'Email notifications for new calls', checked: true },
            { label: 'SMS alerts for system errors', checked: false },
            { label: 'Weekly performance reports', checked: true },
            { label: 'Agent status updates', checked: true },
          ].map((pref, i) => (
            <label key={i} className="flex items-center space-x-3 cursor-pointer group">
              <input
                type="checkbox"
                defaultChecked={pref.checked}
                className="h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">{pref.label}</span>
            </label>
          ))}
        </div>
      </LightGlassCard>

      {/* Save Button */}
      <div className="flex justify-end space-x-3">
        <button className="px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors">
          Cancel
        </button>
        <button className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105">
          Save Changes
        </button>
      </div>
    </div>
  )
}

const IncomingAgentView = () => {
  const [agents, setAgents] = useState<any[]>([])
  const [registeredPhones, setRegisteredPhones] = useState<any[]>([])
  const [loadingAgents, setLoadingAgents] = useState(false)
  const [loadingPhones, setLoadingPhones] = useState(false)
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'inactive' | 'phones'>('all')
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [registerPhoneModalOpen, setRegisterPhoneModalOpen] = useState(false)
  const [registrationSuccess, setRegistrationSuccess] = useState<any>(null)
  const [editAgent, setEditAgent] = useState<any | null>(null)

  // Form states for Create Agent Modal
  const [agentForm, setAgentForm] = useState({
    name: '',
    phoneNumber: '',
    sttModel: 'whisper-1',
    inferenceModel: 'gpt-4o-mini',
    ttsModel: 'tts-1',
    ttsVoice: 'alloy',
    systemPrompt: '',
    greeting: '',
    temperature: 0.7,
    maxTokens: 500,
    active: true,
  })

  // Form states for Register Phone Modal
  const [phoneForm, setPhoneForm] = useState({
    phoneNumber: '',
    provider: 'twilio',
    twilioAccountSid: '',
    twilioAuthToken: '',
  })

  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    aiModels: true,
    behavior: false,
    advanced: false,
  })

  // Load agents
  const loadAgents = async () => {
    try {
      setLoadingAgents(true)
      const response = await fetch('/agents?include_deleted=false')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.agents)) {
          const incomingAgents = result.agents.filter((a: any) =>
            (a.direction === 'incoming' || a.direction === 'inbound') && !a.isDeleted
          )
          setAgents(incomingAgents)
        }
      }
    } catch (error) {
      console.error('Error loading agents:', error)
    } finally {
      setLoadingAgents(false)
    }
  }

  // Load registered phones
  const loadRegisteredPhones = async () => {
    try {
      setLoadingPhones(true)
      const response = await fetch('/api/phones?type=calls')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.phones)) {
          setRegisteredPhones(result.phones.filter((p: any) => !p.isDeleted))
        }
      }
    } catch (error) {
      console.error('Error loading phones:', error)
    } finally {
      setLoadingPhones(false)
    }
  }

  useEffect(() => {
    loadAgents()
    loadRegisteredPhones()
  }, [])

  // Handle create/update agent
  const handleSaveAgent = async () => {
    try {
      const endpoint = editAgent ? `/agents/${editAgent.id}` : '/agents'
      const method = editAgent ? 'PUT' : 'POST'

      const response = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...agentForm, direction: 'incoming' }),
      })

      if (response.ok) {
        setCreateModalOpen(false)
        setEditAgent(null)
        setAgentForm({
          name: '',
          phoneNumber: '',
          sttModel: 'whisper-1',
          inferenceModel: 'gpt-4o-mini',
          ttsModel: 'tts-1',
          ttsVoice: 'alloy',
          systemPrompt: '',
          greeting: '',
          temperature: 0.7,
          maxTokens: 500,
          active: true,
        })
        setTimeout(() => loadAgents(), 500)
      }
    } catch (error) {
      console.error('Error saving agent:', error)
    }
  }

  // Handle delete agent
  const handleDeleteAgent = async (agentId: string) => {
    if (confirm('Are you sure you want to delete this agent?')) {
      try {
        const response = await fetch(`/agents/${agentId}`, { method: 'DELETE' })
        if (response.ok) {
          loadAgents()
        }
      } catch (error) {
        console.error('Error deleting agent:', error)
      }
    }
  }

  // Handle toggle active
  const handleToggleActive = async (agent: any, active: boolean) => {
    try {
      const response = await fetch(`/agents/${agent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active }),
      })
      if (response.ok) {
        loadAgents()
      }
    } catch (error) {
      console.error('Error toggling agent:', error)
    }
  }

  // Handle register phone
  const handleRegisterPhone = async () => {
    try {
      const response = await fetch('/api/phones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...phoneForm, type: 'calls' }),
      })

      if (response.ok) {
        const result = await response.json()
        setRegistrationSuccess(result)
        // setRegisterPhoneModalOpen(false) // Don't close, show success
        setPhoneForm({
          phoneNumber: '',
          provider: 'twilio',
          twilioAccountSid: '',
          twilioAuthToken: '',
        })
        loadRegisteredPhones()
      }
    } catch (error) {
      console.error('Error registering phone:', error)
    }
  }

  // Handle delete phone
  const handleDeletePhone = async (phoneId: string) => {
    if (confirm('Are you sure you want to delete this phone number?')) {
      try {
        console.log('Deleting phone:', phoneId)
        const response = await fetch(`/api/phones/${phoneId}`, { method: 'DELETE' })
        console.log('Delete response status:', response.status)

        if (response.ok) {
          const result = await response.json()
          console.log('Delete result:', result)
          alert('Phone number deleted successfully!')
          loadRegisteredPhones()
        } else {
          const errorText = await response.text()
          console.error('Delete failed:', response.status, errorText)
          alert(`Failed to delete phone number: ${errorText}`)
        }
      } catch (error) {
        console.error('Error deleting phone:', error)
        alert(`Error deleting phone number: ${error}`)
      }
    }
  }

  // Filter agents
  const filteredAgents = agents.filter(agent => {
    if (activeTab === 'active') return agent.active !== false
    if (activeTab === 'inactive') return agent.active === false
    return true
  })

  return (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Incoming Agent</h2>
          <p className="text-slate-600">Create and manage Voice Agents for your Business.</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setCreateModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105 flex items-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Create Agent</span>
          </button>
          <button
            onClick={() => setRegisterPhoneModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-white text-slate-700 text-sm font-bold shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 transition-colors flex items-center space-x-2"
          >
            <Phone className="h-4 w-4" />
            <span>Register Phone</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 border-b border-slate-200">
        {[
          { id: 'all', label: 'All Agents' },
          { id: 'active', label: 'Active Agents' },
          { id: 'inactive', label: 'Inactive Agents' },
          { id: 'phones', label: 'Registered Phone Numbers' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === tab.id
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-slate-600 hover:text-slate-900'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'phones' ? (
        <LightGlassCard className="!p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <th className="p-4">Phone Number</th>
                  <th className="p-4">Provider</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Created</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="text-sm text-slate-700 font-medium divide-y divide-slate-100">
                {registeredPhones.map((phone, i) => (
                  <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                    <td className="p-4 font-mono">{phone.phoneNumber}</td>
                    <td className="p-4 capitalize">{phone.provider}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">
                        Active
                      </span>
                    </td>
                    <td className="p-4 text-slate-500">
                      {phone.created_at ? new Date(phone.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleDeletePhone(phone.id)}
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
                {registeredPhones.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-500">
                      No registered phone numbers yet. Click "Register Phone" to add one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </LightGlassCard>
      ) : (
        <LightGlassCard className="!p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <th className="p-4">Agent Name</th>
                  <th className="p-4">Direction</th>
                  <th className="p-4">Phone Number</th>
                  <th className="p-4">Active</th>
                  <th className="p-4">Last Updated</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="text-sm text-slate-700 font-medium divide-y divide-slate-100">
                {filteredAgents.map((agent, i) => (
                  <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                    <td className="p-4">
                      <div className="flex flex-col gap-1.5">
                        <span className="font-bold text-slate-900">{agent.name}</span>
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold w-fit ${agent.active !== false ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                          }`}>
                          {agent.active !== false ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center space-x-2">
                        <PhoneIncoming className="h-4 w-4 text-emerald-500" />
                        <span className="capitalize">incoming</span>
                      </div>
                    </td>
                    <td className="p-4 font-mono text-slate-600">{agent.phoneNumber}</td>
                    <td className="p-4">
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={agent.active !== false}
                          onChange={(e) => handleToggleActive(agent, e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        <span className="ml-3 text-sm font-medium text-slate-700">
                          {agent.active !== false ? 'Active' : 'Inactive'}
                        </span>
                      </label>
                    </td>
                    <td className="p-4 text-slate-500">
                      {agent.updated_at ? new Date(agent.updated_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => {
                            setEditAgent(agent)
                            setAgentForm({
                              name: agent.name,
                              phoneNumber: agent.phoneNumber,
                              sttModel: agent.sttModel || 'whisper-1',
                              inferenceModel: agent.inferenceModel || 'gpt-4o-mini',
                              ttsModel: agent.ttsModel || 'tts-1',
                              ttsVoice: agent.ttsVoice || 'alloy',
                              systemPrompt: agent.systemPrompt || '',
                              greeting: agent.greeting || '',
                              temperature: agent.temperature || 0.7,
                              maxTokens: agent.maxTokens || 500,
                              active: agent.active !== false,
                            })
                            setCreateModalOpen(true)
                          }}
                          className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteAgent(agent.id)}
                          className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredAgents.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No agents found. Click "Create Agent" to add one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </LightGlassCard>
      )}

      {/* Create/Edit Agent Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="p-6 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold text-slate-900">
                    {editAgent ? 'Edit AI Agent' : 'Create New AI Agent'}
                  </h3>
                  <p className="text-sm text-slate-600 mt-1">
                    Configure your voice AI agent with custom models and behavior settings
                  </p>
                </div>
                <button
                  onClick={() => {
                    setCreateModalOpen(false)
                    setEditAgent(null)
                  }}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-slate-600" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              {/* Basic Information */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, basic: !prev.basic }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Settings className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">Basic Information</span>
                  </div>
                  {expandedSections.basic ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.basic && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Agent Name *</label>
                      <input
                        type="text"
                        value={agentForm.name}
                        onChange={(e) => setAgentForm({ ...agentForm, name: e.target.value })}
                        placeholder="e.g., gman, alexa-bot"
                        disabled={!!editAgent}
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none disabled:bg-slate-100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Phone Number *</label>
                      {editAgent ? (
                        <input
                          type="text"
                          value={agentForm.phoneNumber}
                          readOnly
                          className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-600 shadow-sm ring-1 ring-slate-200"
                        />
                      ) : (
                        <select
                          value={agentForm.phoneNumber}
                          onChange={(e) => setAgentForm({ ...agentForm, phoneNumber: e.target.value })}
                          className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                          <option value="">Select a registered phone number</option>
                          {registeredPhones.map(phone => (
                            <option key={phone.id} value={phone.phoneNumber}>{phone.phoneNumber}</option>
                          ))}
                        </select>
                      )}
                    </div>
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={agentForm.active}
                        onChange={(e) => setAgentForm({ ...agentForm, active: e.target.checked })}
                        className="h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-slate-700">Active (Enable agent to receive calls)</span>
                    </label>
                  </div>
                )}
              </div>

              {/* AI Model Configuration */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, aiModels: !prev.aiModels }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Bot className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">AI Model Configuration</span>
                  </div>
                  {expandedSections.aiModels ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.aiModels && (
                  <div className="p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">STT Model *</label>
                        <select
                          value={agentForm.sttModel}
                          onChange={(e) => setAgentForm({ ...agentForm, sttModel: e.target.value })}
                          className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                          <option value="whisper-1">whisper-1</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Inference Model *</label>
                        <select
                          value={agentForm.inferenceModel}
                          onChange={(e) => setAgentForm({ ...agentForm, inferenceModel: e.target.value })}
                          className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                          <option value="gpt-4o-mini">gpt-4o-mini (Fast, Cost-effective)</option>
                          <option value="gpt-4o">gpt-4o (More Capable)</option>
                          <option value="gpt-4o-realtime-preview-2024-12-17">gpt-4o-realtime-preview (Realtime)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">TTS Model *</label>
                        <select
                          value={agentForm.ttsModel}
                          onChange={(e) => setAgentForm({ ...agentForm, ttsModel: e.target.value })}
                          className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                          <option value="tts-1">tts-1 (Faster, Lower Latency)</option>
                          <option value="tts-1-hd">tts-1-hd (Higher Quality)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">TTS Voice *</label>
                        <select
                          value={agentForm.ttsVoice}
                          onChange={(e) => setAgentForm({ ...agentForm, ttsVoice: e.target.value })}
                          className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                          <option value="alloy">alloy</option>
                          <option value="echo">echo</option>
                          <option value="fable">fable</option>
                          <option value="onyx">onyx</option>
                          <option value="nova">nova</option>
                          <option value="shimmer">shimmer</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Behavior Configuration */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, behavior: !prev.behavior }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">Behavior Configuration</span>
                  </div>
                  {expandedSections.behavior ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.behavior && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">System Prompt *</label>
                      <textarea
                        value={agentForm.systemPrompt}
                        onChange={(e) => setAgentForm({ ...agentForm, systemPrompt: e.target.value })}
                        placeholder="You are a helpful customer support agent..."
                        rows={4}
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Greeting Message</label>
                      <input
                        type="text"
                        value={agentForm.greeting}
                        onChange={(e) => setAgentForm({ ...agentForm, greeting: e.target.value })}
                        placeholder="Welcome to customer support! How can I help you?"
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Advanced Configuration */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSections(prev => ({ ...prev, advanced: !prev.advanced }))}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-blue-600" />
                    <span className="font-bold text-slate-900">Advanced Configuration</span>
                  </div>
                  {expandedSections.advanced ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
                {expandedSections.advanced && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">
                        Temperature: {agentForm.temperature.toFixed(1)}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={agentForm.temperature}
                        onChange={(e) => setAgentForm({ ...agentForm, temperature: parseFloat(e.target.value) })}
                        className="w-full"
                      />
                      <p className="text-xs text-slate-500 mt-1">Controls response randomness (0.0 = deterministic, 2.0 = creative)</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Max Tokens</label>
                      <input
                        type="number"
                        min="1"
                        max="4000"
                        value={agentForm.maxTokens}
                        onChange={(e) => setAgentForm({ ...agentForm, maxTokens: parseInt(e.target.value) || 500 })}
                        className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                      <p className="text-xs text-slate-500 mt-1">Maximum response length (1-4000 tokens)</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="p-6 border-t border-slate-200 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setCreateModalOpen(false)
                  setEditAgent(null)
                }}
                className="px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAgent}
                className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
              >
                {editAgent ? 'Update Agent' : 'Create Agent'}
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Register Phone Modal */}
      {registerPhoneModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl shadow-2xl max-w-lg w-full"
          >
            <div className="p-6 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Phone className="h-6 w-6 text-blue-600" />
                  <div>
                    <h3 className="text-2xl font-bold text-slate-900">
                      {registrationSuccess ? 'Registration Successful!' : 'Register Phone Number'}
                    </h3>
                    <p className="text-sm text-slate-600 mt-1">
                      {registrationSuccess
                        ? 'Configure these webhooks in your Twilio Console'
                        : 'Register your Twilio phone number with credentials to use it for voice agents'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setRegisterPhoneModalOpen(false)
                    setRegistrationSuccess(null)
                  }}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-slate-600" />
                </button>
              </div>
            </div>

            {registrationSuccess ? (
              <div className="p-6 space-y-6">
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3">
                  <div className="p-2 bg-emerald-100 rounded-full shrink-0">
                    <Check className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <h4 className="font-bold text-emerald-900">Phone Number Registered</h4>
                    <p className="text-sm text-emerald-700 mt-1">
                      Your phone number has been successfully registered. Please configure the following webhooks in your Twilio Console for this number.
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">
                      A CALL COMES IN (Webhook)
                    </label>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono text-slate-600 break-all">
                        {registrationSuccess.webhookConfiguration?.incomingUrl || registrationSuccess.webhookUrl}
                      </code>
                      <button
                        onClick={() => navigator.clipboard.writeText(registrationSuccess.webhookConfiguration?.incomingUrl || registrationSuccess.webhookUrl)}
                        className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Copy URL"
                      >
                        <Copy className="h-5 w-5" />
                      </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Set this URL in Twilio Console → Phone Numbers → Manage → Active Numbers → [Your Number] → Voice & Fax → "A CALL COMES IN" (Webhook)
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">
                      CALL STATUS CHANGES (Webhook)
                    </label>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono text-slate-600 break-all">
                        {registrationSuccess.webhookConfiguration?.statusCallbackUrl || registrationSuccess.statusCallbackUrl}
                      </code>
                      <button
                        onClick={() => navigator.clipboard.writeText(registrationSuccess.webhookConfiguration?.statusCallbackUrl || registrationSuccess.statusCallbackUrl)}
                        className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Copy URL"
                      >
                        <Copy className="h-5 w-5" />
                      </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Set this URL in Twilio Console → Phone Numbers → Manage → Active Numbers → [Your Number] → Voice & Fax → "CALL STATUS CHANGES" (Webhook)
                    </p>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-200 flex justify-end">
                  <button
                    onClick={() => {
                      setRegisterPhoneModalOpen(false)
                      setRegistrationSuccess(null)
                    }}
                    className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Provider *</label>
                    <select
                      value={phoneForm.provider}
                      onChange={(e) => setPhoneForm({ ...phoneForm, provider: e.target.value })}
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      <option value="twilio">Twilio</option>
                    </select>
                    <p className="text-xs text-slate-500 mt-1">Select the phone service provider (currently only Twilio is supported)</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Phone Number *</label>
                    <input
                      type="tel"
                      value={phoneForm.phoneNumber}
                      onChange={(e) => setPhoneForm({ ...phoneForm, phoneNumber: e.target.value })}
                      placeholder="+1 555 123 4567"
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-500 mt-1">Your Twilio phone number in E.164 format</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Twilio Account SID *</label>
                    <input
                      type="text"
                      value={phoneForm.twilioAccountSid}
                      onChange={(e) => setPhoneForm({ ...phoneForm, twilioAccountSid: e.target.value })}
                      placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-mono text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-500 mt-1">Found in Twilio Console → Dashboard → Account Info</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Twilio Auth Token *</label>
                    <input
                      type="password"
                      value={phoneForm.twilioAuthToken}
                      onChange={(e) => setPhoneForm({ ...phoneForm, twilioAuthToken: e.target.value })}
                      placeholder="Enter your Twilio Auth Token"
                      className="w-full rounded-xl border-none bg-white px-4 py-3 text-sm font-mono text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-slate-500 mt-1">Found in Twilio Console → Dashboard → Account Info → Auth Token</p>
                  </div>
                </div>

                <div className="p-6 border-t border-slate-200 flex justify-end space-x-3">
                  <button
                    onClick={() => setRegisterPhoneModalOpen(false)}
                    className="px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRegisterPhone}
                    className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
                  >
                    Register Phone
                  </button>
                </div>
              </>
            )}
          </motion.div>
        </div>
      )}
    </div>
  )
}

// Prompts Management View
const PromptsView = () => {
  const [prompts, setPrompts] = useState<any[]>([])
  const [registeredPhones, setRegisteredPhones] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [editPrompt, setEditPrompt] = useState<any | null>(null)

  const [promptForm, setPromptForm] = useState({
    name: '',
    content: '',
    phoneNumberId: '',
    description: '',
    category: 'general',
  })

  // Load prompts
  const loadPrompts = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/prompts')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.prompts)) {
          setPrompts(result.prompts)
        }
      }
    } catch (error) {
      console.error('Error loading prompts:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load registered phones
  const loadRegisteredPhones = async () => {
    try {
      const response = await fetch('/api/phones')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.phones)) {
          setRegisteredPhones(result.phones.filter((p: any) => !p.isDeleted))
        }
      }
    } catch (error) {
      console.error('Error loading phones:', error)
    }
  }

  useEffect(() => {
    loadPrompts()
    loadRegisteredPhones()
  }, [])

  // Handle save prompt
  const [promptError, setPromptError] = useState<string>('')
  const handleSavePrompt = async () => {
    // Basic client‑side validation
    if (!promptForm.name.trim() || !promptForm.content.trim() || !promptForm.phoneNumberId) {
      setPromptError('Name, content, and phone number are required.')
      return
    }
    setPromptError('')
    try {
      const endpoint = editPrompt ? `/api/prompts/${editPrompt.id}` : '/api/prompts'
      const method = editPrompt ? 'PUT' : 'POST'

      const response = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(promptForm),
      })

      if (response.ok) {
        setCreateModalOpen(false)
        setEditPrompt(null)
        setPromptForm({
          name: '',
          content: '',
          phoneNumberId: '',
          description: '',
          category: 'general',
        })
        loadPrompts()
      } else {
        const err = await response.json()
        setPromptError(err.message || 'Failed to save prompt')
      }
    } catch (error) {
      console.error('Error saving prompt:', error)
      setPromptError('Unexpected error while saving prompt')
    }
  }

  // Handle delete prompt
  const handleDeletePrompt = async (promptId: string) => {
    if (confirm('Are you sure you want to delete this prompt?')) {
      try {
        const response = await fetch(`/api/prompts/${promptId}`, { method: 'DELETE' })
        if (response.ok) {
          loadPrompts()
        }
      } catch (error) {
        console.error('Error deleting prompt:', error)
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Prompts Management</h2>
          <p className="text-slate-600">Create and manage AI prompts for outgoing calls.</p>
        </div>
        <button
          onClick={() => {
            setEditPrompt(null)
            setPromptForm({
              name: '',
              content: '',
              phoneNumberId: '',
              description: '',
              category: 'general',
            })
            setCreateModalOpen(true)
          }}
          className="px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105 flex items-center space-x-2"
        >
          <Plus className="h-4 w-4" />
          <span>Create Prompt</span>
        </button>
      </div>

      {/* Prompts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {prompts.map((prompt, i) => {
          const linkedPhone = registeredPhones.find(p => p.id === prompt.phoneNumberId)
          return (
            <LightGlassCard key={prompt.id} delay={i * 0.1} className="group hover:bg-white/80 transition-all">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-slate-900 mb-1">{prompt.name}</h3>
                  {prompt.category && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                      {prompt.category}
                    </span>
                  )}
                </div>
                <div className="flex space-x-1">
                  <button
                    onClick={() => {
                      setEditPrompt(prompt)
                      setPromptForm({
                        name: prompt.name,
                        content: prompt.content,
                        phoneNumberId: prompt.phoneNumberId,
                        description: prompt.description || '',
                        category: prompt.category || 'general',
                      })
                      setCreateModalOpen(true)
                    }}
                    className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDeletePrompt(prompt.id)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {prompt.description && (
                <p className="text-sm text-slate-600 mb-3">{prompt.description}</p>
              )}

              <div className="bg-slate-50 rounded-lg p-3 mb-3 border border-slate-100">
                <p className="text-xs text-slate-700 line-clamp-3 font-mono">{prompt.content}</p>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center space-x-1">
                  <Phone className="h-3 w-3" />
                  <span className="font-mono">{linkedPhone?.phoneNumber || 'N/A'}</span>
                </div>
                <span>{prompt.created_at ? new Date(prompt.created_at).toLocaleDateString() : 'N/A'}</span>
              </div>
            </LightGlassCard>
          )
        })}

        {prompts.length === 0 && !loading && (
          <div className="col-span-full">
            <LightGlassCard className="!bg-gradient-to-b !from-slate-50 !to-white border-dashed">
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 font-medium mb-2">No prompts yet</p>
                <p className="text-sm text-slate-400">Create your first prompt to get started with AI outgoing calls.</p>
              </div>
            </LightGlassCard>
          </div>
        )}
      </div>

      {/* Create/Edit Prompt Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="p-6 border-b border-slate-200">
              <h3 className="text-xl font-bold text-slate-900">{editPrompt ? 'Edit Prompt' : 'Create New Prompt'}</h3>
              <p className="text-sm text-slate-600 mt-1">Configure your AI prompt for outgoing calls</p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Prompt Name *</label>
                <input
                  type="text"
                  value={promptForm.name}
                  onChange={(e) => setPromptForm({ ...promptForm, name: e.target.value })}
                  placeholder="e.g., Sales Follow-up Script"
                  className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Phone Number *</label>
                <select
                  value={promptForm.phoneNumberId}
                  onChange={(e) => setPromptForm({ ...promptForm, phoneNumberId: e.target.value })}
                  className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="">Select a phone number</option>
                  {registeredPhones.map(phone => (
                    <option key={phone.id} value={phone.id}>{phone.phoneNumber}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Category</label>
                <select
                  value={promptForm.category}
                  onChange={(e) => setPromptForm({ ...promptForm, category: e.target.value })}
                  className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="general">General</option>
                  <option value="sales">Sales</option>
                  <option value="support">Support</option>
                  <option value="reminder">Reminder</option>
                  <option value="survey">Survey</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Description</label>
                <input
                  type="text"
                  value={promptForm.description}
                  onChange={(e) => setPromptForm({ ...promptForm, description: e.target.value })}
                  placeholder="Brief description of this prompt"
                  className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Prompt Content *</label>
                <textarea
                  value={promptForm.content}
                  onChange={(e) => setPromptForm({ ...promptForm, content: e.target.value })}
                  placeholder="Enter the AI prompt/script that will be used during the call..."
                  rows={8}
                  className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-mono text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                />
                <p className="text-xs text-slate-500 mt-1">This is the instruction that the AI will follow during the call.</p>
              </div>
            </div>

            <div className="p-6 border-t border-slate-200 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setCreateModalOpen(false)
                  setPromptError('')
                }}
                className="px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSavePrompt}
                className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
              >
                {editPrompt ? 'Update Prompt' : 'Create Prompt'}
              </button>
              {promptError && (
                <p className="mt-2 text-sm text-red-600">{promptError}</p>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}

// Outgoing Agent View
const OutgoingAgentView = () => {
  const [scheduledCalls, setScheduledCalls] = useState<any[]>([])
  const [prompts, setPrompts] = useState<any[]>([])
  const [registeredPhones, setRegisteredPhones] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false)

  const [callForm, setCallForm] = useState({
    callType: 'ai',
    fromPhoneNumberId: '',
    toPhoneNumbers: [''],
    scheduledDateTime: '',
    promptId: '',
  })

  // Load scheduled calls
  const loadScheduledCalls = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/scheduled-calls')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.calls)) {
          setScheduledCalls(result.calls)
        }
      }
    } catch (error) {
      console.error('Error loading scheduled calls:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load prompts
  const loadPrompts = async () => {
    try {
      const response = await fetch('/api/prompts')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.prompts)) {
          setPrompts(result.prompts)
        }
      }
    } catch (error) {
      console.error('Error loading prompts:', error)
    }
  }

  // Load registered phones
  const loadRegisteredPhones = async () => {
    try {
      const response = await fetch('/api/phones')
      if (response.ok) {
        const result = await response.json()
        if (result.success && Array.isArray(result.phones)) {
          setRegisteredPhones(result.phones.filter((p: any) => !p.isDeleted))
        }
      }
    } catch (error) {
      console.error('Error loading phones:', error)
    }
  }

  useEffect(() => {
    loadScheduledCalls()
    loadPrompts()
    loadRegisteredPhones()
  }, [])

  // Handle schedule call
  const [scheduleError, setScheduleError] = useState<string>('')
  const handleScheduleCall = async () => {
    // Basic validation for required fields
    if (!callForm.fromPhoneNumberId) {
      setScheduleError('Select a "From" phone number.')
      return
    }
    if (callForm.toPhoneNumbers.filter(n => n.trim() !== '').length === 0) {
      setScheduleError('Add at least one "To" phone number.')
      return
    }
    if (!callForm.scheduledDateTime) {
      setScheduleError('Select a scheduled date and time.')
      return
    }
    if (callForm.callType === 'ai' && !callForm.promptId) {
      setScheduleError('Select an AI prompt for the call.')
      return
    }
    setScheduleError('')
    try {
      const response = await fetch('/api/scheduled-calls', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...callForm,
          toPhoneNumbers: callForm.toPhoneNumbers.filter(n => n.trim() !== ''),
        }),
      })

      if (response.ok) {
        setScheduleModalOpen(false)
        setCallForm({
          callType: 'ai',
          fromPhoneNumberId: '',
          toPhoneNumbers: [''],
          scheduledDateTime: '',
          promptId: '',
        })
        loadScheduledCalls()
      } else {
        const err = await response.json()
        setScheduleError(err.message || 'Failed to schedule call')
      }
    } catch (error) {
      console.error('Error scheduling call:', error)
      setScheduleError('Unexpected error while scheduling call')
    }
  }

  // Handle delete scheduled call
  const handleDeleteScheduledCall = async (callId: string) => {
    if (confirm('Are you sure you want to delete this scheduled call?')) {
      try {
        const response = await fetch(`/api/scheduled-calls/${callId}`, { method: 'DELETE' })
        if (response.ok) {
          loadScheduledCalls()
        }
      } catch (error) {
        console.error('Error deleting scheduled call:', error)
      }
    }
  }

  const addPhoneNumberField = () => {
    setCallForm({ ...callForm, toPhoneNumbers: [...callForm.toPhoneNumbers, ''] })
  }

  const removePhoneNumberField = (index: number) => {
    const newNumbers = callForm.toPhoneNumbers.filter((_, i) => i !== index)
    setCallForm({ ...callForm, toPhoneNumbers: newNumbers.length > 0 ? newNumbers : [''] })
  }

  const updatePhoneNumber = (index: number, value: string) => {
    const newNumbers = [...callForm.toPhoneNumbers]
    newNumbers[index] = value
    setCallForm({ ...callForm, toPhoneNumbers: newNumbers })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Outgoing Agent</h2>
          <p className="text-slate-600">Schedule AI or normal outgoing calls to single or multiple numbers.</p>
        </div>
        <button
          onClick={() => {
            setCallForm({
              callType: 'ai',
              fromPhoneNumberId: '',
              toPhoneNumbers: [''],
              scheduledDateTime: '',
              promptId: '',
            })
            setScheduleModalOpen(true)
          }}
          className="px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105 flex items-center space-x-2"
        >
          <Calendar className="h-4 w-4" />
          <span>Schedule Call</span>
        </button>
      </div>

      {/* Scheduled Calls Table */}
      <LightGlassCard className="!p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th className="p-4">Type</th>
                <th className="p-4">From</th>
                <th className="p-4">To</th>
                <th className="p-4">Scheduled Time</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm text-slate-700 font-medium divide-y divide-slate-100">
              {scheduledCalls.map((call, i) => {
                const fromPhone = registeredPhones.find(p => p.id === call.fromPhoneNumberId)
                return (
                  <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold capitalize ${call.callType === 'ai' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-700'
                        }`}>
                        {call.callType}
                      </span>
                    </td>
                    <td className="p-4 font-mono">{fromPhone?.phoneNumber || 'N/A'}</td>
                    <td className="p-4">
                      <div className="flex flex-col gap-1">
                        {call.toPhoneNumbers?.slice(0, 2).map((num: string, idx: number) => (
                          <span key={idx} className="font-mono text-xs">{num}</span>
                        ))}
                        {call.toPhoneNumbers?.length > 2 && (
                          <span className="text-xs text-slate-500">+{call.toPhoneNumbers.length - 2} more</span>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      {call.scheduledDateTime ? new Date(call.scheduledDateTime).toLocaleString() : 'N/A'}
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold capitalize ${call.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                        call.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                          call.status === 'failed' ? 'bg-red-100 text-red-700' :
                            'bg-slate-100 text-slate-700'
                        }`}>
                        {call.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleDeleteScheduledCall(call.id)}
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
              {scheduledCalls.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500">
                    No scheduled calls yet. Click "Schedule Call" to create one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </LightGlassCard>

      {/* Schedule Call Modal */}
      {scheduleModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="p-6 border-b border-slate-200">
              <h3 className="text-xl font-bold text-slate-900">Schedule Outgoing Call</h3>
              <p className="text-sm text-slate-600 mt-1">Configure your outgoing call settings</p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Call Type *</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setCallForm({ ...callForm, callType: 'ai' })}
                    className={`p-4 rounded-xl border-2 transition-all ${callForm.callType === 'ai'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                      }`}
                  >
                    <Bot className="h-6 w-6 mx-auto mb-2" />
                    <p className="font-bold text-sm">AI Call</p>
                    <p className="text-xs opacity-70">Use AI prompt</p>
                  </button>
                  <button
                    onClick={() => setCallForm({ ...callForm, callType: 'normal' })}
                    className={`p-4 rounded-xl border-2 transition-all ${callForm.callType === 'normal'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                      }`}
                  >
                    <Phone className="h-6 w-6 mx-auto mb-2" />
                    <p className="font-bold text-sm">Normal Call</p>
                    <p className="text-xs opacity-70">Standard call</p>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">From Phone Number *</label>
                <select
                  value={callForm.fromPhoneNumberId}
                  onChange={(e) => setCallForm({ ...callForm, fromPhoneNumberId: e.target.value })}
                  className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="">Select a phone number</option>
                  {registeredPhones.map(phone => (
                    <option key={phone.id} value={phone.id}>{phone.phoneNumber}</option>
                  ))}
                </select>
              </div>

              {callForm.callType === 'ai' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">AI Prompt *</label>
                  <select
                    value={callForm.promptId}
                    onChange={(e) => setCallForm({ ...callForm, promptId: e.target.value })}
                    className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="">Select a prompt</option>
                    {prompts.filter(p => p.phoneNumberId === callForm.fromPhoneNumberId).map(prompt => (
                      <option key={prompt.id} value={prompt.id}>{prompt.name}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">To Phone Numbers *</label>
                <div className="space-y-2">
                  {callForm.toPhoneNumbers.map((number, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={number}
                        onChange={(e) => updatePhoneNumber(index, e.target.value)}
                        placeholder="+1 (555) 123-4567"
                        className="flex-1 rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-mono text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                      {callForm.toPhoneNumbers.length > 1 && (
                        <button
                          onClick={() => removePhoneNumberField(index)}
                          className="p-3 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={addPhoneNumberField}
                    className="w-full py-2 rounded-lg border-2 border-dashed border-slate-300 text-slate-600 text-sm font-medium hover:border-blue-400 hover:text-blue-600 transition-colors flex items-center justify-center space-x-2"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Add Another Number</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Scheduled Date & Time *</label>
                <input
                  type="datetime-local"
                  value={callForm.scheduledDateTime}
                  onChange={(e) => setCallForm({ ...callForm, scheduledDateTime: e.target.value })}
                  className="w-full rounded-xl border-none bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>

            <div className="p-6 border-t border-slate-200 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setScheduleModalOpen(false)
                  setScheduleError('')
                }}
                className="px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleScheduleCall}
                className="px-6 py-3 rounded-xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all hover:scale-105"
              >
                Schedule Call
              </button>
              {scheduleError && (
                <p className="mt-2 text-sm text-red-600">{scheduleError}</p>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}

export default function FuturisticDemo() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    setIsLoaded(true)
  }, [])

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Ambient Background Effects */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[20%] -left-[10%] h-[800px] w-[800px] rounded-full bg-blue-200/20 blur-[120px]" />
        <div className="absolute top-[20%] right-[0%] h-[600px] w-[600px] rounded-full bg-purple-200/20 blur-[120px]" />
        <div className="absolute bottom-0 left-1/3 h-[500px] w-[500px] rounded-full bg-emerald-100/30 blur-[100px]" />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-30 mix-blend-overlay"></div>
      </div>

      <div className="relative z-10 flex h-screen overflow-hidden">
        {/* Sidebar */}
        <motion.aside
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="w-72 border-r border-slate-200/60 bg-white/50 backdrop-blur-2xl flex flex-col z-20"
        >
          <div className="p-6 flex items-center space-x-3">
            <div className="relative h-10 w-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20">
              <Radio className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-800 tracking-tight">DoDash<span className="text-blue-600">.AI</span></h1>
              <p className="text-[10px] text-slate-500 font-bold tracking-widest uppercase">Voice Intelligence</p>
            </div>
          </div>

          <nav className="flex-1 px-4 space-y-1 mt-6 overflow-y-auto">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider px-4 mb-3">Platform</div>
            <NavItem icon={BarChart3} label="Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />


            <NavItem icon={PhoneIncoming} label="Incoming Agent" active={activeTab === 'incoming-agent'} onClick={() => setActiveTab('incoming-agent')} />
            <NavItem icon={PhoneOutgoing} label="Outgoing Agent" active={activeTab === 'outgoing-agent'} onClick={() => setActiveTab('outgoing-agent')} />
            <NavItem icon={FileText} label="Prompts" active={activeTab === 'prompts'} onClick={() => setActiveTab('prompts')} />
            <NavItem icon={MessageSquare} label="Messaging Agents" active={activeTab === 'messaging-agents'} onClick={() => setActiveTab('messaging-agents')} />
            <NavItem icon={MessageSquare} label="Messages" active={activeTab === 'messages'} onClick={() => setActiveTab('messages')} />
            <NavItem icon={History} label="Call Logs" active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} />
            <NavItem icon={Volume2} label="Voice Customization" active={activeTab === 'voices'} onClick={() => setActiveTab('voices')} />

            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider px-4 mb-3 mt-8">System</div>
            <NavItem icon={Globe} label="Endpoints" active={activeTab === 'endpoints'} onClick={() => setActiveTab('endpoints')} />
            <NavItem icon={FileText} label="Activity Logs" active={activeTab === 'activity'} onClick={() => setActiveTab('activity')} />
            <NavItem icon={Settings} label="Settings" active={activeTab === 'settings'} onClick={() => setActiveTab('settings')} />
          </nav>

          <div className="p-4">
            <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 p-4 text-white shadow-xl shadow-slate-900/10">
              <div className="flex items-center space-x-3 mb-3">
                <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                <span className="text-xs font-bold tracking-wide">SYSTEM OPERATIONAL</span>
              </div>
              <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                <div className="h-full w-3/4 bg-gradient-to-r from-emerald-400 to-blue-400 rounded-full" />
              </div>
            </div>
          </div>
        </motion.aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto scrollbar-hide relative">
          <div className="max-w-7xl mx-auto p-8">

            {/* Header */}
            <header className="flex items-center justify-between mb-10">
              <div>
                <motion.h2
                  key={activeTab}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-3xl font-black text-slate-800 tracking-tight capitalize"
                >
                  {activeTab === 'dashboard' ? 'Dashboard' :

                    activeTab === 'incoming-agent' ? 'Incoming Agent' :
                      activeTab === 'outgoing-agent' ? 'Outgoing Agent' :
                        activeTab === 'prompts' ? 'Prompts Management' :
                          activeTab === 'messaging-agents' ? 'Messaging Agents' :
                            activeTab === 'messages' ? 'Messages & SMS' :
                              activeTab === 'logs' ? 'Call History' :
                                activeTab === 'voices' ? 'Voice Customization' :
                                  activeTab === 'endpoints' ? 'Endpoints & Webhooks' :
                                    activeTab === 'activity' ? 'Activity Logs' :
                                      activeTab === 'settings' ? 'Settings' :
                                        'Command Center'}
                </motion.h2>
                <p className="text-slate-500 mt-1 font-medium">
                  {activeTab === 'dialer' ? 'Make calls and manage active connections.' :

                    activeTab === 'incoming-agent' ? 'Create and manage Voice Agents for your Business.' :
                      activeTab === 'outgoing-agent' ? 'Schedule AI or normal outgoing calls to single or multiple numbers.' :
                        activeTab === 'prompts' ? 'Create and manage AI prompts for outgoing calls.' :
                          activeTab === 'messaging-agents' ? 'Create and manage SMS/Messaging Agents for your Business.' :
                            activeTab === 'messages' ? 'View and send SMS messages to customers.' :
                              activeTab === 'logs' ? 'Review past call performance and recordings.' :
                                activeTab === 'voices' ? 'Preview and customize TTS voices for your agents.' :
                                  activeTab === 'endpoints' ? 'Manage webhook URLs and API endpoints.' :
                                    activeTab === 'activity' ? 'Monitor system events and activity history.' :
                                      activeTab === 'settings' ? 'Configure your account and system preferences.' :
                                        "Good afternoon, Teja. Here's what's happening today."}
                </p>
              </div>

              <div className="flex items-center space-x-4">
                <button className="h-10 w-10 rounded-full bg-white flex items-center justify-center shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 transition-colors relative">
                  <Bell className="h-5 w-5 text-slate-600" />
                  <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />
                </button>
                <button className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30 transition-transform hover:scale-105">
                  <Zap className="h-5 w-5 text-white" />
                </button>
              </div>
            </header>

            {/* Content Area */}
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              {activeTab === 'dashboard' && <DashboardView />}


              {activeTab === 'incoming-agent' && <IncomingAgentView />}
              {activeTab === 'outgoing-agent' && <OutgoingAgentView />}
              {activeTab === 'prompts' && <PromptsView />}
              {activeTab === 'messaging-agents' && <MessagingAgentsView />}
              {activeTab === 'messages' && <MessagesView />}
              {activeTab === 'logs' && <LogsView />}
              {activeTab === 'voices' && <VoiceCustomizationView />}
              {activeTab === 'endpoints' && <EndpointsView />}
              {activeTab === 'activity' && <ActivityLogsView />}
              {activeTab === 'settings' && <SettingsView />}
            </motion.div>

          </div>
        </main>
      </div>
    </div>
  )
}



