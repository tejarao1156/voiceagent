'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Phone, PhoneCall, Loader2 } from 'lucide-react'
import { makeOutboundCall, type RegisteredPhone } from '@/lib/api'
import { cn } from '@/lib/utils'

interface OutgoingAgentProps {
  registeredPhones?: RegisteredPhone[]
}

export function OutgoingAgent({ registeredPhones = [] }: OutgoingAgentProps) {
  const [fromNumber, setFromNumber] = useState('')
  const [toNumber, setToNumber] = useState('')
  const [context, setContext] = useState('')
  const [calling, setCalling] = useState(false)
  const [callResult, setCallResult] = useState<{ success: boolean; message: string } | null>(null)

  // Filter only active registered phones
  const activePhones = registeredPhones.filter((phone) => phone.isActive !== false)

  // Log when registered phones change
  useEffect(() => {
    if (registeredPhones.length > 0) {
      console.log(`📱 Loaded ${registeredPhones.length} registered phone(s), ${activePhones.length} active`)
    } else {
      console.warn('⚠️ No registered phones available for outbound calls')
    }
  }, [registeredPhones.length, activePhones.length])

  const handleMakeCall = async () => {
    if (!fromNumber || !toNumber) {
      alert('Please select a "From" phone number and enter a "To" phone number')
      return
    }

    // Basic phone number validation (E.164 format) for "To" number
    const phoneRegex = /^\+[1-9]\d{1,14}$/
    if (!phoneRegex.test(toNumber)) {
      alert('Invalid "To" phone number format. Please use E.164 format (e.g., +15551234567)')
      return
    }

    try {
      setCalling(true)
      setCallResult(null)

      console.log('📞 Initiating outbound call:', { from: fromNumber, to: toNumber, hasContext: !!context })

      const result = await makeOutboundCall({
        from: fromNumber,
        to: toNumber,
        context: context || undefined,
      })

      console.log('✅ Outbound call initiated successfully:', result.call_sid)

      setCallResult({
        success: true,
        message: `Call initiated successfully! Call SID: ${result.call_sid}`,
      })

      // Clear form after successful call
      setToNumber('')
      setContext('')
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PhoneCall className="h-5 w-5" />
            Make Outbound Call
          </CardTitle>
          <CardDescription>
            Initiate an outbound phone call using a registered phone number. You can optionally provide custom context for the AI agent.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* From Number */}
          <div className="space-y-2">
            <label htmlFor="from-number" className="text-sm font-medium text-slate-700">
              From (Your Registered Number) <span className="text-red-500">*</span>
            </label>
            {activePhones.length > 0 ? (
              <select
                id="from-number"
                value={fromNumber}
                onChange={(e) => setFromNumber(e.target.value)}
                disabled={calling}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select a registered phone number</option>
                {activePhones.map((phone) => (
                  <option key={phone.id} value={phone.phoneNumber}>
                    {phone.phoneNumber}
                  </option>
                ))}
              </select>
            ) : (
              <div className="p-4 border border-slate-300 rounded-md bg-slate-50">
                <p className="text-sm text-slate-600">
                  No registered phone numbers found. Please register a phone number in the Incoming Agent section first.
                </p>
              </div>
            )}
            <p className="text-xs text-slate-500">
              Select a registered phone number from the dropdown. Only active registered numbers are shown.
            </p>
          </div>

          {/* To Number */}
          <div className="space-y-2">
            <label htmlFor="to-number" className="text-sm font-medium text-slate-700">
              To (Destination Number) <span className="text-red-500">*</span>
            </label>
            <Input
              id="to-number"
              type="tel"
              placeholder="+15559876543"
              value={toNumber}
              onChange={(e) => setToNumber(e.target.value)}
              disabled={calling}
            />
            <p className="text-xs text-slate-500">
              Enter the destination phone number in E.164 format (e.g., +15559876543)
            </p>
          </div>

          {/* Custom Context */}
          <div className="space-y-2">
            <label htmlFor="context" className="text-sm font-medium text-slate-700">
              Custom Context (Optional)
            </label>
            <Textarea
              id="context"
              placeholder="You are calling to follow up on a customer inquiry about product availability. Be friendly and professional."
              value={context}
              onChange={(e) => setContext(e.target.value)}
              disabled={calling}
              rows={4}
              className="resize-none"
            />
            <p className="text-xs text-slate-500">
              Optional: Provide custom context for this call. If not provided, the agent's default system prompt will be used.
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
            disabled={calling || !fromNumber || !toNumber || activePhones.length === 0}
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white"
          >
            {calling ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Initiating Call...
              </>
            ) : (
              <>
                <Phone className="h-4 w-4 mr-2" />
                Make Call
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Information Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">How It Works</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="text-indigo-600 font-semibold">1.</span>
              <span>Select a registered phone number from the dropdown as the "From" number</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-indigo-600 font-semibold">2.</span>
              <span>Enter the destination phone number in E.164 format</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-indigo-600 font-semibold">3.</span>
              <span>Optionally provide custom context for the AI agent</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-indigo-600 font-semibold">4.</span>
              <span>Click "Make Call" to initiate the outbound call</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-indigo-600 font-semibold">5.</span>
              <span>The system will use the agent configuration associated with the "From" number</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}

