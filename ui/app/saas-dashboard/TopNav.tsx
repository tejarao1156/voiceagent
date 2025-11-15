'use client'

import { Bell, User, Plus, Phone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface TopNavProps {
  activeTab: string
  onTabChange: (tab: string) => void
  onCreateAgent: () => void
  onRegisterPhone: () => void
  activeSection?: string
}

export function TopNav({ activeTab, onTabChange, onCreateAgent, onRegisterPhone, activeSection }: TopNavProps) {
  // Show "Create Agent" for incoming section
  const showCreateAgent = activeSection === 'incoming-agent'
  // Show "Register Phone Number" only for incoming section
  const showRegisterPhone = activeSection === 'incoming-agent'
  
  return (
    <div className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
      <div className="flex items-center justify-between px-6 h-16">
        {/* Left side - empty for now */}
        <div></div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {showCreateAgent && (
            <>
              <Button
                onClick={onCreateAgent}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg shadow-blue-500/50"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Agent
              </Button>
              <Button
                onClick={onRegisterPhone}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white shadow-lg shadow-blue-500/50"
              >
                <Phone className="h-4 w-4 mr-2" />
                Register Phone Number
              </Button>
            </>
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

