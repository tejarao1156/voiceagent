'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, ArrowRight, ArrowLeft, Phone, Radio, CheckCircle2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Card, CardContent } from './ui/card'
import { useAppStore, PhoneNumber } from '@/lib/store'

interface OnboardingProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Step = 1 | 2 | 3 | 4

export function Onboarding({ open, onOpenChange }: OnboardingProps) {
  const [step, setStep] = useState<Step>(1)
  const [phoneNumber, setPhoneNumber] = useState('')
  const [provider, setProvider] = useState<'twilio' | 'plivo' | 'vonage' | 'custom'>('twilio')
  const [stepsCompleted, setStepsCompleted] = useState(false)
  const { addPhoneNumber, selectPhoneNumber } = useAppStore()

  const formatPhoneNumber = (value: string) => {
    const cleaned = value.replace(/\D/g, '')
    if (cleaned.length <= 10) {
      return cleaned.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3')
    }
    return cleaned.replace(/(\d{1})(\d{3})(\d{3})(\d{4})/, '+$1 ($2) $3-$4')
  }

  const validatePhoneNumber = (num: string) => {
    const cleaned = num.replace(/\D/g, '')
    return cleaned.length >= 10
  }

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value)
    setPhoneNumber(formatted)
  }

  const handleNext = () => {
    if (step === 1 && validatePhoneNumber(phoneNumber)) {
      setStep(2)
    } else if (step === 2) {
      if (provider === 'twilio') {
        setStep(3)
      }
    } else if (step === 3 && stepsCompleted) {
      setStep(4)
    }
  }

  const handleBack = () => {
    if (step > 1) {
      setStep((s) => (s - 1) as Step)
    }
  }

  const handleFinish = async () => {
    // Create new phone number entry
    const newNumber: PhoneNumber = {
      id: `phone_${Date.now()}`,
      number: phoneNumber,
      provider,
      status: 'active',
      createdAt: new Date(),
    }

    addPhoneNumber(newNumber)
    selectPhoneNumber(newNumber.id)
    
    // Reset form
    setStep(1)
    setPhoneNumber('')
    setProvider('twilio')
    setStepsCompleted(false)
    onOpenChange(false)
  }

  const handleClose = () => {
    if (step === 4) {
      handleFinish()
    } else {
      onOpenChange(false)
      // Reset on close
      setTimeout(() => {
        setStep(1)
        setPhoneNumber('')
        setProvider('twilio')
        setStepsCompleted(false)
      }, 300)
    }
  }

  const serverUrl = typeof window !== 'undefined' 
    ? `${window.location.protocol}//${window.location.host}`
    : 'https://your-server-url.com'

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Onboard New Phone Number
          </DialogTitle>
          <DialogDescription>
            Follow these steps to connect your phone number
          </DialogDescription>
        </DialogHeader>

        {/* Progress Indicator */}
        <div className="flex items-center justify-between mb-8">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all
                    ${step >= s
                      ? 'bg-gradient-to-r from-blue-500 to-purple-600 border-transparent text-white'
                      : 'border-slate-700 bg-slate-800 text-slate-500'
                    }
                  `}
                >
                  {step > s ? <Check className="h-5 w-5" /> : s}
                </div>
                <span className="text-xs mt-2 text-slate-400">
                  {s === 1 ? 'Number' : s === 2 ? 'Provider' : s === 3 ? 'Setup' : 'Done'}
                </span>
              </div>
              {s < 4 && (
                <div
                  className={`
                    h-1 flex-1 mx-2 transition-all
                    ${step > s ? 'bg-gradient-to-r from-blue-500 to-purple-600' : 'bg-slate-700'}
                  `}
                />
              )}
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1: Enter Number */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              <div>
                <label className="text-sm font-medium text-slate-300 mb-2 block">
                  Phone Number
                </label>
                <Input
                  type="tel"
                  placeholder="+1 (234) 567-8910"
                  value={phoneNumber}
                  onChange={handlePhoneChange}
                  className="text-lg"
                />
                {phoneNumber && !validatePhoneNumber(phoneNumber) && (
                  <p className="text-xs text-red-400 mt-1">
                    Please enter a valid phone number
                  </p>
                )}
              </div>
            </motion.div>
          )}

          {/* Step 2: Select Provider */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-4">
                {(['twilio', 'plivo', 'vonage', 'custom'] as const).map((prov) => (
                  <motion.button
                    key={prov}
                    onClick={() => setProvider(prov)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`
                      p-4 rounded-lg border-2 transition-all text-left
                      ${provider === prov
                        ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20'
                        : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
                      }
                    `}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Radio className="h-5 w-5" />
                      <span className="font-medium text-slate-200 capitalize">
                        {prov === 'custom' ? 'Custom (Coming Soon)' : prov}
                      </span>
                    </div>
                    {provider === prov && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="text-blue-400"
                      >
                        <CheckCircle2 className="h-5 w-5" />
                      </motion.div>
                    )}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 3: Twilio Setup Instructions */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-6">
                    <div className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                        1
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-slate-200 mb-1">
                          Go to Twilio Console → Phone Numbers
                        </h4>
                        <p className="text-sm text-slate-400">
                          Navigate to your Twilio dashboard and select the phone number you want to configure.
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                        2
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-slate-200 mb-1">
                          Select your number
                        </h4>
                        <p className="text-sm text-slate-400">
                          Click on the phone number: <span className="font-mono text-blue-400">{phoneNumber}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                        3
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-slate-200 mb-1">
                          Configure Voice Settings
                        </h4>
                        <div className="mt-2 space-y-2 text-sm">
                          <div className="bg-slate-800/50 p-3 rounded border border-slate-700">
                            <p className="text-slate-300 mb-1">
                              <span className="text-blue-400">A.</span> Inbound Calls URL:
                            </p>
                            <code className="text-xs text-blue-300 break-all">
                              {serverUrl}/api/ivr/inbound
                            </code>
                          </div>
                          <div className="bg-slate-800/50 p-3 rounded border border-slate-700">
                            <p className="text-slate-300 mb-1">
                              <span className="text-blue-400">B.</span> Status Callback URL:
                            </p>
                            <code className="text-xs text-blue-300 break-all">
                              {serverUrl}/api/ivr/status
                            </code>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                        4
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-slate-200 mb-1">
                          Save Changes
                        </h4>
                        <p className="text-sm text-slate-400">
                          Click "Save" to apply the configuration.
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="flex items-center gap-3 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <input
                  type="checkbox"
                  id="steps-completed"
                  checked={stepsCompleted}
                  onChange={(e) => setStepsCompleted(e.target.checked)}
                  className="w-5 h-5 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-2 focus:ring-blue-500"
                />
                <label htmlFor="steps-completed" className="text-sm text-slate-300 cursor-pointer">
                  I've completed these steps
                </label>
              </div>
            </motion.div>
          )}

          {/* Step 4: Success */}
          {step === 4 && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="text-center py-8"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 15 }}
                className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-r from-green-500 to-emerald-500 mb-4 shadow-lg shadow-green-500/50"
              >
                <Check className="h-10 w-10 text-white" />
              </motion.div>
              <motion.h3
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-2xl font-bold text-slate-100 mb-2"
              >
                🎉 Success!
              </motion.h3>
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="text-slate-400 mb-6"
              >
                Your number has been successfully onboarded!
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Navigation Buttons */}
        <div className="flex justify-between gap-4 mt-6">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={step === 1}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          {step < 4 ? (
            <Button
              onClick={handleNext}
              disabled={
                (step === 1 && !validatePhoneNumber(phoneNumber)) ||
                (step === 3 && !stepsCompleted)
              }
              className="flex items-center gap-2"
            >
              Next
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              onClick={handleFinish}
              className="flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
            >
              View Dashboard
              <ArrowRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

