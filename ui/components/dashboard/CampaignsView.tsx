'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Megaphone,
  Upload,
  Phone,
  MessageSquare,
  Send,
  Play,
  Pause,
  Trash2,
  Eye,
  Plus,
  X,
  Check,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  FileSpreadsheet,
  Users,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  List,
  Edit,
  Search
} from 'lucide-react'

// Types
interface ContactList {
  id: string
  name: string
  description: string
  contact_count: number
  version: number
  created_at: string
  updated_at: string
}

// Types
interface Campaign {
  id: string
  name: string
  type: 'voice' | 'sms' | 'whatsapp'
  status: 'draft' | 'running' | 'completed' | 'paused'
  config: {
    promptId?: string
    messageBody?: string
    fromNumber?: string
  }
  stats: {
    total: number
    pending: number
    success: number
    failed: number
  }
  created_at: string
}

// Reusable Card component (matches dashboard style)
const GlassCard = ({ children, className = "" }: { children: React.ReactNode, className?: string }) => (
  <div className={`relative overflow-hidden rounded-2xl border border-white/60 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 p-6 backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] ${className}`}>
    {children}
  </div>
)

// Status Badge
const StatusBadge = ({ status }: { status: string }) => {
  const styles: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600',
    running: 'bg-blue-100 text-blue-700 animate-pulse',
    completed: 'bg-emerald-100 text-emerald-700',
    paused: 'bg-yellow-100 text-yellow-700',
    failed: 'bg-red-100 text-red-700'
  }
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase ${styles[status] || styles.draft}`}>
      {status}
    </span>
  )
}

// Type Badge
const TypeBadge = ({ type }: { type: string }) => {
  const icons: Record<string, React.ReactNode> = {
    voice: <Phone className="h-3 w-3" />,
    sms: <MessageSquare className="h-3 w-3" />,
    whatsapp: <Send className="h-3 w-3" />
  }
  const colors: Record<string, string> = {
    voice: 'bg-purple-100 text-purple-700',
    sms: 'bg-cyan-100 text-cyan-700',
    whatsapp: 'bg-green-100 text-green-700'
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-bold ${colors[type]}`}>
      {icons[type]}
      {type.toUpperCase()}
    </span>
  )
}

