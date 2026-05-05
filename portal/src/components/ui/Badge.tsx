import { clsx } from 'clsx'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'outline'
  className?: string
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border',
        variant === 'outline' && 'bg-transparent',
        className
      )}
    >
      {children}
    </span>
  )
}
