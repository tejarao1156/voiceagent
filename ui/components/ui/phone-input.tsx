'use client'

import { cn } from '@/lib/utils'

interface PhoneInputProps {
  value: string
  onChange: (value: string) => void
  className?: string
  placeholder?: string
  required?: boolean
}

export function PhoneInput({
  value,
  onChange,
  className,
  placeholder = '5551234567',
  required = false,
}: PhoneInputProps) {
  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Allow only digits, no formatting
    const digits = e.target.value.replace(/\D/g, '')
    onChange(digits)
  }

  return (
    <div className={cn('relative', className)}>
      <input
        type="tel"
        value={value}
        onChange={handlePhoneChange}
        placeholder={placeholder}
        required={required}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
        maxLength={20}
      />
    </div>
  )
}

