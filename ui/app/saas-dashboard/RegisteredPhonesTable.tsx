'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  MoreVertical,
  Copy,
  Check,
  Phone,
  Link as LinkIcon,
  Eye,
  EyeOff,
  Trash2
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
import { type RegisteredPhone } from '@/lib/api'

interface RegisteredPhonesTableProps {
  phones: RegisteredPhone[]
  onCopy?: (text: string, field: string) => void
  onDelete?: (phone: RegisteredPhone) => void
}

export function RegisteredPhonesTable({
  phones,
  onCopy,
  onDelete,
}: RegisteredPhonesTableProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [showAccountSid, setShowAccountSid] = useState<Record<string, boolean>>({})

  const handleCopy = async (text: string, field: string, phoneId: string) => {
    try {
      if (!text) {
        console.warn(`Cannot copy empty ${field} for phone ${phoneId}`)
        return
      }
      await navigator.clipboard.writeText(text)
      setCopiedField(`${phoneId}-${field}`)
      setTimeout(() => setCopiedField(null), 2000)
      if (onCopy) {
        onCopy(text, field)
      }
    } catch (error) {
      console.error(`Failed to copy ${field} to clipboard:`, error)
      // Could show a toast notification here in the future
    }
  }

  const toggleShowAccountSid = (phoneId: string) => {
    setShowAccountSid(prev => ({
      ...prev,
      [phoneId]: !prev[phoneId]
    }))
  }

  const formatDate = (dateString: string) => {
    try {
      if (!dateString) return 'Unknown'
      const date = new Date(dateString)
      if (isNaN(date.getTime())) {
        console.warn(`Invalid date string: ${dateString}`)
        return dateString
      }
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }) + ' ' + date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
    } catch (e) {
      console.error(`Error formatting date ${dateString}:`, e)
      return dateString || 'Unknown'
    }
  }

  const maskAccountSid = (sid: string) => {
    if (!sid || typeof sid !== 'string') return ''
    if (sid.length <= 8) return sid
    return sid.substring(0, 4) + '•'.repeat(sid.length - 8) + sid.substring(sid.length - 4)
  }

  if (!phones || phones.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm p-12">
        <div className="text-center">
          <Phone className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No registered phone numbers</h3>
          <p className="text-sm text-slate-600 mb-6">
            Register a phone number to get started with creating agents
          </p>
          <p className="text-xs text-slate-500 mt-4">
            Check the browser console for debugging information
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
            <TableHead className="font-semibold text-slate-800">Phone Number</TableHead>
            <TableHead className="font-semibold text-slate-800">Twilio Account SID</TableHead>
            <TableHead className="font-semibold text-slate-800">Status</TableHead>
            <TableHead className="font-semibold text-slate-800">User ID</TableHead>
            <TableHead className="font-semibold text-slate-800">Webhook URLs</TableHead>
            <TableHead className="font-semibold text-slate-800">Created</TableHead>
            <TableHead className="font-semibold text-slate-800">Updated</TableHead>
            <TableHead className="font-semibold text-slate-800 w-[100px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {phones.map((phone, index) => (
            <motion.tr
              key={phone.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
            >
              <TableCell>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-indigo-600" />
                    <span className="font-medium text-slate-900 font-mono text-sm">
                      {phone.phoneNumber || 'N/A'}
                    </span>
                  </div>
                  {phone.originalPhoneNumber && phone.originalPhoneNumber !== phone.phoneNumber && (
                    <span className="text-xs text-slate-500 italic ml-6">
                      Original: {phone.originalPhoneNumber}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-slate-700">
                    {phone.twilioAccountSid 
                      ? (showAccountSid[phone.id] 
                          ? phone.twilioAccountSid 
                          : maskAccountSid(phone.twilioAccountSid))
                      : 'N/A'}
                  </span>
                  {phone.twilioAccountSid && (
                    <button
                      onClick={() => toggleShowAccountSid(phone.id)}
                      className="p-1 rounded hover:bg-slate-100 transition-colors"
                      title={showAccountSid[phone.id] ? 'Hide' : 'Show'}
                    >
                      {showAccountSid[phone.id] ? (
                        <EyeOff className="h-3 w-3 text-slate-500" />
                      ) : (
                        <Eye className="h-3 w-3 text-slate-500" />
                      )}
                    </button>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <Badge 
                  variant={phone.isActive !== false ? 'success' : 'secondary'}
                  className={cn(
                    phone.isActive !== false 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-slate-100 text-slate-800'
                  )}
                >
                  {phone.isActive !== false ? 'Active' : 'Inactive'}
                </Badge>
              </TableCell>
              <TableCell className="text-slate-600 text-sm">
                {phone.userId || (
                  <span className="text-slate-400 italic">No user ID</span>
                )}
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-slate-500">Incoming:</span>
                    <span className="font-mono text-xs text-slate-700 truncate max-w-[200px]">
                      {phone.webhookUrl || 'N/A'}
                    </span>
                    {phone.webhookUrl && (
                      <button
                        onClick={() => handleCopy(phone.webhookUrl, 'incoming', phone.id)}
                        className="p-1 rounded hover:bg-slate-100 transition-colors"
                        title="Copy incoming webhook URL"
                      >
                        {copiedField === `${phone.id}-incoming` ? (
                          <Check className="h-3 w-3 text-green-600" />
                        ) : (
                          <Copy className="h-3 w-3 text-slate-500" />
                        )}
                      </button>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-slate-500">Status:</span>
                    <span className="font-mono text-xs text-slate-700 truncate max-w-[200px]">
                      {phone.statusCallbackUrl || 'N/A'}
                    </span>
                    {phone.statusCallbackUrl && (
                      <button
                        onClick={() => handleCopy(phone.statusCallbackUrl, 'status', phone.id)}
                        className="p-1 rounded hover:bg-slate-100 transition-colors"
                        title="Copy status callback URL"
                      >
                        {copiedField === `${phone.id}-status` ? (
                          <Check className="h-3 w-3 text-green-600" />
                        ) : (
                          <Copy className="h-3 w-3 text-slate-500" />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </TableCell>
              <TableCell className="text-slate-600 text-sm">
                {phone.created_at ? formatDate(phone.created_at) : 'Unknown'}
              </TableCell>
              <TableCell className="text-slate-600 text-sm">
                {phone.updated_at ? formatDate(phone.updated_at) : (
                  phone.created_at ? formatDate(phone.created_at) : 'Unknown'
                )}
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
                      onClick={() => handleCopy(phone.phoneNumber, 'phone', phone.id)}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy Phone Number
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleCopy(phone.twilioAccountSid, 'accountSid', phone.id)}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy Account SID
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleCopy(phone.webhookUrl, 'webhook', phone.id)}
                    >
                      <LinkIcon className="h-4 w-4 mr-2" />
                      Copy Webhook URL
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleCopy(phone.statusCallbackUrl, 'statusCallback', phone.id)}
                    >
                      <LinkIcon className="h-4 w-4 mr-2" />
                      Copy Status Callback URL
                    </DropdownMenuItem>
                    {onDelete && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => onDelete(phone)}
                          className="text-red-600 focus:text-red-600"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </>
                    )}
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

