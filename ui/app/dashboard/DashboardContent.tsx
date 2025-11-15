'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { CallList } from '@/components/CallList'
import { SearchBar } from '@/components/SearchBar'
import { useAppStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Phone, Clock, Activity } from 'lucide-react'
import { fetchPhoneNumbers } from '@/lib/api'

interface DashboardContentProps {
  onAddNumber: () => void
}

export default function DashboardContent({ onAddNumber }: DashboardContentProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const {
    phoneNumbers,
    selectedPhoneNumberId,
    calls,
    setPhoneNumbers,
    setCalls,
  } = useAppStore()

  const selectedNumber = phoneNumbers.find((n) => n.id === selectedPhoneNumberId)
  const allCalls = selectedNumber ? calls[selectedNumber.id] || [] : []
  
  // Filter calls based on search query
  const filteredCalls = useMemo(() => {
    if (!searchQuery.trim()) return allCalls
    const query = searchQuery.toLowerCase()
    return allCalls.filter(
      (call) =>
        call.callerNumber.toLowerCase().includes(query) ||
        call.conversation?.some((msg) => msg.text.toLowerCase().includes(query))
    )
  }, [allCalls, searchQuery])
  
  // Calculate stats
  const now = new Date()
  const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000)
  const recentCalls = allCalls.filter(
    (call) => new Date(call.timestamp) >= oneHourAgo
  )
  const ongoingCalls = allCalls.filter((call) => call.status === 'ongoing')
  const totalCalls = allCalls.length

  // Load phone numbers from MongoDB
  useEffect(() => {
    const loadPhoneNumbers = async () => {
      try {
        const phones = await fetchPhoneNumbers()
        setPhoneNumbers(phones)
      } catch (error) {
        console.error('Error loading phone numbers:', error)
      }
    }
    loadPhoneNumbers()
  }, [])

  useEffect(() => {
    const fetchCalls = async () => {
      if (selectedNumber) {
        try {
          const { fetchCalls } = await import('@/lib/api')
          const fetchedCalls = await fetchCalls(selectedNumber.id)
          
          // Transform API response to match Call interface
          const transformedCalls = fetchedCalls.map((call: any) => ({
            id: call.id || call.call_sid,
            phoneNumberId: selectedNumber.id,
            callerNumber: call.from_number || call.callerNumber,
            status: call.status === 'ongoing' ? 'ongoing' : 'finished',
            timestamp: new Date(call.timestamp || call.start_time),
            duration: call.duration,
            conversation: call.conversation || []
          }))
          
          setCalls(selectedNumber.id, transformedCalls)
        } catch (error) {
          console.error('Error fetching calls:', error)
        }
      }
    }
    
    fetchCalls()
    
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchCalls, 5000)
    return () => clearInterval(interval)
  }, [selectedNumber, setCalls])

  return (
    <div className="p-8">
      {!selectedNumber ? (
        // Welcome Screen
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-center min-h-[calc(100vh-8rem)]"
        >
          <Card className="max-w-2xl w-full border-slate-700/50 bg-slate-900/40 backdrop-blur-sm">
            <CardContent className="p-12 text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 15 }}
                className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-r from-blue-500/20 to-purple-500/20 mb-6"
              >
                <Phone className="h-10 w-10 text-blue-400" />
              </motion.div>
              <h1 className="text-3xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Welcome to DoDash Voice Agent 👋
              </h1>
              <p className="text-slate-400 mb-8 text-lg">
                Onboard your first phone number to get started with AI-powered voice interactions.
              </p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onAddNumber}
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 rounded-lg font-medium shadow-lg shadow-blue-500/30 transition-all"
              >
                <Phone className="h-5 w-5" />
                Add Your First Number
              </motion.button>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        // Dashboard View
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-6"
        >
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              {selectedNumber.name || selectedNumber.number}
            </h1>
            <div className="flex items-center gap-4 text-sm text-slate-400">
              <span>{selectedNumber.number}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <div
                  className={`h-2 w-2 rounded-full ${
                    selectedNumber.status === 'active'
                      ? 'bg-green-400 shadow-lg shadow-green-400/50'
                      : 'bg-red-400'
                  }`}
                />
                {selectedNumber.status === 'active' ? 'Active' : 'Disconnected'}
              </span>
              {selectedNumber.lastSync && (
                <>
                  <span>•</span>
                  <span>Last sync: {selectedNumber.lastSync.toLocaleString()}</span>
                </>
              )}
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card className="border-slate-700/50 bg-slate-900/40 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <Activity className="h-4 w-4" />
                    Last Hour
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-slate-100">
                    {recentCalls.length}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">calls</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="border-slate-700/50 bg-slate-900/40 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <Phone className="h-4 w-4" />
                    Total Calls
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-slate-100">
                    {totalCalls}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">all time</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="border-slate-700/50 bg-slate-900/40 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Ongoing
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-400">
                    {ongoingCalls.length}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">active now</p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Recent Calls */}
          <Card className="border-slate-700/50 bg-slate-900/40 backdrop-blur-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-xl">Recent Calls</CardTitle>
                <div className="w-64">
                  <SearchBar
                    value={searchQuery}
                    onChange={setSearchQuery}
                    placeholder="Search calls..."
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <CallList 
                calls={filteredCalls} 
                onCallUpdate={(callId, updates) => {
                  if (selectedNumber) {
                    const updatedCalls = allCalls.map(call => 
                      call.id === callId ? { ...call, ...updates } : call
                    )
                    setCalls(selectedNumber.id, updatedCalls)
                  }
                }}
              />
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  )
}

