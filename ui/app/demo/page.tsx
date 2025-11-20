'use client'

import { useState, useEffect, useRef } from 'react'
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
  PhoneMissed,
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
  CheckCircle2,
  Filter,
  Edit,
  Trash2,
  Plus,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle
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

const DashboardView = () => (
  <div className="space-y-8">
    {/* Stats Grid */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard icon={Phone} label="Total Calls" value="2,543" trend="+12.5%" color="from-blue-500 to-cyan-500" delay={0.1} />
      <StatCard icon={Clock} label="Avg. Duration" value="4m 12s" trend="+5.2%" color="from-violet-500 to-fuchsia-500" delay={0.2} />
      <StatCard icon={Zap} label="Active Agents" value="14" trend="+2" color="from-emerald-500 to-teal-500" delay={0.3} />
      <StatCard icon={DollarSign} label="Cost / Min" value="$0.04" trend="-8.1%" color="from-orange-500 to-red-500" delay={0.4} />
    </div>

    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Live Activity Feed */}
      <div className="lg:col-span-2 space-y-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold text-slate-800">Active Agents</h3>
          <button className="text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors">View All</button>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="space-y-4">
          {[
            { name: "Support Bot Alpha", status: "active", type: "Inbound Support", calls: "1,234", performance: "98%" },
            { name: "Sales Outreach X", status: "active", type: "Outbound Sales", calls: "856", performance: "92%" },
            { name: "Appointment Setter", status: "idle", type: "Scheduling", calls: "445", performance: "88%" }
          ].map((agent, i) => (
            <div key={i} className="group flex items-center justify-between rounded-xl border border-slate-100 bg-white/50 p-4 transition-all hover:bg-white hover:shadow-md hover:shadow-slate-200/50 hover:border-white">
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 p-[2px]">
                    <div className="h-full w-full rounded-full bg-white flex items-center justify-center">
                      <Cpu className="h-6 w-6 text-blue-600" />
                    </div>
                  </div>
                  <div className={`absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white ${agent.status === 'active' ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                </div>
                <div>
                  <h4 className="font-bold text-slate-800 group-hover:text-blue-600 transition-colors">{agent.name}</h4>
                  <p className="text-xs text-slate-500 font-medium">{agent.type}</p>
                </div>
              </div>
              <div className="flex items-center space-x-8">
                <div className="text-center hidden sm:block">
                  <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">Calls</p>
                  <p className="font-mono text-sm font-bold text-slate-700">{agent.calls}</p>
                </div>
                <div className="text-center hidden sm:block">
                  <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">Performance</p>
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-16 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-blue-400 to-purple-500" style={{ width: agent.performance }} />
                    </div>
                    <span className="text-xs font-bold text-slate-700">{agent.performance}</span>
                  </div>
                </div>
                <button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors">
                  <MoreHorizontal className="h-5 w-5" />
                </button>
              </div>
            </div>
          ))}
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
            {[
              { label: "API Latency", value: "45ms", color: "bg-emerald-500", width: "20%" },
              { label: "Voice Synthesis", value: "120ms", color: "bg-blue-500", width: "35%" },
              { label: "Database Load", value: "12%", color: "bg-purple-500", width: "12%" }
            ].map((item, i) => (
              <div key={i}>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-500 font-medium">{item.label}</span>
                  <span className={`font-bold ${item.color.replace('bg-', 'text-').replace('500', '600')}`}>{item.value}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full ${item.color} rounded-full shadow-sm`} style={{ width: item.width }} />
                </div>
              </div>
            ))}
          </div>
        </LightGlassCard>

        <LightGlassCard delay={0.7}>
          <h3 className="text-lg font-bold text-slate-800 mb-4">Recent Events</h3>
          <div className="space-y-0">
            {[1, 2, 3].map((_, i) => (
              <div key={i} className="flex items-start space-x-3 py-4 border-b border-slate-100 last:border-0 last:pb-0 first:pt-0">
                <div className="mt-1.5 h-2 w-2 rounded-full bg-blue-500 ring-4 ring-blue-50" />
                <div>
                  <p className="text-sm font-semibold text-slate-700">New agent "Sales Bot" created</p>
                  <p className="text-xs text-slate-400 mt-0.5">2 minutes ago by Admin</p>
                </div>
              </div>
            ))}
          </div>
        </LightGlassCard>
      </div>
    </div>
  </div>
)

