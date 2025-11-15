'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { PhoneCall, Loader2 } from 'lucide-react'
import { makeOutboundCall, type RegisteredPhone } from '@/lib/api'
import { cn } from '@/lib/utils'

interface MakeCallFormProps {
  registeredPhones: RegisteredPhone[]
}

export function MakeCallForm({ registeredPhones = [] }: MakeCallFormProps) {
  const [selectedPhoneId, setSelectedPhoneId] = useState('')
  const [toNumber, setToNumber] = useState('')
  const [aiPrompt, setAiPrompt] = useState('')
  const [greeting, setGreeting] = useState('')
  const [calling, setCalling] = useState(false)
  const [callResult, setCallResult] = useState<{ success: boolean; message: string } | null>(null)

  // Filter only active registered phones
  const activePhones = registeredPhones.filter((phone) => phone.isActive !== false)

  const selectedPhone = activePhones.find((phone) => phone.id === selectedPhoneId)

  const handleMakeCall = async () => {
    if (!selectedPhoneId || !toNumber) {
      alert('Please select a registered phone number and enter a destination phone number')
      return
    }

    // Basic phone number validation (E.164 format) for "To" number
    const phoneRegex = /^\+[1-9]\d{1,14}$/
    if (!phoneRegex.test(toNumber)) {
      alert('Invalid destination phone number format. Please use E.164 format (e.g., +15551234567)')
      return
    }

    try {
      setCalling(true)
      setCallResult(null)

      // Build custom context from AI prompt and greeting
      let customContext = ''
      if (aiPrompt.trim()) {
        customContext = aiPrompt.trim()
      }
      if (greeting.trim()) {
        if (customContext) {
          customContext += `\n\nGreeting: ${greeting.trim()}`
        } else {
          customContext = `Greeting: ${greeting.trim()}`
        }
      }

      console.log('📞 Initiating outbound call:', {
        from: selectedPhone?.phoneNumber,
        to: toNumber,
        hasAiPrompt: !!aiPrompt,
        hasGreeting: !!greeting,
      })

      const result = await makeOutboundCall({
        from: selectedPhone!.phoneNumber,
        to: toNumber,
        context: customContext || undefined,
      })

      console.log('✅ Outbound call initiated successfully:', result.call_sid)

      setCallResult({
        success: true,
        message: `Call initiated successfully! Call SID: ${result.call_sid}`,
      })

      // Clear form after successful call
      setToNumber('')
      setAiPrompt('')
      setGreeting('')
    } catch (error) {
      console.error('❌ Error making outbound call:', error)
      setCallResult({
        success: false,
        message: error instanceof Error ? error.message : 'Failed to make outbound call',
      })
    } finally {
      setCalling(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
      <div className="p-6 space-y-5">
        {/* Registered Phone Number */}
        <div>
          <label className="text-sm font-medium text-slate-700 mb-1 block">
            Registered Phone Number <span className="text-red-500">*</span>
          </label>
          {activePhones.length > 0 ? (
            <select
              value={selectedPhoneId}
              onChange={(e) => setSelectedPhoneId(e.target.value)}
              disabled={calling}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-slate-900 disabled:bg-slate-100 disabled:cursor-not-allowed"
              required
            >
              <option value="">Select a registered phone number</option>
              {activePhones.map((phone) => (
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
          <p className="text-xs text-slate-500 mt-1">
            Select a phone number that has been registered with Twilio credentials
          </p>
        </div>

        {/* Destination Phone Number */}
        <div>
          <label className="text-sm font-medium text-slate-700 mb-1 block">
            Phone Number to Call <span className="text-red-500">*</span>
          </label>
          <Input
            type="tel"
            value={toNumber}
            onChange={(e) => setToNumber(e.target.value)}
            placeholder="+15559876543"
            required
            disabled={calling}
            className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-slate-500 mt-1">
            Enter the destination phone number in E.164 format (e.g., +15551234567)
          </p>
        </div>

        {/* AI Prompt */}
        <div>
          <label className="text-sm font-medium text-slate-700 mb-1 block">
            Prompt for AI to Talk
          </label>
          <Textarea
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            placeholder="You are calling to follow up on a customer inquiry. Be friendly and professional."
            disabled={calling}
            rows={4}
            className="resize-none bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-slate-500 mt-1">
            Provide instructions for the AI agent on what to say during the call
          </p>
        </div>

        {/* Greeting Prompt */}
        <div>
          <label className="text-sm font-medium text-slate-700 mb-1 block">
            Greeting Prompt
          </label>
          <Textarea
            value={greeting}
            onChange={(e) => setGreeting(e.target.value)}
            placeholder="Hello! This is an automated call from [Your Company]. How can I help you today?"
            disabled={calling}
            rows={3}
            className="resize-none bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-slate-500 mt-1">
            The initial greeting message the AI will say when the call is answered
          </p>
        </div>

        {/* Call Result */}
        {callResult && (
          <div
            className={cn(
              'p-4 rounded-lg border',
              callResult.success
                ? 'bg-green-50 border-green-200 text-green-800'
                : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            <p className="text-sm font-medium">{callResult.message}</p>
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleMakeCall}
          disabled={calling || !selectedPhoneId || !toNumber || activePhones.length === 0}
          className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white"
        >
          {calling ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Initiating Call...
            </>
          ) : (
            <>
              <PhoneCall className="h-4 w-4 mr-2" />
              Make Call
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

