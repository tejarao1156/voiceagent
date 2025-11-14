'use client'

import { useState, useEffect } from 'react'
import { Phone, Copy, Check, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { registerPhone, type RegisteredPhone } from '@/lib/api'

interface RegisterPhoneModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function RegisterPhoneModal({
  open,
  onOpenChange,
  onSuccess,
}: RegisterPhoneModalProps) {
  const [formData, setFormData] = useState({
    phoneNumber: '',
    twilioAccountSid: '',
    twilioAuthToken: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [webhookConfig, setWebhookConfig] = useState<{
    incomingUrl: string
    statusCallbackUrl: string
    steps: string[]
  } | null>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)

  // Reset form when modal opens/closes
  useEffect(() => {
    if (open) {
      setFormData({
        phoneNumber: '',
        twilioAccountSid: '',
        twilioAuthToken: '',
      })
      setError(null)
      setSuccess(false)
      setWebhookConfig(null)
      setCopiedField(null)
    }
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const result = await registerPhone({
        phoneNumber: formData.phoneNumber,
        twilioAccountSid: formData.twilioAccountSid,
        twilioAuthToken: formData.twilioAuthToken,
      })

      setSuccess(true)
      setWebhookConfig({
        incomingUrl: result.webhookConfiguration.incomingUrl,
        statusCallbackUrl: result.webhookConfiguration.statusCallbackUrl,
        steps: result.webhookConfiguration.steps,
      })

      // Call success callback
      if (onSuccess) {
        onSuccess()
      }
    } catch (err: any) {
      // Handle duplicate phone error (409 Conflict)
      if (err.message && err.message.includes('already registered')) {
        setError(`This phone number is already registered. Please delete the existing registration first or use a different phone number.`)
      } else {
        setError(err.message || 'Failed to register phone number')
      }
      console.error('Error registering phone:', err)
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto bg-white border-slate-200 [&>button]:text-slate-600">
        <DialogHeader>
          <DialogTitle className="text-2xl font-semibold text-slate-900 flex items-center gap-2">
            <Phone className="h-6 w-6 text-indigo-600" />
            Register Phone Number
          </DialogTitle>
          <p className="text-sm text-slate-600 mt-1">
            Register your Twilio phone number with credentials to use it for agents
          </p>
        </DialogHeader>

        {!success ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Phone Number */}
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1 block">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <Input
                type="tel"
                value={formData.phoneNumber}
                onChange={(e) =>
                  setFormData({ ...formData, phoneNumber: e.target.value })
                }
                placeholder="+1 555 123 4567"
                required
                className="bg-white border-slate-300 text-slate-900"
              />
              <p className="text-xs text-slate-500 mt-1">
                Your Twilio phone number in E.164 format
              </p>
            </div>

            {/* Twilio Account SID */}
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1 block">
                Twilio Account SID <span className="text-red-500">*</span>
              </label>
              <Input
                type="text"
                value={formData.twilioAccountSid}
                onChange={(e) =>
                  setFormData({ ...formData, twilioAccountSid: e.target.value })
                }
                placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                required
                className="bg-white border-slate-300 text-slate-900 font-mono text-sm"
              />
              <p className="text-xs text-slate-500 mt-1">
                Found in Twilio Console → Dashboard → Account Info
              </p>
            </div>

            {/* Twilio Auth Token */}
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1 block">
                Twilio Auth Token <span className="text-red-500">*</span>
              </label>
              <Input
                type="password"
                value={formData.twilioAuthToken}
                onChange={(e) =>
                  setFormData({ ...formData, twilioAuthToken: e.target.value })
                }
                placeholder="Enter your Twilio Auth Token"
                required
                className="bg-white border-slate-300 text-slate-900 font-mono text-sm"
              />
              <p className="text-xs text-slate-500 mt-1">
                Found in Twilio Console → Dashboard → Account Info → Auth Token
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-900">Error</p>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            )}

            {/* Form Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                className="border-slate-300"
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg"
                disabled={loading}
              >
                {loading ? 'Registering...' : 'Register Phone'}
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            {/* Success Message */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Check className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-900">
                    Phone Number Registered Successfully!
                  </p>
                  <p className="text-sm text-green-700 mt-1">
                    Your phone number has been registered. Now configure the webhook URLs in your Twilio Console.
                  </p>
                </div>
              </div>
            </div>

            {/* Webhook URLs */}
            {webhookConfig && (
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    Incoming Webhook URL
                  </label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="text"
                      value={webhookConfig.incomingUrl}
                      readOnly
                      className="bg-slate-50 border-slate-300 text-slate-600 cursor-not-allowed font-mono text-xs"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(webhookConfig.incomingUrl, 'incoming')}
                      className="border-slate-300"
                    >
                      {copiedField === 'incoming' ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Set this as "A CALL COMES IN" webhook in Twilio Console
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">
                    Status Callback URL
                  </label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="text"
                      value={webhookConfig.statusCallbackUrl}
                      readOnly
                      className="bg-slate-50 border-slate-300 text-slate-600 cursor-not-allowed font-mono text-xs"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(webhookConfig.statusCallbackUrl, 'status')}
                      className="border-slate-300"
                    >
                      {copiedField === 'status' ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Set this as "STATUS CALLBACK URL" in Twilio Console
                  </p>
                </div>

                {/* Instructions */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm font-medium text-blue-900 mb-2">
                    Configuration Steps:
                  </p>
                  <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
                    {webhookConfig.steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ol>
                </div>
              </div>
            )}

            {/* Close Button */}
            <div className="flex justify-end pt-4 border-t border-slate-200">
              <Button
                type="button"
                onClick={() => {
                  onOpenChange(false)
                  setSuccess(false)
                }}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg"
              >
                Done
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

