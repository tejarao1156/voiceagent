'use client'

import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, Settings, Bot, MessageSquare, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Slider } from '@/components/ui/slider'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { fetchRegisteredPhones, type RegisteredPhone } from '@/lib/api'

interface CreateAgentModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: {
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
  }) => void
  editAgent?: {
    id: string
    name: string
    direction: 'incoming' | 'outgoing' | 'messaging'
    phoneNumber: string
    sttModel?: string
    inferenceModel?: string
    ttsModel?: string
    ttsVoice?: string
    systemPrompt?: string
    greeting?: string
    temperature?: number
    maxTokens?: number
    active?: boolean
    phoneIsDeleted?: boolean
    twilioAccountSid?: string
    twilioAuthToken?: string
  } | null
  activeSection?: 'incoming-agent' | 'outgoing-agent' | 'messaging-agent'
}

export function CreateAgentModal({
  open,
  onOpenChange,
  onSubmit,
  editAgent,
  activeSection = 'incoming-agent',
}: CreateAgentModalProps) {
  const isEditMode = !!editAgent
  // Agent is read-only if: inactive (active=false) OR phone is deleted
  const isInactiveAgent = isEditMode && editAgent && (
    editAgent.active === false || 
    editAgent.phoneIsDeleted === true
  )
  
  const [formData, setFormData] = useState({
    name: '',
    direction: 'incoming' as 'incoming' | 'outgoing' | 'messaging',
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
    twilioAccountSid: '',
    twilioAuthToken: '',
  })

  const [webhookUrls, setWebhookUrls] = useState<{
    incomingUrl: string
    statusCallbackUrl: string
    environment?: { runtime: string; baseUrl: string }
  } | null>(null)
  const [registeredPhones, setRegisteredPhones] = useState<RegisteredPhone[]>([])
  const [selectedPhoneId, setSelectedPhoneId] = useState<string>('')
  const [isTwilioPhone, setIsTwilioPhone] = useState(false)  // Auto-detect if phone is Twilio
  
  // Check if this is a messaging agent (after formData is initialized)
  const isMessagingAgent = formData.direction === 'messaging'

  // Fetch webhook URLs and registered phones when modal opens
  useEffect(() => {
    const fetchData = async () => {
      if (open) {
        try {
          // Fetch webhook URLs (always fetch, will show conditionally)
          const response = await fetch('/webhooks/twilio/urls')
          if (response.ok) {
            const data = await response.json()
            setWebhookUrls(data)
          }
          
          // Fetch registered phones (only active ones for agent creation)
          if (!isEditMode) {
            const phones = await fetchRegisteredPhones(true) // Only active phones
            setRegisteredPhones(phones)
            if (phones.length > 0) {
              setSelectedPhoneId(phones[0].id)
              const firstPhone = phones[0]
              setFormData(prev => ({
                ...prev,
                phoneNumber: firstPhone.phoneNumber,
                twilioAccountSid: firstPhone.twilioAccountSid,
              }))
              // Check if phone is Twilio (has twilioAccountSid)
              setIsTwilioPhone(!!firstPhone.twilioAccountSid)
            }
          }
        } catch (error) {
          console.error('Failed to fetch data:', error)
        }
      }
    }
    fetchData()
  }, [open, isEditMode])
  
  // Handle registered phone selection
  useEffect(() => {
    if (selectedPhoneId && !isEditMode) {
      const selectedPhone = registeredPhones.find(p => p.id === selectedPhoneId)
      if (selectedPhone) {
        setFormData(prev => ({
          ...prev,
          phoneNumber: selectedPhone.phoneNumber,
          twilioAccountSid: selectedPhone.twilioAccountSid,
        }))
        // Auto-detect if phone is Twilio (has twilioAccountSid)
        setIsTwilioPhone(!!selectedPhone.twilioAccountSid)
      }
    }
  }, [selectedPhoneId, isEditMode, registeredPhones])

  // Load edit agent data when modal opens
  useEffect(() => {
    if (open && editAgent) {
      setFormData({
        name: editAgent.name || '',
        direction: ((editAgent.direction as string) === 'inbound' ? 'incoming' : editAgent.direction) || 'incoming',
        phoneNumber: editAgent.phoneNumber || '',
        sttModel: editAgent.sttModel || 'whisper-1',
        inferenceModel: editAgent.inferenceModel || 'gpt-4o-mini',
        ttsModel: editAgent.ttsModel || 'tts-1',
        ttsVoice: editAgent.ttsVoice || 'alloy',
        systemPrompt: editAgent.systemPrompt || '',
        greeting: editAgent.greeting || '',
        temperature: editAgent.temperature ?? 0.7,
        maxTokens: editAgent.maxTokens ?? 500,
        active: editAgent.active ?? true,
        twilioAccountSid: editAgent.twilioAccountSid || '',
        twilioAuthToken: editAgent.twilioAuthToken || '',
      })
      // Check if phone is Twilio (has twilioAccountSid)
      setIsTwilioPhone(!!editAgent.twilioAccountSid)
    } else if (open && !editAgent) {
      // Reset form for create mode - set direction based on activeSection
      const defaultDirection = activeSection === 'messaging-agent' ? 'messaging' 
        : activeSection === 'outgoing-agent' ? 'outgoing' 
        : 'incoming'
      setFormData({
        name: '',
        direction: defaultDirection,
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
        twilioAccountSid: '',
        twilioAuthToken: '',
      })
      setIsTwilioPhone(false)
    }
  }, [open, editAgent, activeSection])

  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    aiModels: true,
    behavior: false,
    advanced: false,
    provider: false,
  })

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Prevent submission for inactive agents
    if (isInactiveAgent) {
      const reason = editAgent && editAgent.phoneIsDeleted
        ? 'The associated phone number has been deleted'
        : 'This agent is inactive'
      alert(`This agent cannot be updated. ${reason}.`)
      return
    }
    
    // Validate that a registered phone is selected (for new agents)
    if (!isEditMode && (!selectedPhoneId || !formData.phoneNumber)) {
      alert('Please select a registered phone number')
      return
    }
    
    // Validate that registered phones exist (for new agents)
    if (!isEditMode && registeredPhones.length === 0) {
      alert('No registered phone numbers available. Please register a phone number first.')
      return
    }
    
    onSubmit(formData)
    // Reset form - set direction based on activeSection
    const defaultDirection = activeSection === 'messaging-agent' ? 'messaging' 
      : activeSection === 'outgoing-agent' ? 'outgoing' 
      : 'incoming'
    setFormData({
      name: '',
      direction: defaultDirection,
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
      twilioAccountSid: '',
      twilioAuthToken: '',
    })
    setSelectedPhoneId('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto bg-white border-slate-200 [&>button]:text-slate-600">
        <DialogHeader>
          <DialogTitle className="text-2xl font-semibold text-slate-900">
            {isEditMode ? (isInactiveAgent ? 'View AI Agent (Inactive)' : 'Edit AI Agent') : 'Create New AI Agent'}
          </DialogTitle>
          <p className="text-sm text-slate-600 mt-1">
            {isInactiveAgent 
              ? (editAgent && editAgent.phoneIsDeleted
                  ? 'This agent is read-only because its associated phone number was deleted. You can view the configuration but cannot make changes.'
                  : 'This agent is inactive. You can view the configuration but cannot make changes.')
              : isEditMode 
              ? (isMessagingAgent 
                  ? 'Update your messaging AI agent configuration (name and phone number cannot be changed)'
                  : 'Update your voice AI agent configuration (name and phone number cannot be changed)')
              : (isMessagingAgent
                  ? 'Configure your messaging AI agent with phone number, prompt, and greeting'
                  : 'Configure your voice AI agent with custom models and behavior settings')}
          </p>
          {isInactiveAgent && (
            <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-800">
                ⚠️ This agent is read-only. {editAgent && editAgent.phoneIsDeleted 
                  ? 'The associated phone number has been deleted, so this agent cannot be edited or activated.'
                  : 'This agent is inactive and cannot be edited or activated.'}
              </p>
            </div>
          )}
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          {/* Basic Information Section */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => toggleSection('basic')}
              className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-indigo-600" />
                <span className="font-semibold text-slate-900">Basic Information</span>
              </div>
              {expandedSections.basic ? (
                <ChevronUp className="h-5 w-5 text-slate-600" />
              ) : (
                <ChevronDown className="h-5 w-5 text-slate-600" />
              )}
            </button>
            {expandedSections.basic && (
              <div className="p-4 space-y-4 bg-white">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    Agent Name <span className="text-red-500">*</span>
                    {isEditMode && <span className="text-xs text-slate-500 ml-2">(Cannot be changed)</span>}
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., gman, alexa-bot"
                    required
                    disabled={isEditMode || isInactiveAgent}
                    className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    Phone Number <span className="text-red-500">*</span>
                    {isEditMode && <span className="text-xs text-slate-500 ml-2">(Cannot be changed)</span>}
                  </label>
                  {isEditMode ? (
                    <div className="pointer-events-none opacity-60">
                      <Input
                        value={formData.phoneNumber}
                        readOnly
                        className="bg-slate-50 border-slate-300 text-slate-600 cursor-not-allowed"
                      />
                    </div>
                  ) : registeredPhones.length > 0 ? (
                    <select
                      value={selectedPhoneId}
                      onChange={(e) => setSelectedPhoneId(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900"
                      required
                    >
                      <option value="">Select a registered phone number</option>
                      {registeredPhones.map((phone) => (
                        <option key={phone.id} value={phone.id}>
                          {phone.phoneNumber}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <p className="text-sm font-medium text-amber-900 mb-1">
                        No registered phone numbers available
                      </p>
                      <p className="text-xs text-amber-700">
                        Please register a phone number first using the "Register Phone Number" button in the top navigation bar.
                      </p>
                    </div>
                  )}
                  {!isEditMode && registeredPhones.length > 0 && (
                    <p className="text-xs text-slate-500 mt-1">
                      Select a phone number that has been registered with Twilio credentials
                    </p>
                  )}
                </div>

                  <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="active"
                    checked={formData.active}
                    onChange={(e) =>
                      setFormData({ ...formData, active: e.target.checked })
                    }
                    disabled={isInactiveAgent}
                    className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 disabled:cursor-not-allowed"
                  />
                  <label htmlFor="active" className="text-sm font-medium text-slate-700 cursor-pointer">
                    {isMessagingAgent 
                      ? 'Active (Enable agent to receive messages and respond)'
                      : 'Active (Enable agent to receive calls)'}
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* AI Model Configuration Section - Hide STT/TTS for messaging agents */}
          {!isMessagingAgent && (
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('aiModels')}
                className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-indigo-600" />
                  <span className="font-semibold text-slate-900">AI Model Configuration</span>
                </div>
                {expandedSections.aiModels ? (
                  <ChevronUp className="h-5 w-5 text-slate-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-slate-600" />
                )}
              </button>
              {expandedSections.aiModels && (
                <div className="p-4 space-y-4 bg-white">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-1 block">
                        STT Model <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={formData.sttModel}
                        onChange={(e) =>
                          setFormData({ ...formData, sttModel: e.target.value })
                        }
                        disabled={isInactiveAgent}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
                      >
                        <option value="whisper-1">whisper-1</option>
                      </select>
                      <p className="text-xs text-slate-500 mt-1">Speech-to-Text model</p>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-1 block">
                        Inference Model <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={formData.inferenceModel}
                        onChange={(e) =>
                          setFormData({ ...formData, inferenceModel: e.target.value })
                        }
                        disabled={isInactiveAgent}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
                      >
                        <option value="gpt-4o-mini">gpt-4o-mini (Fast, Cost-effective)</option>
                        <option value="gpt-4o">gpt-4o (More Capable)</option>
                        <option value="gpt-4o-realtime-preview-2024-12-17">gpt-4o-realtime-preview (Realtime)</option>
                      </select>
                      <p className="text-xs text-slate-500 mt-1">LLM for generating responses</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-1 block">
                        TTS Model <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={formData.ttsModel}
                        onChange={(e) =>
                          setFormData({ ...formData, ttsModel: e.target.value })
                        }
                        disabled={isInactiveAgent}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
                      >
                        <option value="tts-1">tts-1 (Faster, Lower Latency)</option>
                        <option value="tts-1-hd">tts-1-hd (Higher Quality)</option>
                      </select>
                      <p className="text-xs text-slate-500 mt-1">Text-to-Speech model</p>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-1 block">
                        TTS Voice <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={formData.ttsVoice}
                        onChange={(e) =>
                          setFormData({ ...formData, ttsVoice: e.target.value })
                        }
                        disabled={isInactiveAgent}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
                      >
                        <option value="alloy">alloy</option>
                        <option value="echo">echo</option>
                        <option value="fable">fable</option>
                        <option value="onyx">onyx</option>
                        <option value="nova">nova</option>
                        <option value="shimmer">shimmer</option>
                      </select>
                      <p className="text-xs text-slate-500 mt-1">Voice personality</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* LLM Model Configuration Section - For messaging agents only */}
          {isMessagingAgent && (
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('aiModels')}
                className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-indigo-600" />
                  <span className="font-semibold text-slate-900">LLM Model Configuration</span>
                </div>
                {expandedSections.aiModels ? (
                  <ChevronUp className="h-5 w-5 text-slate-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-slate-600" />
                )}
              </button>
              {expandedSections.aiModels && (
                <div className="p-4 space-y-4 bg-white">
                  <div>
                    <label className="text-sm font-medium text-slate-700 mb-1 block">
                      Inference Model <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={formData.inferenceModel}
                      onChange={(e) =>
                        setFormData({ ...formData, inferenceModel: e.target.value })
                      }
                      disabled={isInactiveAgent}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
                    >
                      <option value="gpt-4o-mini">gpt-4o-mini (Fast, Cost-effective)</option>
                      <option value="gpt-4o">gpt-4o (More Capable)</option>
                      <option value="gpt-4o-realtime-preview-2024-12-17">gpt-4o-realtime-preview (Realtime)</option>
                    </select>
                    <p className="text-xs text-slate-500 mt-1">LLM for generating message responses</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Behavior Configuration Section */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => toggleSection('behavior')}
              className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-indigo-600" />
                <span className="font-semibold text-slate-900">Behavior Configuration</span>
              </div>
              {expandedSections.behavior ? (
                <ChevronUp className="h-5 w-5 text-slate-600" />
              ) : (
                <ChevronDown className="h-5 w-5 text-slate-600" />
              )}
            </button>
            {expandedSections.behavior && (
              <div className="p-4 space-y-4 bg-white">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    System Prompt <span className="text-red-500">*</span>
                  </label>
                  <Textarea
                    value={formData.systemPrompt}
                    onChange={(e) =>
                      setFormData({ ...formData, systemPrompt: e.target.value })
                    }
                    placeholder="You are a helpful customer support agent..."
                    required
                    rows={4}
                    disabled={isInactiveAgent}
                    className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Custom instructions for AI behavior and personality
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    Greeting Message
                  </label>
                  <Input
                    value={formData.greeting}
                    onChange={(e) =>
                      setFormData({ ...formData, greeting: e.target.value })
                    }
                    placeholder="Welcome to customer support! How can I help you?"
                    disabled={isInactiveAgent}
                    className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    {isMessagingAgent 
                      ? 'Initial message sent when user first texts (optional)'
                      : 'Initial message when call starts (optional)'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Advanced Configuration Section */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => toggleSection('advanced')}
              className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-indigo-600" />
                <span className="font-semibold text-slate-900">Advanced Configuration</span>
              </div>
              {expandedSections.advanced ? (
                <ChevronUp className="h-5 w-5 text-slate-600" />
              ) : (
                <ChevronDown className="h-5 w-5 text-slate-600" />
              )}
            </button>
            {expandedSections.advanced && (
              <div className="p-4 space-y-4 bg-white">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-2 block">
                    Temperature: {formData.temperature.toFixed(1)}
                  </label>
                  <Slider
                    value={formData.temperature}
                    onValueChange={(value) =>
                      setFormData({ ...formData, temperature: value })
                    }
                    min={0}
                    max={2}
                    step={0.1}
                    disabled={isInactiveAgent}
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Controls response randomness (0.0 = deterministic, 2.0 = creative)
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    Max Tokens
                  </label>
                  <Input
                    type="number"
                    value={formData.maxTokens}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        maxTokens: parseInt(e.target.value) || 500,
                      })
                    }
                    disabled={isInactiveAgent}
                    min={1}
                    max={4000}
                    className="bg-white border-slate-300 text-slate-900"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Maximum response length (1-4000 tokens)
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Twilio Configuration (shown only if phone is associated with Twilio) */}
          {isTwilioPhone && (
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('provider')}
                className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <Settings className="h-5 w-5 text-indigo-600" />
                  <span className="font-semibold text-slate-900">Twilio Configuration</span>
                </div>
                {expandedSections.provider ? (
                  <ChevronUp className="h-5 w-5 text-slate-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-slate-600" />
                )}
              </button>
              {expandedSections.provider && (
                <div className="p-4 space-y-4 bg-white">
                  {/* Webhook URLs - Read Only */}
                  {webhookUrls && (
                    <>
                      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 mb-4">
                        <p className="text-xs font-medium text-indigo-900 mb-2">
                          🌐 Environment: {webhookUrls.environment?.runtime?.toUpperCase() || 'UNKNOWN'}
                        </p>
                        <p className="text-xs text-indigo-700">
                          This phone number is associated with Twilio. Configure these webhook URLs in your Twilio Console.
                        </p>
                      </div>

                      <div>
                        <label className="text-sm font-medium text-slate-700 mb-1 block">
                          Incoming Webhook URL <span className="text-xs text-slate-500">(Read-only)</span>
                        </label>
                        <Input
                          type="text"
                          value={webhookUrls.incomingUrl}
                          readOnly
                          disabled
                          className="bg-slate-50 border-slate-300 text-slate-600 cursor-not-allowed font-mono text-xs"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                          Set this as "A CALL COMES IN" webhook in Twilio Console
                        </p>
                      </div>

                      <div>
                        <label className="text-sm font-medium text-slate-700 mb-1 block">
                          Status Callback URL <span className="text-xs text-slate-500">(Read-only)</span>
                        </label>
                        <Input
                          type="text"
                          value={webhookUrls.statusCallbackUrl}
                          readOnly
                          disabled
                          className="bg-slate-50 border-slate-300 text-slate-600 cursor-not-allowed font-mono text-xs"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                          Set this as "STATUS CALLBACK URL" in Twilio Console
                        </p>
                      </div>

                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Form Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="border-slate-300"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg disabled:bg-slate-400 disabled:cursor-not-allowed"
              disabled={isInactiveAgent || (!isEditMode && registeredPhones.length === 0)}
            >
              {isInactiveAgent ? 'View Only (Inactive)' : (isEditMode ? 'Update Agent' : 'Create Agent')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