// Campaign List View
const CampaignList = ({
  campaigns,
  onSelect,
  onStart,
  onPause,
  onDelete,
  loading
}: {
  campaigns: Campaign[]
  onSelect: (c: Campaign) => void
  onStart: (id: string) => void
  onPause: (id: string) => void
  onDelete: (id: string) => void
  loading: boolean
}) => {
  const [filter, setFilter] = useState<'all' | 'voice' | 'sms' | 'whatsapp'>('all')

  const filtered = campaigns.filter(c => filter === 'all' || c.type === filter)

  return (
    <div className="space-y-4">
      {/* Filter Tabs */}
      <div className="flex space-x-2 bg-white p-1 rounded-lg border border-slate-200 w-fit">
        {['all', 'voice', 'sms', 'whatsapp'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f as any)}
            className={`px-4 py-1.5 text-xs font-bold rounded-md capitalize transition-colors ${filter === f ? 'bg-blue-100 text-blue-700' : 'text-slate-500 hover:bg-slate-50'
              }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Campaign Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <Megaphone className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>No campaigns found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Progress</th>
                <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Created</th>
                <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((campaign) => (
                <tr key={campaign.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-800">{campaign.name}</td>
                  <td className="px-4 py-3"><TypeBadge type={campaign.type} /></td>
                  <td className="px-4 py-3"><StatusBadge status={campaign.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all"
                          style={{ width: `${campaign.stats.total ? ((campaign.stats.success + campaign.stats.failed) / campaign.stats.total) * 100 : 0}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500">
                        {campaign.stats.success + campaign.stats.failed}/{campaign.stats.total}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {new Date(campaign.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onSelect(campaign)}
                        className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      {campaign.status === 'draft' || campaign.status === 'paused' ? (
                        <button
                          onClick={() => onStart(campaign.id)}
                          className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                          title="Start"
                        >
                          <Play className="h-4 w-4" />
                        </button>
                      ) : campaign.status === 'running' ? (
                        <button
                          onClick={() => onPause(campaign.id)}
                          className="p-2 text-slate-400 hover:text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                          title="Pause"
                        >
                          <Pause className="h-4 w-4" />
                        </button>
                      ) : null}
                      <button
                        onClick={() => onDelete(campaign.id)}
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const CampaignWizard = ({
  onClose,
  onCreated,
  prompts,
  phoneNumbers: registeredPhones,
  contactLists
}: {
  onClose: () => void
  onCreated: () => void
  prompts: any[]
  phoneNumbers: any[]
  contactLists: ContactList[]
}) => {
  const [step, setStep] = useState(1)
  const [file, setFile] = useState<File | null>(null)
  const [uploadedNumbers, setUploadedNumbers] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [useExistingList, setUseExistingList] = useState(false)
  const [selectedListId, setSelectedListId] = useState('')

  const [formData, setFormData] = useState({
    name: '',
    type: 'sms' as 'voice' | 'sms' | 'whatsapp',
    promptId: '',
    messageBody: '',
    fromNumber: ''
  })

  const [creating, setCreating] = useState(false)

  const selectedList = contactLists.find(l => l.id === selectedListId)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return

    setFile(f)
    setUploading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', f)

      const res = await fetch('/api/campaigns/upload', {
        method: 'POST',
        body: formData
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')

      setUploadedNumbers(data.phone_numbers || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleCreate = async () => {
    setCreating(true)
    setError('')

    try {
      const res = await fetch('/api/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          type: formData.type,
          config: {
            promptId: formData.promptId,
            messageBody: formData.messageBody,
            fromNumber: formData.fromNumber
          },
          phone_numbers: useExistingList ? [] : uploadedNumbers,
          contact_list_id: useExistingList ? selectedListId : null
        })
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Creation failed')

      onCreated()
      onClose()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const canProceedStep1 = uploadedNumbers.length > 0 || selectedListId
  const canProceedStep2 = formData.name && formData.fromNumber &&
    (formData.type === 'voice' ? formData.promptId : formData.messageBody)

  const contactCount = useExistingList ? (selectedList?.contact_count || 0) : uploadedNumbers.length

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Create Campaign</h2>
            <p className="text-sm text-slate-500">Step {step} of 3</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>

        {/* Progress */}
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center gap-2">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${s < step ? 'bg-emerald-500 text-white' :
                  s === step ? 'bg-blue-600 text-white' :
                    'bg-slate-200 text-slate-500'
                  }`}>
                  {s < step ? <Check className="h-4 w-4" /> : s}
                </div>
                {s < 3 && <div className={`w-16 h-1 mx-2 rounded ${s < step ? 'bg-emerald-500' : 'bg-slate-200'}`} />}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[50vh]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <h3 className="font-bold text-slate-700">Select Contacts</h3>

              {/* Toggle: Upload vs Existing List */}
              <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
                <button
                  onClick={() => { setUseExistingList(false); setSelectedListId(''); }}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-bold transition-colors ${!useExistingList ? 'bg-white text-blue-600 shadow' : 'text-slate-500'
                    }`}
                >
                  Upload New
                </button>
                <button
                  onClick={() => { setUseExistingList(true); setUploadedNumbers([]); setFile(null); }}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-bold transition-colors ${useExistingList ? 'bg-white text-blue-600 shadow' : 'text-slate-500'
                    }`}
                >
                  Use Existing List
                </button>
              </div>

              {!useExistingList ? (
                <>
                  <p className="text-sm text-slate-500">Upload an Excel file (.xlsx) with a column containing "Phone" in the header.</p>

                  <label className="block">
                    <div className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${uploading ? 'border-blue-300 bg-blue-50' : 'border-slate-300 hover:border-blue-400 hover:bg-blue-50'
                      }`}>
                      {uploading ? (
                        <Loader2 className="h-10 w-10 mx-auto text-blue-500 animate-spin" />
                      ) : (
                        <>
                          <FileSpreadsheet className="h-10 w-10 mx-auto text-slate-400 mb-3" />
                          <p className="text-sm font-medium text-slate-600">
                            {file ? file.name : 'Click to upload or drag and drop'}
                          </p>
                          <p className="text-xs text-slate-400 mt-1">.xlsx files only</p>
                        </>
                      )}
                    </div>
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      className="hidden"
                      onChange={handleFileUpload}
                      disabled={uploading}
                    />
                  </label>

                  {uploadedNumbers.length > 0 && (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                      <div className="flex items-center gap-2 text-emerald-700">
                        <CheckCircle2 className="h-5 w-5" />
                        <span className="font-bold">{uploadedNumbers.length} contacts found</span>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm text-slate-500">Choose from your saved contact lists.</p>

                  {contactLists.length === 0 ? (
                    <div className="text-center py-8 text-slate-400">
                      <List className="h-10 w-10 mx-auto mb-2 opacity-30" />
                      <p>No contact lists yet</p>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {contactLists.map(list => (
                        <button
                          key={list.id}
                          onClick={() => setSelectedListId(list.id)}
                          className={`w-full p-4 rounded-xl border-2 text-left transition-all ${selectedListId === list.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-slate-200 hover:border-slate-300'
                            }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-bold text-slate-800">{list.name}</p>
                              <p className="text-xs text-slate-500">{list.description || 'No description'}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-bold text-blue-600">{list.contact_count}</p>
                              <p className="text-xs text-slate-400">contacts</p>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}

                  {selectedListId && (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                      <div className="flex items-center gap-2 text-emerald-700">
                        <CheckCircle2 className="h-5 w-5" />
                        <span className="font-bold">Selected: {selectedList?.name} ({selectedList?.contact_count} contacts)</span>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h3 className="font-bold text-slate-700">Configure Campaign</h3>

              {/* Campaign Name */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Campaign"
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              {/* Campaign Type */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Campaign Type</label>
                <div className="flex gap-3">
                  {(['voice', 'sms', 'whatsapp'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setFormData({ ...formData, type: t })}
                      className={`flex-1 p-4 rounded-xl border-2 transition-all ${formData.type === t
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300'
                        }`}
                    >
                      <TypeBadge type={t} />
                    </button>
                  ))}
                </div>
              </div>

              {/* From Number */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">From Number</label>
                <select
                  value={formData.fromNumber}
                  onChange={(e) => setFormData({ ...formData, fromNumber: e.target.value })}
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="">Select a number</option>
                  {registeredPhones.map((p: any) => (
                    <option key={p.id} value={p.phoneNumber}>{p.phoneNumber}</option>
                  ))}
                </select>
              </div>

              {/* Voice: Prompt Selector */}
              {formData.type === 'voice' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">AI Prompt</label>
                  <select
                    value={formData.promptId}
                    onChange={(e) => setFormData({ ...formData, promptId: e.target.value })}
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="">Select a prompt</option>
                    {prompts.map((p: any) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* SMS/WhatsApp: Message Body */}
              {(formData.type === 'sms' || formData.type === 'whatsapp') && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Message</label>
                  <textarea
                    value={formData.messageBody}
                    onChange={(e) => setFormData({ ...formData, messageBody: e.target.value })}
                    placeholder="Enter your message..."
                    rows={4}
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                  />
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <h3 className="font-bold text-slate-700">Review & Create</h3>

              <GlassCard className="!p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-500">Campaign Name</span>
                  <span className="font-medium text-slate-800">{formData.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Type</span>
                  <TypeBadge type={formData.type} />
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">From Number</span>
                  <span className="font-mono text-slate-800">{formData.fromNumber}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Contacts</span>
                  <span className="font-bold text-blue-600">{contactCount}</span>
                </div>
                {useExistingList && selectedList && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Contact List</span>
                    <span className="font-medium text-slate-800">{selectedList.name}</span>
                  </div>
                )}
              </GlassCard>

              {(formData.type === 'sms' || formData.type === 'whatsapp') && (
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <p className="text-xs text-slate-500 mb-1">Message Preview</p>
                  <p className="text-sm text-slate-700">{formData.messageBody}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-200 bg-slate-50">
          <button
            onClick={() => step > 1 ? setStep(step - 1) : onClose()}
            className="px-4 py-2 text-slate-600 hover:text-slate-800 font-medium flex items-center gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            {step > 1 ? 'Back' : 'Cancel'}
          </button>

          {step < 3 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={step === 1 ? !canProceedStep1 : !canProceedStep2}
              className="px-6 py-2 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={creating}
              className="px-6 py-2 bg-emerald-600 text-white rounded-xl font-bold hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Create Campaign
            </button>
          )}
        </div>
      </motion.div>
    </div>
  )
}

// Campaign Detail View
const CampaignDetail = ({
  campaign,
  onBack,
  onRefresh
}: {
  campaign: Campaign
  onBack: () => void
  onRefresh: () => void
}) => {
  const progressPercent = campaign.stats.total
    ? Math.round(((campaign.stats.success + campaign.stats.failed) / campaign.stats.total) * 100)
    : 0

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
        <ChevronLeft className="h-4 w-4" />
        Back to Campaigns
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">{campaign.name}</h2>
          <div className="flex items-center gap-3 mt-2">
            <TypeBadge type={campaign.type} />
            <StatusBadge status={campaign.status} />
          </div>
        </div>
        <button onClick={onRefresh} className="p-2 hover:bg-slate-100 rounded-lg">
          <Loader2 className="h-5 w-5 text-slate-400" />
        </button>
      </div>

      {/* Progress */}
      <GlassCard>
        <div className="flex items-center justify-between mb-4">
          <span className="text-lg font-bold text-slate-800">Progress</span>
          <span className="text-2xl font-bold text-blue-600">{progressPercent}%</span>
        </div>
        <div className="h-4 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </GlassCard>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <GlassCard className="!p-4 text-center">
          <Users className="h-6 w-6 mx-auto text-slate-400 mb-2" />
          <p className="text-2xl font-bold text-slate-800">{campaign.stats.total}</p>
          <p className="text-xs text-slate-500">Total</p>
        </GlassCard>
        <GlassCard className="!p-4 text-center">
          <Clock className="h-6 w-6 mx-auto text-blue-400 mb-2" />
          <p className="text-2xl font-bold text-blue-600">{campaign.stats.pending}</p>
          <p className="text-xs text-slate-500">Pending</p>
        </GlassCard>
        <GlassCard className="!p-4 text-center">
          <CheckCircle2 className="h-6 w-6 mx-auto text-emerald-400 mb-2" />
          <p className="text-2xl font-bold text-emerald-600">{campaign.stats.success}</p>
          <p className="text-xs text-slate-500">Success</p>
        </GlassCard>
        <GlassCard className="!p-4 text-center">
          <XCircle className="h-6 w-6 mx-auto text-red-400 mb-2" />
          <p className="text-2xl font-bold text-red-600">{campaign.stats.failed}</p>
          <p className="text-xs text-slate-500">Failed</p>
        </GlassCard>
      </div>
    </div>
  )
}

function ContactListDetail({ list, onBack, onRefresh }: { list: ContactList; onBack: () => void; onRefresh: () => void }) {
  const [contacts, setContacts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showManualModal, setShowManualModal] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Manual add state
  const [manualNumbers, setManualNumbers] = useState('')
  const [addingManual, setAddingManual] = useState(false)

  const loadContacts = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/contact-lists/${list.id}/contacts`)
      const data = await res.json()
      if (data.contacts) setContacts(data.contacts)
    } catch (e) {
      console.error('Error loading contacts:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadContacts()
  }, [list.id])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', e.target.files[0])

    try {
      const res = await fetch(`/api/contact-lists/${list.id}/upload`, {
        method: 'POST',
        body: formData
      })

      if (res.ok) {
        await onRefresh() // Update list counts
        await loadContacts()
        setShowUploadModal(false)
      } else {
        const err = await res.json()
        alert(`Upload failed: ${err.detail || 'Unknown error'}`)
      }
    } catch (e) {
      console.error('Upload error:', e)
      alert('Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleManualAdd = async () => {
    if (!manualNumbers.trim()) return
    setAddingManual(true)

    // Convert comma/newline separated string to list of objects
    const numbers = manualNumbers.split(/[\n,]+/).map(n => n.trim()).filter(n => n)
    const contactsPayload = numbers.map(n => ({
      original: n,
      name: '',
      metadata: {}
    }))

    try {
      const res = await fetch(`/api/contact-lists/${list.id}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contacts: contactsPayload })
      })

      if (res.ok) {
        await onRefresh()
        await loadContacts()
        setShowManualModal(false)
        setManualNumbers('')
      }
    } catch (e) {
      console.error('Error adding contacts:', e)
    } finally {
      setAddingManual(false)
    }
  }

  const handleDeleteContact = async (contactId: string) => {
    if (!confirm('Remove this contact?')) return
    try {
      await fetch(`/api/contact-lists/${list.id}/contacts/${contactId}`, { method: 'DELETE' })
      loadContacts()
      onRefresh()
    } catch (e) {
      console.error('Error deleting contact:', e)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-slate-100 rounded-full transition-colors"
        >
          <ChevronLeft className="h-6 w-6 text-slate-500" />
        </button>
        <div>
          <h2 className="text-2xl font-bold text-slate-800">{list.name}</h2>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <span>{list.contact_count} contacts</span>
            <span>•</span>
            <span>Version {list.version}</span>
            <span>•</span>
            <span>Updated {new Date(list.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => setShowManualModal(true)}
            className="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-xl font-bold hover:bg-slate-50 flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Quick Add
          </button>
          <button
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 flex items-center gap-2 shadow-lg shadow-blue-500/30"
          >
            <Upload className="h-4 w-4" />
            Upload Excel
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-sm text-slate-500 mb-1">Total Contacts</p>
          <p className="text-2xl font-bold text-slate-800">{list.contact_count}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-sm text-slate-500 mb-1">Valid (E.164)</p>
          <p className="text-2xl font-bold text-emerald-600">
            {contacts.filter(c => c.status === 'active').length}
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <p className="text-sm text-slate-500 mb-1">Invalid</p>
          <p className="text-2xl font-bold text-red-600">
            {contacts.filter(c => c.status === 'invalid').length}
          </p>
        </div>
      </div>

      {/* Contacts Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-100 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search contacts..."
              className="w-full pl-9 pr-4 py-2 bg-slate-50 rounded-lg border-none focus:ring-2 focus:ring-blue-500/20 text-sm"
            />
          </div>
        </div>

        {loading ? (
          <div className="py-20 flex justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <Users className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p>No contacts yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="px-4 py-3 font-semibold text-slate-500">Name</th>
                  <th className="px-4 py-3 font-semibold text-slate-500">Phone</th>
                  <th className="px-4 py-3 font-semibold text-slate-500">Status</th>
                  <th className="px-4 py-3 font-semibold text-slate-500 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {contacts.map((contact) => (
                  <tr key={contact.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {contact.name || '-'}
                    </td>
                    <td className="px-4 py-3 text-slate-600 font-mono">
                      {contact.normalized_phone || contact.phone_number}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${contact.status === 'active'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-red-100 text-red-700'
                        }`}>
                        {contact.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDeleteContact(contact.id)}
                        className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <AnimatePresence>
        {showUploadModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl"
            >
              <h3 className="text-lg font-bold text-slate-800 mb-4">Upload Contacts</h3>
              <p className="text-sm text-slate-500 mb-6">
                Upload an Excel file (.xlsx) or CSV. The first column should be "phone".
                Optional columns: "name", "email", etc.
              </p>

              <div
                className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-blue-500 hover:bg-blue-50 transition-colors cursor-pointer group"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-10 w-10 mx-auto mb-3 text-slate-400 group-hover:text-blue-500" />
                <p className="font-medium text-slate-600 group-hover:text-blue-600">
                  {uploading ? 'Uploading...' : 'Click to select file'}
                </p>
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileUpload}
                  disabled={uploading}
                />
              </div>

              <div className="flex justify-end mt-6">
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
                  disabled={uploading}
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Manual Add Modal */}
      <AnimatePresence>
        {showManualModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-2xl"
            >
              <h3 className="text-lg font-bold text-slate-800 mb-4">Quick Add Numbers</h3>
              <p className="text-sm text-slate-500 mb-4">
                Paste phone numbers separated by commas or newlines.
              </p>
              <textarea
                value={manualNumbers}
                onChange={(e) => setManualNumbers(e.target.value)}
                className="w-full h-40 p-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm resize-none mb-4"
                placeholder="+15550001111, +15550002222..."
              />
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowManualModal(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleManualAdd}
                  disabled={!manualNumbers.trim() || addingManual}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {addingManual ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add Contacts'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Main CampaignsView Component
export default function CampaignsView() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [showWizard, setShowWizard] = useState(false)
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [prompts, setPrompts] = useState<any[]>([])
  const [phoneNumbers, setPhoneNumbers] = useState<any[]>([])
  const [contactLists, setContactLists] = useState<ContactList[]>([])
  const [selectedContactList, setSelectedContactList] = useState<ContactList | null>(null)
  const [activeTab, setActiveTab] = useState<'campaigns' | 'lists'>('campaigns')
  const [showNewListModal, setShowNewListModal] = useState(false)
  const [newListName, setNewListName] = useState('')
  const [creatingList, setCreatingList] = useState(false)

  const loadCampaigns = async () => {
    try {
      const res = await fetch('/api/campaigns')
      const data = await res.json()
      if (data.campaigns) setCampaigns(data.campaigns)
    } catch (e) {
      console.error('Error loading campaigns:', e)
    } finally {
      setLoading(false)
    }
  }

  const loadContactLists = async () => {
    try {
      const res = await fetch('/api/contact-lists')
      const data = await res.json()
      if (data.lists) setContactLists(data.lists)
    } catch (e) {
      console.error('Error loading contact lists:', e)
    }
  }


  const loadPrompts = async () => {
    try {
      const res = await fetch('/api/prompts')
      const data = await res.json()
      if (data.prompts) setPrompts(data.prompts)
    } catch (e) {
      console.error('Error loading prompts:', e)
    }
  }

  const loadPhoneNumbers = async () => {
    try {
      const res = await fetch('/api/phones?type=calls')
      const data = await res.json()
      if (data.phones) setPhoneNumbers(data.phones)
    } catch (e) {
      console.error('Error loading phones:', e)
    }
  }

  useEffect(() => {
    loadCampaigns()
    loadPrompts()
    loadPhoneNumbers()
    loadContactLists()

    // Poll for updates while any campaign is running
    const interval = setInterval(() => {
      if (campaigns.some(c => c.status === 'running')) {
        loadCampaigns()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const handleCreateList = async () => {
    if (!newListName) return
    setCreatingList(true)
    try {
      const res = await fetch('/api/contact-lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newListName })
      })
      if (res.ok) {
        loadContactLists()
        setShowNewListModal(false)
        setNewListName('')
      }
    } catch (e) {
      console.error('Error creating list:', e)
    } finally {
      setCreatingList(false)
    }
  }

  const handleDeleteList = async (listId: string) => {
    if (!confirm('Delete this contact list?')) return
    try {
      await fetch(`/api/contact-lists/${listId}`, { method: 'DELETE' })
      loadContactLists()
    } catch (e) {
      console.error('Error deleting list:', e)
    }
  }


  const handleStart = async (id: string) => {
    try {
      await fetch(`/api/campaigns/${id}/start`, { method: 'POST' })
      loadCampaigns()
    } catch (e) {
      console.error('Error starting campaign:', e)
    }
  }

  const handlePause = async (id: string) => {
    try {
      await fetch(`/api/campaigns/${id}/pause`, { method: 'POST' })
      loadCampaigns()
    } catch (e) {
      console.error('Error pausing campaign:', e)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this campaign?')) return
    try {
      await fetch(`/api/campaigns/${id}`, { method: 'DELETE' })
      loadCampaigns()
    } catch (e) {
      console.error('Error deleting campaign:', e)
    }
  }

  const handleSelectCampaign = async (campaign: Campaign) => {
    try {
      const res = await fetch(`/api/campaigns/${campaign.id}`)
      const data = await res.json()
      if (data.campaign) setSelectedCampaign(data.campaign)
    } catch (e) {
      console.error('Error loading campaign details:', e)
    }
  }

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      {!selectedCampaign && !selectedContactList && (
        <div className="flex gap-2 p-1 bg-slate-100 rounded-lg w-fit">
          <button
            onClick={() => setActiveTab('campaigns')}
            className={`py-2 px-4 rounded-md text-sm font-bold flex items-center gap-2 transition-colors ${activeTab === 'campaigns' ? 'bg-white text-blue-600 shadow' : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            <Megaphone className="h-4 w-4" />
            Campaigns
          </button>
          <button
            onClick={() => setActiveTab('lists')}
            className={`py-2 px-4 rounded-md text-sm font-bold flex items-center gap-2 transition-colors ${activeTab === 'lists' ? 'bg-white text-blue-600 shadow' : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            <List className="h-4 w-4" />
            Contact Lists
          </button>
        </div>
      )}

      {selectedCampaign ? (
        <CampaignDetail
          campaign={selectedCampaign}
          onBack={() => setSelectedCampaign(null)}
          onRefresh={() => handleSelectCampaign(selectedCampaign)}
        />
      ) : selectedContactList ? (
        <ContactListDetail
          list={selectedContactList}
          onBack={() => setSelectedContactList(null)}
          onRefresh={loadContactLists}
        />
      ) : activeTab === 'campaigns' ? (
        <>
          {/* Campaigns Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-800">All Campaigns</h2>
              <p className="text-sm text-slate-500">{campaigns.length} campaign(s)</p>
            </div>
            <button
              onClick={() => setShowWizard(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 flex items-center gap-2 shadow-lg shadow-blue-500/30"
            >
              <Plus className="h-4 w-4" />
              New Campaign
            </button>
          </div>

          {/* Campaign List */}
          <CampaignList
            campaigns={campaigns}
            onSelect={handleSelectCampaign}
            onStart={handleStart}
            onPause={handlePause}
            onDelete={handleDelete}
            loading={loading}
          />
        </>
      ) : (
        <>
          {/* Contact Lists Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-800">Contact Lists</h2>
              <p className="text-sm text-slate-500">Manage reusable contact lists for campaigns</p>
            </div>
            <button
              onClick={() => setShowNewListModal(true)}
              className="px-4 py-2 bg-emerald-600 text-white rounded-xl font-bold hover:bg-emerald-700 flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              New List
            </button>
          </div>

          {/* Contact Lists Table */}
          {contactLists.length === 0 ? (
            <div className="text-center py-20 text-slate-400">
              <List className="h-12 w-12 mx-auto mb-4 opacity-30" />
              <p>No contact lists yet</p>
              <p className="text-sm">Create a list to reuse contacts across campaigns</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Contacts</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Version</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase">Updated</th>
                    <th className="px-4 py-3 text-right text-xs font-bold text-slate-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {contactLists.map((list) => (
                    <tr key={list.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-800">{list.name}</p>
                        <p className="text-xs text-slate-400">{list.description || 'No description'}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-bold text-blue-600">{list.contact_count}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500">v{list.version}</td>
                      <td className="px-4 py-3 text-sm text-slate-500">
                        {new Date(list.updated_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setSelectedContactList(list)}
                            className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="View"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteList(list.id)}
                            className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Wizard Modal */}
      <AnimatePresence>
        {showWizard && (
          <CampaignWizard
            onClose={() => setShowWizard(false)}
            onCreated={loadCampaigns}
            prompts={prompts}
            phoneNumbers={phoneNumbers}
            contactLists={contactLists}
          />
        )}
      </AnimatePresence>

      {/* New List Modal */}
      <AnimatePresence>
        {showNewListModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl"
            >
              <h3 className="text-lg font-bold text-slate-800 mb-4">Create Contact List</h3>
              <input
                type="text"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                placeholder="List name..."
                className="w-full px-4 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none mb-4"
              />
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowNewListModal(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateList}
                  disabled={!newListName || creatingList}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-bold disabled:opacity-50"
                >
                  {creatingList ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
