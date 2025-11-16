'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowDownLeft,
  MoreVertical,
  Edit,
  Trash2,
  Link as LinkIcon,
  ShoppingCart,
  Copy,
  Bot
} from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface Agent {
  id: string
  name: string
  direction: 'incoming' | 'outgoing' | 'messaging'
  phoneNumber: string
  lastUpdated: string
  status: 'active' | 'idle' | 'upgraded'
  active?: boolean
  phoneIsDeleted?: boolean  // True if the associated phone number is deleted
  // Configuration fields
  sttModel?: string
  inferenceModel?: string
  ttsModel?: string
  ttsVoice?: string
  systemPrompt?: string
  greeting?: string
  temperature?: number
  maxTokens?: number
  twilioAccountSid?: string
  twilioAuthToken?: string
}

interface AgentTableProps {
  agents: Agent[]
  onEdit: (agent: Agent) => void
  onDelete: (agent: Agent) => void
  onToggleActive?: (agent: Agent, active: boolean) => void
}

export function AgentTable({
  agents,
  onEdit,
  onDelete,
  onToggleActive,
}: AgentTableProps) {
  const getStatusVariant = (status: Agent['status']) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'upgraded':
        return 'success' // Green for upgraded
      case 'idle':
        return 'secondary'
      default:
        return 'secondary'
    }
  }
  
  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'upgraded':
        return 'bg-green-500'
      case 'active':
        return 'bg-green-500'
      default:
        return 'bg-slate-500'
    }
  }

  if (agents.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm p-12">
        <div className="text-center">
          <Bot className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No agents yet</h3>
          <p className="text-sm text-slate-600 mb-6">
            Get started by creating your first AI agent
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="border-b border-slate-200 bg-slate-50/50">
            <TableHead className="font-semibold text-slate-800">Agent Name</TableHead>
            <TableHead className="font-semibold text-slate-800">Direction</TableHead>
            <TableHead className="font-semibold text-slate-800">Phone Numbers/Number Pools</TableHead>
            <TableHead className="font-semibold text-slate-800">Active</TableHead>
            <TableHead className="font-semibold text-slate-800">Last</TableHead>
            <TableHead className="font-semibold text-slate-800 w-[100px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {agents.map((agent, index) => (
            <motion.tr
              key={agent.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
            >
              <TableCell>
                <div className="flex items-center gap-3">
                  <div className="flex flex-col gap-1.5">
                    <span className="font-medium text-slate-900">{agent.name}</span>
                    <span className={cn(
                      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold w-fit",
                      getStatusColor(agent.status),
                      "text-white"
                    )}>
                      {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
                    </span>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <ArrowDownLeft className="h-4 w-4 text-green-600" />
                  <span className="text-slate-700 capitalize">incoming</span>
                </div>
              </TableCell>
              <TableCell className="text-slate-700 font-mono text-sm">
                {agent.phoneNumber}
              </TableCell>
              <TableCell>
                <label className={cn(
                  "relative inline-flex items-center",
                  agent.phoneIsDeleted ? "cursor-not-allowed opacity-60" : "cursor-pointer"
                )}>
                  <input
                    type="checkbox"
                    checked={agent.active ?? false}
                    onChange={(e) => {
                      e.stopPropagation()
                      if (onToggleActive && !agent.phoneIsDeleted) {
                        onToggleActive(agent, e.target.checked)
                      }
                    }}
                    disabled={agent.phoneIsDeleted}
                    className="sr-only peer disabled:cursor-not-allowed"
                  />
                  <div className={cn(
                    "w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600",
                    agent.phoneIsDeleted && "opacity-50 cursor-not-allowed"
                  )}></div>
                  <span className={cn(
                    "ml-3 text-sm font-medium",
                    agent.phoneIsDeleted ? "text-slate-500" : "text-slate-700"
                  )}>
                    {agent.active ? 'Active' : 'Inactive'}
                    {agent.phoneIsDeleted && ' (Phone Deleted)'}
                  </span>
                </label>
              </TableCell>
              <TableCell className="text-slate-600 text-sm">
                {agent.lastUpdated}
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="p-1 rounded hover:bg-slate-100 transition-colors">
                      <MoreVertical className="h-4 w-4 text-slate-600" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuItem 
                      onClick={() => onEdit(agent)}
                    >
                      <Edit className="h-4 w-4 mr-2" />
                      Edit
                      {agent.phoneIsDeleted && " (View Only)"}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => onDelete(agent)}
                      className="text-red-600 focus:text-red-600"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </motion.tr>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

