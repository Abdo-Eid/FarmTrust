'use client'
import { useState, useRef, useEffect } from 'react'
import { clsx } from 'clsx'

interface LogViewerProps {
  logs: string[]
  maxHeight?: string
}

export function LogViewer({ logs, maxHeight = '200px' }: LogViewerProps) {
  const [expanded, setExpanded] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (expanded) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs, expanded])

  return (
    <div className="border border-gray-200 rounded-md overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-2 bg-teal-950 text-teal-300 text-xs font-mono hover:bg-teal-900 transition-colors"
        onClick={() => setExpanded(v => !v)}
      >
        <span className="flex items-center gap-2">
          <span className="material-symbols-outlined text-sm">terminal</span>
          Pipeline Logs ({logs.length} lines)
        </span>
        <span className={clsx('material-symbols-outlined text-sm transition-transform', expanded && 'rotate-180')}>
          expand_more
        </span>
      </button>

      {expanded && (
        <div
          className="bg-teal-950 overflow-y-auto"
          style={{ maxHeight }}
        >
          <div className="px-4 py-3 space-y-0.5">
            {logs.map((line, i) => {
              const isError = line.includes('[ERROR]')
              const isWarn  = line.includes('[WARN]')
              return (
                <p key={i} className={clsx(
                  'text-xs font-mono leading-relaxed',
                  isError ? 'text-red-400' : isWarn ? 'text-amber-400' : 'text-teal-200'
                )}>
                  {line}
                </p>
              )
            })}
            <div ref={bottomRef} />
          </div>
        </div>
      )}
    </div>
  )
}
