import Link from 'next/link'
import { clsx } from 'clsx'

interface Crumb {
  label: string
  href?: string
}

interface TopBarProps {
  breadcrumbs: Crumb[]
  actions?: React.ReactNode
  className?: string
}

export function TopBar({ breadcrumbs, actions, className }: TopBarProps) {
  return (
    <div className={clsx('flex items-center justify-between px-6 py-3 bg-white border-b border-gray-200', className)}>
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1 text-sm">
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && (
              <span className="material-symbols-outlined text-gray-300 text-sm">chevron_right</span>
            )}
            {crumb.href ? (
              <Link href={crumb.href} className="text-teal-700 hover:text-teal-600 font-medium transition-colors">
                {crumb.label}
              </Link>
            ) : (
              <span className="text-gray-600">{crumb.label}</span>
            )}
          </span>
        ))}
      </nav>

      {/* Actions */}
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
