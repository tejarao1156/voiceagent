/**
 * API functions for fetching dashboard statistics
 */

import type { CallStatistics, CallsByDate, CallsByAgent, RecentCall } from './types'

// Use relative URLs so requests go through FastAPI proxy on port 4002
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''

/**
 * Fetch call statistics
 */
export async function fetchCallStatistics(
  agentId?: string,
  startDate?: string,
  endDate?: string
): Promise<CallStatistics> {
  const params = new URLSearchParams()
  if (agentId) params.append('agent_id', agentId)
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)

  const url = `${API_BASE_URL}/analytics/call-statistics${params.toString() ? `?${params.toString()}` : ''}`
  const response = await fetch(url)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch call statistics: ${response.statusText}`)
  }
  
  return response.json()
}

/**
 * Fetch calls grouped by date
 */
export async function fetchCallsByDate(
  days: number = 7,
  agentId?: string
): Promise<CallsByDate[]> {
  const params = new URLSearchParams()
  params.append('days', days.toString())
  if (agentId) params.append('agent_id', agentId)

  const url = `${API_BASE_URL}/analytics/calls-by-date?${params.toString()}`
  const response = await fetch(url)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch calls by date: ${response.statusText}`)
  }
  
  const data = await response.json()
  return data.data || []
}

/**
 * Fetch calls grouped by agent
 */
export async function fetchCallsByAgent(): Promise<CallsByAgent[]> {
  const url = `${API_BASE_URL}/analytics/calls-by-agent`
  const response = await fetch(url)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch calls by agent: ${response.statusText}`)
  }
  
  const data = await response.json()
  return data.data || []
}

/**
 * Fetch recent calls
 */
export async function fetchRecentCalls(limit: number = 10): Promise<RecentCall[]> {
  const url = `${API_BASE_URL}/analytics/recent-calls?limit=${limit}`
  const response = await fetch(url)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch recent calls: ${response.statusText}`)
  }
  
  const data = await response.json()
  return data.data || []
}

