'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, Settings, Bot, MessageSquare, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Slider } from '@/components/ui/slider'
import { PhoneInput } from '@/components/ui/phone-input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface CreateAgentModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: {
    name: string
    direction: 'inbound'
    phoneNumber: string
    provider: 'twilio' | 'custom'
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
}

export function CreateAgentModal({
  open,
  onOpenChange,
  onSubmit,
}: CreateAgentModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    direction: 'inbound' as 'inbound',
    phoneNumber: '',
    provider: 'twilio' as 'twilio' | 'custom',
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
    onSubmit(formData)
    setFormData({
      name: '',
      direction: 'inbound',
      phoneNumber: '',
      provider: 'twilio',
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
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto bg-white border-slate-200 [&>button]:text-slate-600">
        <DialogHeader>
          <DialogTitle className="text-2xl font-semibold text-slate-900">
            Create New AI Agent
          </DialogTitle>
          <p className="text-sm text-slate-600 mt-1">
            Configure your voice AI agent with custom models and behavior settings
          </p>
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
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., gman, alexa-bot"
                    required
                    className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-slate-700 mb-1 block">
                      Direction <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={formData.direction}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          direction: e.target.value as 'inbound',
                        })
                      }
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900"
                    >
                      <option value="inbound">Inbound</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-700 mb-1 block">
                      Provider <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={formData.provider}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          provider: e.target.value as 'twilio' | 'custom',
                        })
                      }
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900"
                    >
                      <option value="twilio">Twilio</option>
                      <option value="custom">Custom</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    Phone Number <span className="text-red-500">*</span>
                  </label>
                  <PhoneInput
                    value={formData.phoneNumber}
                    onChange={(value) =>
                      setFormData({ ...formData, phoneNumber: value })
                    }
                    placeholder="Enter phone number"
                    required
                  />
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="active"
                    checked={formData.active}
                    onChange={(e) =>
                      setFormData({ ...formData, active: e.target.checked })
                    }
                    className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500"
                  />
                  <label htmlFor="active" className="text-sm font-medium text-slate-700 cursor-pointer">
                    Active (Enable agent to receive calls)
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* AI Model Configuration Section */}
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
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900"
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
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900"
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
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900"
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
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900"
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
                    className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400"
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
                    className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Initial message when call starts (optional)
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

          {/* Provider-Specific Configuration */}
          {formData.provider === 'twilio' && (
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
                  <div>
                    <label className="text-sm font-medium text-slate-700 mb-1 block">
                      Twilio Account SID (Optional)
                    </label>
                    <Input
                      type="text"
                      value={formData.twilioAccountSid}
                      onChange={(e) =>
                        setFormData({ ...formData, twilioAccountSid: e.target.value })
                      }
                      placeholder="Override default Twilio account"
                      className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium text-slate-700 mb-1 block">
                      Twilio Auth Token (Optional)
                    </label>
                    <Input
                      type="password"
                      value={formData.twilioAuthToken}
                      onChange={(e) =>
                        setFormData({ ...formData, twilioAuthToken: e.target.value })
                      }
                      placeholder="Override default Twilio auth token"
                      className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400"
                    />
                  </div>
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
              className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg"
            >
              Create Agent
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
