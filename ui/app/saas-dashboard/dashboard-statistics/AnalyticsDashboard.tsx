'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Phone, Clock, TrendingUp, Activity, Calendar, BarChart3 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import type { CallStatistics, CallsByDate, CallsByAgent } from './types'
import { formatDuration, formatDate } from './utils'
import { fetchCallStatistics, fetchCallsByDate, fetchCallsByAgent } from './api'

// Sample data for demonstration
const sampleStats: CallStatistics = {
  total_calls: 247,
  total_duration_seconds: 18450,
  average_duration_seconds: 74.7,
  min_duration_seconds: 12.3,
  max_duration_seconds: 342.5,
  active_calls: 3,
  completed_calls: 244,
}

const sampleCallsByDate: CallsByDate[] = [
  { date: '2025-11-04', count: 12, total_duration_seconds: 890 },
  { date: '2025-11-05', count: 18, total_duration_seconds: 1340 },
  { date: '2025-11-06', count: 25, total_duration_seconds: 1875 },
  { date: '2025-11-07', count: 32, total_duration_seconds: 2390 },
  { date: '2025-11-08', count: 28, total_duration_seconds: 2090 },
  { date: '2025-11-09', count: 35, total_duration_seconds: 2615 },
  { date: '2025-11-10', count: 42, total_duration_seconds: 3138 },
  { date: '2025-11-11', count: 55, total_duration_seconds: 4112 },
]

const sampleCallsByAgent: CallsByAgent[] = [
  { agent_id: '+1 555 202 2030', call_count: 142, total_duration_seconds: 10615, average_duration_seconds: 74.8 },
  { agent_id: '+1 555 204 0090', call_count: 89, total_duration_seconds: 6645, average_duration_seconds: 74.7 },
  { agent_id: '+1 555 301 4567', call_count: 16, total_duration_seconds: 1190, average_duration_seconds: 74.4 },
]

