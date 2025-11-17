'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { MessageSquare, Loader2 } from 'lucide-react'
import { sendMessage, type RegisteredPhone } from '@/lib/api'
import { cn } from '@/lib/utils'

interface SendMessageFormProps {
  registeredPhones: RegisteredPhone[]
  onMessageSent?: () => void
}

export function SendMessageForm({ registeredPhones = [], onMessageSent }: SendMessageFormProps) {
  const [selectedPhoneId, setSelectedPhoneId] = useState('')
  const [toNumber, setToNumber] = useState('')
  const [messageBody, setMessageBody] = useState('')
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<{ success: boolean; message: string } | null>(null)

  // Filter only active registered phones
  const activePhones = registeredPhones.filter((phone) => phone.isActive !== false)

  const selectedPhone = activePhones.find((phone) => phone.id === selectedPhoneId)

  const handleSendMessage = async () => {
    if (!selectedPhoneId || !toNumber || !messageBody.trim()) {
      alert('Please select a registered phone number, enter a destination phone number, and provide a message')
      return
    }

    // Basic phone number validation (E.164 format) for "To" number
    const phoneRegex = /^\+[1-9]\d{1,14}$/
    if (!phoneRegex.test(toNumber)) {
      alert('Invalid destination phone number format. Please use E.164 format (e.g., +15551234567)')
      return
    }

    try {
      setSending(true)
      setSendResult(null)

      console.log('📱 Sending SMS:', {
        from: selectedPhone?.phoneNumber,
        to: toNumber,
        body: messageBody,
      })

      const result = await sendMessage({
        from: selectedPhone!.phoneNumber,
        to: toNumber,
        body: messageBody.trim(),
      })

      console.log('✅ SMS sent successfully:', result.message_sid)

      setSendResult({
        success: true,
        message: `Message sent successfully! Message SID: ${result.message_sid}`,
      })

      // Clear form after successful send
      setToNumber('')
      setMessageBody('')
      
      // Notify parent to reload messages
      if (onMessageSent) {
        setTimeout(() => onMessageSent(), 1000)
      }
    } catch (error) {
      console.error('❌ Error sending message:', error)
      setSendResult({
        success: false,
        message: error instanceof Error ? error.message : 'Failed to send message',
      })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm">
      <div className="p-6 space-y-5">
        {/* Header */}
        <div>
          <h2 className="text-lg font-semibold text-slate-800 mb-1">Send SMS Message</h2>
          <p className="text-sm text-slate-600">Send a text message from one of your registered phone numbers</p>
        </div>

        {/* Registered Phone Number */}
        <div>
          <label className="text-sm font-medium text-slate-700 mb-1 block">
            From (Registered Phone Number) <span className="text-red-500">*</span>
          </label>
          {activePhones.length > 0 ? (
            <select
              value={selectedPhoneId}
              onChange={(e) => setSelectedPhoneId(e.target.value)}
              disabled={sending}
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
            To (Destination Phone Number) <span className="text-red-500">*</span>
          </label>
          <Input
            type="tel"
            value={toNumber}
            onChange={(e) => setToNumber(e.target.value)}
            placeholder="+15559876543"
            required
            disabled={sending}
            className="bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-slate-500 mt-1">
            Enter the destination phone number in E.164 format (e.g., +15551234567)
          </p>
        </div>

        {/* Message Body */}
        <div>
          <label className="text-sm font-medium text-slate-700 mb-1 block">
            Message <span className="text-red-500">*</span>
          </label>
          <Textarea
            value={messageBody}
            onChange={(e) => setMessageBody(e.target.value)}
            placeholder="Type your message here..."
            disabled={sending}
            rows={4}
            className="resize-none bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
            required
          />
          <p className="text-xs text-slate-500 mt-1">
            Enter the message text you want to send (max 1600 characters for SMS)
          </p>
        </div>

        {/* Send Result */}
        {sendResult && (
          <div
            className={cn(
              'p-4 rounded-lg border',
              sendResult.success
                ? 'bg-green-50 border-green-200 text-green-800'
                : 'bg-red-50 border-red-200 text-red-800'
            )}
          >
            <p className="text-sm font-medium">{sendResult.message}</p>
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSendMessage}
          disabled={sending || !selectedPhoneId || !toNumber || !messageBody.trim() || activePhones.length === 0}
          className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white"
        >
          {sending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Sending Message...
            </>
          ) : (
            <>
              <MessageSquare className="h-4 w-4 mr-2" />
              Send Message
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

