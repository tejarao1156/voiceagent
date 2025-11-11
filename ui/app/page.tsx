'use client'

import { useState } from 'react'
import { LayoutDashboard, Mic } from 'lucide-react'
import { Tabs } from '@/components/Tabs'
import { Sidebar } from '@/components/Sidebar'
import { Onboarding } from '@/components/Onboarding'
import DashboardContent from './dashboard/DashboardContent'
import VoiceAgentContent from './voice-agent/VoiceAgentContent'

type TabId = 'dashboard' | 'voice-agent'

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')
  const [onboardingOpen, setOnboardingOpen] = useState(false)

  const tabs = [
    {
      id: 'dashboard' as TabId,
      label: 'Dashboard',
      icon: <LayoutDashboard className="h-4 w-4" />,
    },
    {
      id: 'voice-agent' as TabId,
      label: 'Voice Agent',
      icon: <Mic className="h-4 w-4" />,
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 text-white">
      <Sidebar onAddNumber={() => setOnboardingOpen(true)} />
      
      <div className="ml-72 flex flex-col h-screen">
        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
        
        <div className="flex-1 overflow-auto">
          {activeTab === 'dashboard' && (
            <DashboardContent onAddNumber={() => setOnboardingOpen(true)} />
          )}
          {activeTab === 'voice-agent' && <VoiceAgentContent />}
        </div>
      </div>

      <Onboarding open={onboardingOpen} onOpenChange={setOnboardingOpen} />
    </div>
  )
}
