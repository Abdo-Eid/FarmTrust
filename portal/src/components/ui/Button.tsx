import { clsx } from 'clsx'
import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: string
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center justify-center gap-2 font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-1',
        size === 'sm' && 'px-3 py-1.5 text-xs',
        size === 'md' && 'px-4 py-2 text-sm',
        size === 'lg' && 'px-6 py-3 text-base',
        variant === 'primary'   && 'bg-teal-700 text-white hover:bg-teal-800 disabled:opacity-50',
        variant === 'secondary' && 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 disabled:opacity-50',
        variant === 'ghost'     && 'bg-transparent text-gray-600 hover:bg-gray-100 disabled:opacity-50',
        variant === 'danger'    && 'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50',
        (disabled || loading)   && 'cursor-not-allowed',
        className
      )}
      {...props}
    >
      {loading && (
        <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
      )}
      {icon && !loading && (
        <span className="material-symbols-outlined text-base">{icon}</span>
      )}
      {children}
    </button>
  )
}
