'use client'

import { motion } from 'framer-motion'
import { User, Bot } from 'lucide-react'
import { ConversationMessage } from '@/lib/store'
import { cn } from '@/lib/utils'

interface ConversationProps {
  messages: ConversationMessage[]
  isLive?: boolean
}

export function Conversation({ messages, isLive = false }: ConversationProps) {
  if (!messages || messages.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500 text-sm">
        <p>{isLive ? 'Waiting for conversation...' : 'No conversation data available'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4">
      {messages.map((message, index) => {
        const isUser = message.role === 'user'
        const isLastMessage = index === messages.length - 1
        
        return (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className={cn(
              "flex gap-3",
              isUser ? "justify-start" : "justify-end"
            )}
          >
            {isUser && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                <User className="h-4 w-4 text-slate-300" />
              </div>
            )}
            
            <div
              className={cn(
                "max-w-[80%] rounded-2xl px-4 py-3 shadow-lg",
                isUser
                  ? "bg-slate-800/50 text-slate-100 border border-slate-700/50"
                  : "bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-slate-100 border border-blue-500/30",
                isLive && isLastMessage && "ring-2 ring-green-400/50"
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-slate-400">
                  {isUser ? '🧑 User' : '🤖 AI'}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(message.timestamp as string | Date).toLocaleTimeString()}
                </span>
                {isLive && isLastMessage && (
                  <span className="text-xs text-green-400 animate-pulse">● Live</span>
                )}
              </div>
              <p className="text-sm leading-relaxed">{message.text}</p>
            </div>

            {!isUser && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center">
                <Bot className="h-4 w-4 text-white" />
              </div>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}

