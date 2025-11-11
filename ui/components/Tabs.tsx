'use client'

import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface Tab {
  id: string
  label: string
  icon?: React.ReactNode
}

interface TabsProps {
  tabs: Tab[]
  activeTab: string
  onTabChange: (tabId: string) => void
}

export function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  const activeIndex = tabs.findIndex((tab) => tab.id === activeTab)

  return (
    <div className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm">
      <div className="flex space-x-1 px-4">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                "relative px-6 py-3 text-sm font-medium transition-colors",
                isActive
                  ? "text-slate-100"
                  : "text-slate-400 hover:text-slate-300"
              )}
            >
              <div className="flex items-center gap-2">
                {tab.icon}
                {tab.label}
              </div>
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-600"
                  initial={false}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