const DialerView = () => {
  const [activeCall, setActiveCall] = useState<boolean>(false)
  const [dialNumber, setDialNumber] = useState("")
  const [callDuration, setCallDuration] = useState(0)

  useEffect(() => {
    let interval: any;
    if (activeCall) {
      interval = setInterval(() => setCallDuration(prev => prev + 1), 1000)
    } else {
      setCallDuration(0)
    }
    return () => clearInterval(interval)
  }, [activeCall])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-140px)]">
      {/* Dialer / Active Call Panel */}
      <div className="flex flex-col">
        <LightGlassCard className="flex-1 flex flex-col items-center justify-center relative overflow-hidden !p-0">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 to-purple-50/50 z-0" />

          <AnimatePresence mode="wait">
            {!activeCall ? (
              <motion.div
                key="keypad"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="relative z-10 w-full max-w-xs flex flex-col items-center"
              >
                <input
                  type="text"
                  value={dialNumber}
                  readOnly
                  className="w-full text-center text-4xl font-light text-slate-800 bg-transparent border-none outline-none mb-8 placeholder:text-slate-300"
                  placeholder="+1 (555)..."
                />
                <div className="grid grid-cols-3 gap-6 mb-8">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, '*', 0, '#'].map((key) => (
                    <button
                      key={key}
                      onClick={() => setDialNumber(prev => prev + key)}
                      className="h-16 w-16 rounded-full bg-white shadow-sm border border-slate-100 text-2xl font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all active:scale-95 flex items-center justify-center"
                    >
                      {key}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => setActiveCall(true)}
                  disabled={dialNumber.length < 3}
                  className="h-16 w-16 rounded-full bg-emerald-500 text-white shadow-lg shadow-emerald-500/30 flex items-center justify-center hover:bg-emerald-600 hover:scale-105 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Phone className="h-8 w-8" />
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="active-call"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="relative z-10 w-full flex flex-col items-center"
              >
                <div className="h-32 w-32 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 p-1 mb-6 relative">
                  <div className="h-full w-full rounded-full bg-white flex items-center justify-center overflow-hidden">
                    <User className="h-16 w-16 text-slate-300" />
                  </div>
                  <span className="absolute bottom-2 right-2 h-4 w-4 rounded-full bg-emerald-500 border-2 border-white animate-pulse" />
                </div>
                <h3 className="text-2xl font-bold text-slate-800 mb-1">{dialNumber || "Unknown Caller"}</h3>
                <p className="text-blue-600 font-medium mb-8">{formatTime(callDuration)}</p>

                {/* Audio Waveform Simulation */}
                <div className="flex items-center space-x-1 h-12 mb-12">
                  {[...Array(20)].map((_, i) => (
                    <motion.div
                      key={i}
                      animate={{ height: [10, Math.random() * 40 + 10, 10] }}
                      transition={{ repeat: Infinity, duration: 1, delay: i * 0.05 }}
                      className="w-1.5 bg-blue-400 rounded-full opacity-60"
                    />
                  ))}
                </div>

                <div className="flex items-center space-x-6">
                  <button className="h-14 w-14 rounded-full bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 flex items-center justify-center transition-colors">
                    <Mic className="h-6 w-6" />
                  </button>
                  <button
                    onClick={() => setActiveCall(false)}
                    className="h-16 w-16 rounded-full bg-red-500 text-white shadow-lg shadow-red-500/30 flex items-center justify-center hover:bg-red-600 hover:scale-105 transition-all"
                  >
                    <PhoneMissed className="h-8 w-8" />
                  </button>
                  <button className="h-14 w-14 rounded-full bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 flex items-center justify-center transition-colors">
                    <MoreHorizontal className="h-6 w-6" />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </LightGlassCard>
      </div>

      {/* Recent Calls List */}
      <div className="flex flex-col space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-slate-800">Recent Activity</h3>
          <div className="flex space-x-2">
            <button className="px-3 py-1.5 rounded-lg bg-white text-xs font-bold text-slate-600 shadow-sm border border-slate-200">All</button>
            <button className="px-3 py-1.5 rounded-lg hover:bg-white/50 text-xs font-medium text-slate-500 transition-colors">Missed</button>
          </div>
        </div>

        <div className="space-y-3 overflow-y-auto pr-2">
          {[
            { name: "John Doe", number: "+1 (555) 123-4567", type: "incoming", time: "2 mins ago", duration: "5m 23s", status: "completed" },
            { name: "Sarah Smith", number: "+1 (555) 987-6543", type: "outgoing", time: "1 hour ago", duration: "12m 05s", status: "completed" },
            { name: "Unknown", number: "+1 (555) 000-0000", type: "missed", time: "3 hours ago", duration: "0s", status: "missed" },
            { name: "Support Line", number: "+1 (800) 123-4567", type: "outgoing", time: "Yesterday", duration: "24m 10s", status: "completed" },
          ].map((call, i) => (
            <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/60 border border-white/60 hover:bg-white hover:shadow-sm transition-all">
              <div className="flex items-center space-x-4">
                <div className={`h-10 w-10 rounded-full flex items-center justify-center ${call.type === 'missed' ? 'bg-red-100 text-red-600' :
                  call.type === 'incoming' ? 'bg-blue-100 text-blue-600' : 'bg-emerald-100 text-emerald-600'
                  }`}>
                  {call.type === 'missed' ? <PhoneMissed className="h-5 w-5" /> :
                    call.type === 'incoming' ? <PhoneIncoming className="h-5 w-5" /> : <PhoneOutgoing className="h-5 w-5" />}
                </div>
                <div>
                  <h4 className="font-bold text-slate-800 text-sm">{call.name}</h4>
                  <p className="text-xs text-slate-500">{call.number}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs font-bold text-slate-700">{call.time}</p>
                <p className="text-xs text-slate-400">{call.duration}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const AgentsView = () => {
  const [selectedAgent, setSelectedAgent] = useState<number | null>(null)
  const [messages, setMessages] = useState([
    { role: 'agent', text: "Hello! I'm your sales assistant. How can I help you today?" }
  ])
  const [inputText, setInputText] = useState("")

  const handleSendMessage = () => {
    if (!inputText.trim()) return
    setMessages(prev => [...prev, { role: 'user', text: inputText }])
    setInputText("")
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'agent', text: "I can certainly help with that. Let me pull up the details for you." }])
    }, 1000)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[calc(100vh-140px)]">
      {/* Agents List */}
      <div className="space-y-4 lg:col-span-1 overflow-y-auto pr-2">
        {[
          { id: 1, name: "Support Bot Alpha", role: "Customer Service", status: "active" },
          { id: 2, name: "Sales Outreach X", role: "Outbound Sales", status: "active" },
          { id: 3, name: "Appointment Setter", role: "Scheduling", status: "idle" },
          { id: 4, name: "Tech Support V2", role: "Technical", status: "offline" },
        ].map((agent) => (
          <div
            key={agent.id}
            onClick={() => setSelectedAgent(agent.id)}
            className={`cursor-pointer p-4 rounded-xl border transition-all ${selectedAgent === agent.id
              ? 'bg-white border-blue-200 shadow-md shadow-blue-500/10 ring-1 ring-blue-500'
              : 'bg-white/40 border-white/60 hover:bg-white/80'
              }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold">
                  {agent.name[0]}
                </div>
                <div>
                  <h4 className="font-bold text-slate-800 text-sm">{agent.name}</h4>
                  <p className="text-xs text-slate-500">{agent.role}</p>
                </div>
              </div>
              <div className={`h-2.5 w-2.5 rounded-full ${agent.status === 'active' ? 'bg-emerald-500' :
                agent.status === 'idle' ? 'bg-amber-500' : 'bg-slate-300'
                }`} />
            </div>
          </div>
        ))}
        <button className="w-full py-3 rounded-xl border-2 border-dashed border-slate-300 text-slate-500 font-bold text-sm hover:border-blue-400 hover:text-blue-600 transition-colors flex items-center justify-center space-x-2">
          <span>+ Create New Agent</span>
        </button>
      </div>

      {/* Chat / Config Panel */}
      <div className="lg:col-span-2 flex flex-col h-full">
        <LightGlassCard className="flex-1 flex flex-col !p-0 overflow-hidden">
          {selectedAgent ? (
            <>
              {/* Chat Header */}
              <div className="p-4 border-b border-slate-100 bg-white/50 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <Bot className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-800 text-sm">Test Conversation</h3>
                    <p className="text-xs text-slate-500">Simulating voice interaction via text</p>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button className="p-2 hover:bg-slate-100 rounded-lg text-slate-500"><Settings className="h-4 w-4" /></button>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] p-4 rounded-2xl text-sm font-medium ${msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none shadow-lg shadow-blue-500/20'
                      : 'bg-white text-slate-700 rounded-bl-none shadow-sm border border-slate-100'
                      }`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>

              {/* Input Area */}
              <div className="p-4 bg-white border-t border-slate-100">
                <div className="flex items-center space-x-2 bg-slate-50 rounded-xl p-2 border border-slate-200 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
                  <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors"><Mic className="h-5 w-5" /></button>
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                    placeholder="Type a message to test the agent..."
                    className="flex-1 bg-transparent border-none outline-none text-sm font-medium text-slate-700 placeholder:text-slate-400"
                  />
                  <button
                    onClick={handleSendMessage}
                    className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md shadow-blue-500/20"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
              <Bot className="h-16 w-16 mb-4 opacity-20" />
              <p className="font-medium">Select an agent to configure or test</p>
            </div>
          )}
        </LightGlassCard>
      </div>
    </div>
  )
}

const LogsView = () => (
  <div className="space-y-6">
    <div className="flex items-center justify-between">
      <h2 className="text-2xl font-bold text-slate-800">Call Logs</h2>
      <div className="flex space-x-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search logs..."
            className="h-10 w-64 rounded-xl border-none bg-white pl-10 pr-4 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <button className="h-10 px-4 rounded-xl bg-white text-slate-600 text-sm font-bold shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 flex items-center space-x-2">
          <Calendar className="h-4 w-4" />
          <span>Date Range</span>
        </button>
        <button className="h-10 px-4 rounded-xl bg-blue-600 text-white text-sm font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 flex items-center space-x-2">
          <span>Export CSV</span>
        </button>
      </div>
    </div>

    <LightGlassCard className="!p-0 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/50 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
              <th className="p-4">Status</th>
              <th className="p-4">Direction</th>
              <th className="p-4">From / To</th>
              <th className="p-4">Agent</th>
              <th className="p-4">Duration</th>
              <th className="p-4">Date & Time</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="text-sm text-slate-700 font-medium divide-y divide-slate-100">
            {[
              { status: "completed", direction: "inbound", from: "+1 (555) 123-4567", agent: "Support Bot Alpha", duration: "5m 23s", date: "Oct 24, 2:30 PM" },
              { status: "missed", direction: "inbound", from: "+1 (555) 987-6543", agent: "-", duration: "0s", date: "Oct 24, 1:15 PM" },
              { status: "completed", direction: "outbound", from: "+1 (555) 444-3333", agent: "Sales Outreach X", duration: "12m 05s", date: "Oct 24, 11:00 AM" },
              { status: "voicemail", direction: "inbound", from: "+1 (555) 222-1111", agent: "Support Bot Alpha", duration: "1m 45s", date: "Oct 23, 4:45 PM" },
              { status: "completed", direction: "outbound", from: "+1 (555) 666-7777", agent: "Appointment Setter", duration: "3m 10s", date: "Oct 23, 2:20 PM" },
            ].map((log, i) => (
              <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                <td className="p-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold capitalize ${log.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                    log.status === 'missed' ? 'bg-red-100 text-red-700' :
                      'bg-amber-100 text-amber-700'
                    }`}>
                    {log.status}
                  </span>
                </td>
                <td className="p-4">
                  <div className="flex items-center space-x-2">
                    {log.direction === 'inbound' ? <PhoneIncoming className="h-4 w-4 text-blue-500" /> : <PhoneOutgoing className="h-4 w-4 text-purple-500" />}
                    <span className="capitalize">{log.direction}</span>
                  </div>
                </td>
                <td className="p-4 font-mono text-slate-600">{log.from}</td>
                <td className="p-4">{log.agent}</td>
                <td className="p-4">{log.duration}</td>
                <td className="p-4 text-slate-500">{log.date}</td>
                <td className="p-4 text-right">
                  <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                    <Play className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="p-4 border-t border-slate-200/60 flex items-center justify-between text-xs text-slate-500 font-medium">
        <span>Showing 1-5 of 2,453 logs</span>
        <div className="flex space-x-2">
          <button className="px-3 py-1 rounded-lg border border-slate-200 hover:bg-slate-50">Previous</button>
          <button className="px-3 py-1 rounded-lg border border-slate-200 hover:bg-slate-50">Next</button>
        </div>
      </div>
    </LightGlassCard>
  </div>
)

const MessagesView = () => {
  const [selectedPhone, setSelectedPhone] = useState('+1 (555) 123-4567')
  const [messageText, setMessageText] = useState('')

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[calc(100vh-140px)]">
      {/* Phone Numbers List */}
      <div className="space-y-4 overflow-y-auto pr-2">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-800">Conversations</h3>
          <button className="p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors">
            <Send className="h-4 w-4" />
          </button>
        </div>
        {[
          { phone: '+1 (555) 123-4567', name: 'John Doe', lastMsg: 'Thanks for the information!', time: '2m ago', unread: 2 },
          { phone: '+1 (555) 987-6543', name: 'Sarah Smith', lastMsg: 'When can we schedule a call?', time: '1h ago', unread: 0 },
          { phone: '+1 (555) 444-3333', name: 'Mike Johnson', lastMsg: 'Perfect, see you then', time: '3h ago', unread: 0 },
        ].map((contact, i) => (
          <div
            key={i}
            onClick={() => setSelectedPhone(contact.phone)}
            className={`cursor-pointer p-4 rounded-xl border transition-all ${selectedPhone === contact.phone
              ? 'bg-white border-blue-200 shadow-md shadow-blue-500/10 ring-1 ring-blue-500'
              : 'bg-white/40 border-white/60 hover:bg-white/80'
              }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-3">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold">
                  {contact.name[0]}
                </div>
                <div>
                  <h4 className="font-bold text-slate-800 text-sm">{contact.name}</h4>
                  <p className="text-xs text-slate-500 font-mono">{contact.phone}</p>
                </div>
              </div>
              {contact.unread > 0 && (
                <span className="h-5 w-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                  {contact.unread}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 truncate">{contact.lastMsg}</p>
            <p className="text-xs text-slate-400 mt-1">{contact.time}</p>
          </div>
        ))}
      </div>

      {/* Message Thread */}
      <div className="lg:col-span-2 flex flex-col">
        <LightGlassCard className="flex-1 flex flex-col !p-0 overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-slate-100 bg-white/50 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                <MessageSquare className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-sm">{selectedPhone}</h3>
                <p className="text-xs text-slate-500">SMS Conversation</p>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
            {[
              { role: 'received', text: 'Hi! I have a question about your services.', time: '10:30 AM' },
              { role: 'sent', text: 'Hello! I\'d be happy to help. What would you like to know?', time: '10:31 AM' },
              { role: 'received', text: 'Can you tell me about pricing and availability?', time: '10:32 AM' },
              { role: 'sent', text: 'Of course! Our plans start at $29/month. We have immediate availability. Would you like to schedule a demo?', time: '10:33 AM' },
              { role: 'received', text: 'Thanks for the information!', time: '10:35 AM' },
            ].map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'sent' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%]`}>
                  <div className={`p-4 rounded-2xl text-sm font-medium ${msg.role === 'sent'
                    ? 'bg-blue-600 text-white rounded-br-none shadow-lg shadow-blue-500/20'
                    : 'bg-white text-slate-700 rounded-bl-none shadow-sm border border-slate-100'
                    }`}>
                    {msg.text}
                  </div>
                  <p className="text-xs text-slate-400 mt-1 px-2">{msg.time}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Input Area */}
          <div className="p-4 bg-white border-t border-slate-100">
            <div className="flex items-center space-x-2 bg-slate-50 rounded-xl p-2 border border-slate-200 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
              <input
                type="text"
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                placeholder="Type a message..."
                className="flex-1 bg-transparent border-none outline-none text-sm font-medium text-slate-700 placeholder:text-slate-400"
              />
              <span className="text-xs text-slate-400">{messageText.length}/160</span>
              <button
                onClick={() => setMessageText('')}
                className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md shadow-blue-500/20"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </LightGlassCard>
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

  const endpoints = [
    {
      name: 'Voice Call Webhook',
      url: 'https://api.dodash.ai/webhooks/voice/incoming',
      status: 'active',
      description: 'Receives incoming call events from Twilio'
    },
    {
      name: 'SMS Webhook',
      url: 'https://api.dodash.ai/webhooks/sms/incoming',
      status: 'active',
      description: 'Receives incoming SMS messages'
    },
    {
      name: 'Status Callback',
      url: 'https://api.dodash.ai/webhooks/status',
      status: 'active',
      description: 'Receives call status updates'
    },
    {
      name: 'API Base URL',
      url: 'https://api.dodash.ai/v1',
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
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Activity Logs</h2>
          <p className="text-slate-600">System events and activity history.</p>
        </div>
        <div className="flex space-x-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search logs..."
              className="h-10 w-64 rounded-xl border-none bg-white pl-10 pr-4 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <button className="h-10 px-4 rounded-xl bg-white text-slate-600 text-sm font-bold shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 flex items-center space-x-2">
            <Filter className="h-4 w-4" />
            <span>Filter</span>
          </button>
          <button className="h-10 px-4 rounded-xl bg-blue-600 text-white text-sm font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700">
            Export
          </button>
        </div>
      </div>

      <LightGlassCard className="!p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th className="p-4">Event Type</th>
                <th className="p-4">Description</th>
                <th className="p-4">User / Agent</th>
                <th className="p-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="text-sm text-slate-700 font-medium divide-y divide-slate-100">
              {[
                { type: 'agent_created', desc: 'New agent "Sales Bot" created', user: 'Admin', time: '2 minutes ago', color: 'bg-emerald-100 text-emerald-700' },
                { type: 'call_initiated', desc: 'Outbound call to +1 (555) 123-4567', user: 'Support Bot Alpha', time: '15 minutes ago', color: 'bg-blue-100 text-blue-700' },
                { type: 'settings_changed', desc: 'Voice model updated to "nova"', user: 'Admin', time: '1 hour ago', color: 'bg-purple-100 text-purple-700' },
                { type: 'phone_registered', desc: 'New phone number registered', user: 'Admin', time: '2 hours ago', color: 'bg-cyan-100 text-cyan-700' },
                { type: 'agent_updated', desc: 'Agent "Support Bot" configuration changed', user: 'Admin', time: '3 hours ago', color: 'bg-amber-100 text-amber-700' },
                { type: 'message_sent', desc: 'SMS sent to +1 (555) 987-6543', user: 'Messaging Agent', time: '4 hours ago', color: 'bg-blue-100 text-blue-700' },
              ].map((log, i) => (
                <tr key={i} className="hover:bg-blue-50/30 transition-colors">
                  <td className="p-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold capitalize ${log.color}`}>
                      {log.type.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="p-4">{log.desc}</td>
                  <td className="p-4 text-slate-600">{log.user}</td>
                  <td className="p-4 text-slate-500">{log.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t border-slate-200/60 flex items-center justify-between text-xs text-slate-500 font-medium">
          <span>Showing 1-6 of 342 events</span>
          <div className="flex space-x-2">
            <button className="px-3 py-1 rounded-lg border border-slate-200 hover:bg-slate-50">Previous</button>
            <button className="px-3 py-1 rounded-lg border border-slate-200 hover:bg-slate-50">Next</button>
          </div>
        </div>
      </LightGlassCard>
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
      const response = await fetch('/api/phones')
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
        body: JSON.stringify(phoneForm),
      })

      if (response.ok) {
        setRegisterPhoneModalOpen(false)
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
        const response = await fetch(`/api/phones/${phoneId}`, { method: 'DELETE' })
        if (response.ok) {
          loadRegisteredPhones()
        }
      } catch (error) {
        console.error('Error deleting phone:', error)
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
                    <h3 className="text-2xl font-bold text-slate-900">Register Phone Number</h3>
                    <p className="text-sm text-slate-600 mt-1">
                      Register your Twilio phone number with credentials to use it for agents
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setRegisterPhoneModalOpen(false)}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-slate-600" />
                </button>
              </div>
            </div>

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
            <NavItem icon={Phone} label="Phone / Dialer" active={activeTab === 'dialer'} onClick={() => setActiveTab('dialer')} />
            <NavItem icon={Users} label="Agents & Chat" active={activeTab === 'agents'} onClick={() => setActiveTab('agents')} />
            <NavItem icon={PhoneIncoming} label="Incoming Agent" active={activeTab === 'incoming-agent'} onClick={() => setActiveTab('incoming-agent')} />
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
                  {activeTab === 'dialer' ? 'Phone & Dialer' :
                    activeTab === 'agents' ? 'Agent Management' :
                      activeTab === 'incoming-agent' ? 'Incoming Agent' :
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
                    activeTab === 'agents' ? 'Configure agents and test conversations.' :
                      activeTab === 'incoming-agent' ? 'Create and manage Voice Agents for your Business.' :
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
              {activeTab === 'dialer' && <DialerView />}
              {activeTab === 'agents' && <AgentsView />}
              {activeTab === 'incoming-agent' && <IncomingAgentView />}
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

// Helper icons
function DollarSign(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" x2="12" y1="2" y2="22" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  )
}
