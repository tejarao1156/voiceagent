'use client'

import { motion } from 'framer-motion'
import { Plus, Phone } from 'lucide-react'
import { useAppStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import { Button } from './ui/button'
import { ThemeToggle } from './ThemeToggle'

interface SidebarProps {
  onAddNumber: () => void
}

export function Sidebar({ onAddNumber }: SidebarProps) {
  const { phoneNumbers, selectedPhoneNumberId, selectPhoneNumber, calls } = useAppStore()

  return (
    <motion.div
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="fixed left-0 top-0 h-full w-72 border-r border-slate-800/50 bg-gradient-to-b from-slate-900/95 via-slate-900/90 to-slate-900/95 backdrop-blur-xl z-10"
    >
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-6 border-b border-slate-800/50">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              DoDash Voice
            </h1>
            <ThemeToggle />
          </div>
          <p className="text-xs text-slate-400">IVR Voice Agent Platform</p>
        </div>

        {/* Add Number Button */}
        <div className="p-4">
          <Button
            onClick={onAddNumber}
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-lg shadow-blue-500/30"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add New Number
          </Button>
        </div>

        {/* Numbers List */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <div className="space-y-2">
            {phoneNumbers.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                <Phone className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No numbers onboarded yet</p>
              </div>
            ) : (
              phoneNumbers.map((number) => {
                const isSelected = selectedPhoneNumberId === number.id
                const numberCalls = calls[number.id] || []
                const hasOngoingCall = numberCalls.some(
                  (call) => call.status === 'ongoing'
                )

                return (
                  <motion.button
                    key={number.id}
                    onClick={() => selectPhoneNumber(number.id)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={cn(
                      "w-full text-left p-3 rounded-lg border transition-all duration-200",
                      isSelected
                        ? "bg-gradient-to-r from-blue-500/20 to-purple-500/20 border-blue-500/50 shadow-lg shadow-blue-500/20"
                        : "bg-slate-800/30 border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/50"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {hasOngoingCall && (
                            <motion.div
                              animate={{ scale: [1, 1.2, 1] }}
                              transition={{ repeat: Infinity, duration: 2 }}
                              className="h-2 w-2 rounded-full bg-green-400 shadow-lg shadow-green-400/50"
                            />
                          )}
                          <span className="text-sm font-medium text-slate-200 truncate">
                            {number.name || number.number}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 truncate">{number.number}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-2">
                        <div
                          className={cn(
                            "h-2 w-2 rounded-full",
                            number.status === 'active'
                              ? "bg-green-400 shadow-lg shadow-green-400/50"
                              : "bg-red-400 shadow-lg shadow-red-400/50"
                          )}
                        />
                      </div>
                    </div>
                  </motion.button>
                )
              })
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

