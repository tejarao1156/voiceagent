'use client'

import {
  LayoutDashboard,
  Bot,
  Phone,
  Volume2,
  Link as LinkIcon,
  FileText,
  Settings,
  ArrowUp
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarItem {
  id: string
  label: string
  icon: React.ReactNode
}

const sidebarItems: SidebarItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="h-5 w-5" /> },
  { id: 'ai-agents', label: 'AI Agents', icon: <Bot className="h-5 w-5" /> },
  { id: 'calls', label: 'Calls', icon: <Phone className="h-5 w-5" /> },
  { id: 'voice-customization', label: 'Voice Customization', icon: <Volume2 className="h-5 w-5" /> },
  { id: 'endpoints', label: 'Endpoints', icon: <LinkIcon className="h-5 w-5" /> },
  { id: 'activity-logs', label: 'Activity Logs', icon: <FileText className="h-5 w-5" /> },
  { id: 'settings', label: 'Settings', icon: <Settings className="h-5 w-5" /> },
]

interface SidebarProps {
  activeSection: string
  onSectionChange: (section: string) => void
}

export function Sidebar({ activeSection, onSectionChange }: SidebarProps) {
  return (
    <div className="fixed left-0 top-0 h-screen w-60 bg-[#0F172A] text-white flex flex-col z-50">
      {/* Logo */}
      <div className="p-6 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <ArrowUp className="h-4 w-4 text-orange-500" />
            <ArrowUp className="h-4 w-4 text-green-500" />
          </div>
          <span className="text-xl font-semibold">GHL</span>
        </div>
      </div>

      {/* Menu Items */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {sidebarItems.map((item) => {
          const isActive = activeSection === item.id
          return (
            <button
              key={item.id}
              onClick={() => {
                onSectionChange(item.id)
                if (typeof window !== 'undefined') {
                  window.location.hash = item.id
                }
              }}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all",
                "hover:bg-slate-700/40 hover:text-white",
                isActive
                  ? "bg-slate-700/60 text-white border-l-4 border-indigo-500"
                  : "text-slate-300"
              )}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-700/50">
        <div className="text-xs text-slate-400 text-center">
          Version 1.0.0
        </div>
      </div>
    </div>
  )
}

