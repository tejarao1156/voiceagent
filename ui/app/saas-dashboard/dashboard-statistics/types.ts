/**
 * Type definitions for dashboard statistics
 */

export interface CallStatistics {
  total_calls: number
  total_duration_seconds: number
  average_duration_seconds: number
  min_duration_seconds: number
  max_duration_seconds: number
  active_calls: number
  completed_calls: number
}

export interface CallsByDate {
  date: string
  count: number
  total_duration_seconds: number
}

export interface CallsByAgent {
  agent_id: string
  call_count: number
  total_duration_seconds: number
  average_duration_seconds: number
}

export interface RecentCall {
  session_id: string
  agent_id: string | null
  customer_id: string | null
  status: string
  message_count: number
  duration_seconds: number
  created_at: string
  updated_at: string
}