export function AnalyticsDashboard() {
  const [stats, setStats] = useState<CallStatistics | null>(sampleStats)
  const [callsByDate, setCallsByDate] = useState<CallsByDate[]>(sampleCallsByDate)
  const [callsByAgent, setCallsByAgent] = useState<CallsByAgent[]>(sampleCallsByAgent)
  const [loading, setLoading] = useState(false)
  const [selectedDays, setSelectedDays] = useState(7)
  const [useSampleData, setUseSampleData] = useState(true)

  useEffect(() => {
    fetchAnalytics()
  }, [selectedDays])

  const fetchAnalytics = async () => {
    try {
      setLoading(true)

      // Fetch all analytics data in parallel with error handling and timeout
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Timeout')), 2000)
      )

      const [statsResult, dateResult, agentResult] = await Promise.allSettled([
        Promise.race([fetchCallStatistics(), timeoutPromise]),
        Promise.race([fetchCallsByDate(selectedDays), timeoutPromise]),
        Promise.race([fetchCallsByAgent(), timeoutPromise]),
      ])

      // Process stats response
      if (statsResult.status === 'fulfilled' && !(statsResult.value instanceof Error)) {
        const realStats = statsResult.value as CallStatistics
        if (realStats.total_calls > 0) {
          setStats(realStats)
          setUseSampleData(false)
        } else {
          setStats(sampleStats)
          setUseSampleData(true)
        }
      } else {
        setStats(sampleStats)
        setUseSampleData(true)
      }

      // Process date response
      if (dateResult.status === 'fulfilled' && !(dateResult.value instanceof Error)) {
        const realDateData = dateResult.value as CallsByDate[]
        if (realDateData.length > 0) {
          setCallsByDate(realDateData)
        } else {
          setCallsByDate(sampleCallsByDate)
        }
      } else {
        setCallsByDate(sampleCallsByDate)
      }

      // Process agent response
      if (agentResult.status === 'fulfilled' && !(agentResult.value instanceof Error)) {
        const realAgentData = agentResult.value as CallsByAgent[]
        if (realAgentData.length > 0) {
          setCallsByAgent(realAgentData)
        } else {
          setCallsByAgent(sampleCallsByAgent)
        }
      } else {
        setCallsByAgent(sampleCallsByAgent)
      }
    } catch (error) {
      console.error('Error fetching analytics:', error)
      // Use sample data on error
      setStats(sampleStats)
      setCallsByDate(sampleCallsByDate)
      setCallsByAgent(sampleCallsByAgent)
      setUseSampleData(true)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-600">Loading analytics...</div>
      </div>
    )
  }

  // Ensure stats is always set (use sample data if no real data)
  const displayStats = stats || sampleStats
  const displayCallsByDate = callsByDate.length > 0 ? callsByDate : sampleCallsByDate
  const displayCallsByAgent = callsByAgent.length > 0 ? callsByAgent : sampleCallsByAgent

  return (
    <div className="space-y-6">
      {/* Sample Data Indicator */}
      {useSampleData && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-blue-600" />
            <span className="text-sm text-blue-800">Showing sample data for demonstration</span>
          </div>
        </div>
      )}

      {/* Time Range Selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-600">Show data for:</span>
        {[7, 30, 90].map((days) => (
          <button
            key={days}
            onClick={() => setSelectedDays(days)}
            className={`px-3 py-1 text-sm rounded-lg transition-colors ${
              selectedDays === days
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {days} days
          </button>
        ))}
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Total Calls</p>
              <p className="text-3xl font-bold text-slate-900">
                {displayStats.total_calls}
              </p>
            </div>
            <div className="p-3 bg-blue-100 rounded-lg">
              <Phone className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Avg Duration</p>
              <p className="text-3xl font-bold text-slate-900">
                {formatDuration(displayStats.average_duration_seconds)}
              </p>
            </div>
            <div className="p-3 bg-green-100 rounded-lg">
              <Clock className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Max Duration</p>
              <p className="text-3xl font-bold text-slate-900">
                {formatDuration(displayStats.max_duration_seconds)}
              </p>
            </div>
            <div className="p-3 bg-purple-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-purple-600" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 mb-1">Completed</p>
              <p className="text-3xl font-bold text-slate-900">
                {displayStats.completed_calls}
              </p>
            </div>
            <div className="p-3 bg-indigo-100 rounded-lg">
              <Activity className="h-6 w-6 text-indigo-600" />
            </div>
          </div>
        </Card>
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="h-5 w-5 text-slate-600" />
            <h3 className="font-semibold text-slate-900">Duration Stats</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Min Duration:</span>
              <span className="text-sm font-medium text-slate-900">
                {formatDuration(displayStats.min_duration_seconds)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Total Duration:</span>
              <span className="text-sm font-medium text-slate-900">
                {formatDuration(displayStats.total_duration_seconds)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Active Calls:</span>
              <span className="text-sm font-medium text-slate-900">
                {displayStats.active_calls}
              </span>
            </div>
          </div>
        </Card>

        {/* Calls by Date Chart */}
        <Card className="p-6 md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <Calendar className="h-5 w-5 text-slate-600" />
            <h3 className="font-semibold text-slate-900">Calls by Date</h3>
          </div>
          {displayCallsByDate.length > 0 ? (
            <div className="space-y-3">
              {displayCallsByDate.map((item, index) => (
                <div key={index} className="flex items-center gap-4">
                  <div className="w-20 text-sm text-slate-600">
                    {formatDate(item.date)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-slate-200 rounded-full h-2">
                        <div
                          className="bg-indigo-600 h-2 rounded-full"
                          style={{
                            width: `${
                              (item.count / Math.max(...displayCallsByDate.map((d) => d.count), 1)) * 100
                            }%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium text-slate-900 w-12 text-right">
                        {item.count}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Calendar className="h-8 w-8 text-slate-400 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No calls data available for this period</p>
            </div>
          )}
        </Card>
      </div>

      {/* Calls by Agent */}
      {displayCallsByAgent.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <BarChart3 className="h-5 w-5 text-slate-600" />
            <h3 className="font-semibold text-slate-900">Calls by Agent</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-4 text-sm font-semibold text-slate-700">
                    Agent ID
                  </th>
                  <th className="text-right py-2 px-4 text-sm font-semibold text-slate-700">
                    Calls
                  </th>
                  <th className="text-right py-2 px-4 text-sm font-semibold text-slate-700">
                    Avg Duration
                  </th>
                  <th className="text-right py-2 px-4 text-sm font-semibold text-slate-700">
                    Total Duration
                  </th>
                </tr>
              </thead>
              <tbody>
                {displayCallsByAgent.map((agent, index) => (
                  <tr key={index} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4 text-sm text-slate-900">
                      {agent.agent_id || 'Unknown'}
                    </td>
                    <td className="py-3 px-4 text-sm text-right font-medium text-slate-900">
                      {agent.call_count}
                    </td>
                    <td className="py-3 px-4 text-sm text-right text-slate-700">
                      {formatDuration(agent.average_duration_seconds)}
                    </td>
                    <td className="py-3 px-4 text-sm text-right text-slate-700">
                      {formatDuration(agent.total_duration_seconds)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

