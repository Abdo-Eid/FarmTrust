import { clsx } from 'clsx'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export function Card({ children, className, padding = 'md' }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-white border border-gray-200 rounded-md shadow-panel',
        padding === 'none' && 'p-0',
        padding === 'sm'   && 'p-3',
        padding === 'md'   && 'p-4',
        padding === 'lg'   && 'p-6',
        className
      )}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx('flex items-center justify-between pb-3 mb-3 border-b border-gray-100', className)}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h3 className={clsx('text-sm font-semibold text-gray-900 uppercase tracking-wide', className)}>
      {children}
    </h3>
  )
}
