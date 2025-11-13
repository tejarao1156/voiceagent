'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Phone, Clock, Search } from 'lucide-react'
import { CallList } from '@/components/CallList'
import { Call } from '@/lib/store'
import { fetchCalls } from '@/lib/api'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export function CallsSection() {
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'ongoing' | 'finished'>('all')
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  // Load calls from API
  const loadCalls = async () => {
    try {
      setLoading(true)
      const fetchedCalls = await fetchCalls(selectedAgent || undefined)
      
      // Transform API response to match Call interface
      const transformedCalls: Call[] = fetchedCalls.map((call: any) => ({
        id: call.id || call.call_sid,
        phoneNumberId: call.agent_id || call.to_number,
        callerNumber: call.from_number || call.callerNumber,
        status: call.status === 'ongoing' ? 'ongoing' : 'finished',
        timestamp: call.timestamp || call.start_time,
        duration: call.duration,
        conversation: call.conversation || []
      }))
      
      setCalls(transformedCalls)
    } catch (error) {
      console.error('Error fetching calls:', error)
      setCalls([])
    } finally {
      setLoading(false)
    }
  }

  // Load calls on mount and poll for updates
  useEffect(() => {
    loadCalls()
    
    // Poll for updates every 5 seconds
    const interval = setInterval(loadCalls, 5000)
    return () => clearInterval(interval)
  }, [selectedAgent])

  // Filter calls based on search and status
  const filteredCalls = useMemo(() => {
    let filtered = calls

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter(call => call.status === statusFilter)
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (call) =>
          call.callerNumber.toLowerCase().includes(query) ||
          call.conversation?.some((msg) => msg.text.toLowerCase().includes(query))
      )
    }

    return filtered
  }, [calls, statusFilter, searchQuery])

  // Calculate stats
  const stats = useMemo(() => {
    const totalCalls = calls.length
    const ongoingCalls = calls.filter(call => call.status === 'ongoing').length
    const finishedCalls = calls.filter(call => call.status === 'finished').length
    const totalDuration = calls.reduce((sum, call) => sum + (call.duration || 0), 0)
    const avgDuration = totalCalls > 0 ? totalDuration / totalCalls : 0

    return {
      totalCalls,
      ongoingCalls,
      finishedCalls,
      avgDuration
    }
  }, [calls])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">
          Calls
        </h1>
        <p className="text-slate-600">
          View and manage all phone calls with real-time transcripts.
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Total Calls</p>
              <p className="text-2xl font-semibold text-slate-900">{stats.totalCalls}</p>
            </div>
            <Phone className="h-8 w-8 text-slate-400" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Ongoing</p>
              <p className="text-2xl font-semibold text-green-600">{stats.ongoingCalls}</p>
            </div>
            <div className="h-3 w-3 rounded-full bg-green-400 animate-pulse" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Completed</p>
              <p className="text-2xl font-semibold text-slate-900">{stats.finishedCalls}</p>
            </div>
            <Clock className="h-8 w-8 text-slate-400" />
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Avg Duration</p>
              <p className="text-2xl font-semibold text-slate-900">
                {formatDuration(stats.avgDuration)}
              </p>
            </div>
            <Clock className="h-8 w-8 text-slate-400" />
          </div>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Search calls by number or conversation..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Status Filter */}
          <div className="flex gap-2">
            <button
              onClick={() => setStatusFilter('all')}
              className={cn(
                "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
                statusFilter === 'all'
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              )}
            >
              All
            </button>
            <button
              onClick={() => setStatusFilter('ongoing')}
              className={cn(
                "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
                statusFilter === 'ongoing'
                  ? "bg-green-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              )}
            >
              Ongoing
            </button>
            <button
              onClick={() => setStatusFilter('finished')}
              className={cn(
                "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
                statusFilter === 'finished'
                  ? "bg-slate-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              )}
            >
              Finished
            </button>
          </div>
        </div>
      </Card>

      {/* Calls List */}
      <Card className="p-6">
        {loading ? (
          <div className="text-center py-12 text-slate-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p>Loading calls...</p>
          </div>
        ) : (
          <CallList
            calls={filteredCalls}
            onCallUpdate={(callId, updates) => {
              setCalls(prevCalls =>
                prevCalls.map(call =>
                  call.id === callId ? { ...call, ...updates } : call
                )
              )
            }}
          />
        )}
      </Card>
    </div>
  )
}

