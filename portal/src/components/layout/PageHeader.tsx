import { clsx } from 'clsx'

interface PageHeaderProps {
  title: string
  subtitle?: string
  meta?: Array<{ icon: string; value: string }>
  actions?: React.ReactNode
  className?: string
}

export function PageHeader({ title, subtitle, meta, actions, className }: PageHeaderProps) {
  return (
    <div
      className={clsx(
        'relative bg-teal-gradient overflow-hidden',
        className
      )}
    >
      {/* Tech-grid overlay */}
      <div
        className="absolute inset-0 bg-tech-grid opacity-100 pointer-events-none"
        aria-hidden
      />

      <div className="relative px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-white text-xl font-semibold leading-tight">{title}</h1>
            {subtitle && (
              <p className="text-teal-100 text-sm mt-1">{subtitle}</p>
            )}
            {meta && meta.length > 0 && (
              <div className="flex items-center gap-4 mt-2">
                {meta.map((m, i) => (
                  <span key={i} className="flex items-center gap-1 text-teal-100 text-xs">
                    <span className="material-symbols-outlined text-sm">{m.icon}</span>
                    {m.value}
                  </span>
                ))}
              </div>
            )}
          </div>
          {actions && (
            <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>
          )}
        </div>
      </div>
    </div>
  )
}
