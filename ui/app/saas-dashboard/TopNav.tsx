'use client'

import { Bell, User, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface TopNavProps {
  activeTab: string
  onTabChange: (tab: string) => void
  onCreateAgent: () => void
  activeSection?: string
}

const tabs = [
  'AI Agents',
]

export function TopNav({ activeTab, onTabChange, onCreateAgent, activeSection }: TopNavProps) {
  const showCreateAgent = activeSection !== 'dashboard'
  
  return (
    <div className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
      <div className="flex items-center justify-between px-6 h-16">
        {/* Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {tabs.map((tab) => {
            const isActive = activeTab === tab
            return (
              <button
                key={tab}
                onClick={() => onTabChange(tab)}
                className={cn(
                  "px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap",
                  isActive
                    ? "text-indigo-600 border-b-2 border-indigo-600"
                    : "text-slate-600 hover:text-slate-900"
                )}
              >
                {tab}
              </button>
            )
          })}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {showCreateAgent && (
            <Button
              onClick={onCreateAgent}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg shadow-blue-500/50"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Agent
            </Button>
          )}
          
          <button className="p-2 rounded-lg hover:bg-slate-100 transition-colors">
            <Bell className="h-5 w-5 text-slate-600" />
          </button>
          
          <button className="p-2 rounded-lg hover:bg-slate-100 transition-colors">
            <User className="h-5 w-5 text-slate-600" />
          </button>
        </div>
      </div>
    </div>
  )
}

