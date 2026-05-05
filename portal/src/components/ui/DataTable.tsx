'use client'
import { clsx } from 'clsx'
import { useState } from 'react'
import type { Column } from '@/lib/types'

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  onRowClick?: (row: T) => void
  emptyMessage?: string
  loading?: boolean
}

export function DataTable<T extends { id: string }>({
  columns,
  data,
  onRowClick,
  emptyMessage = 'No data available',
  loading = false,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = [...data].sort((a, b) => {
    if (!sortKey) return 0
    const av = (a as Record<string, unknown>)[sortKey]
    const bv = (b as Record<string, unknown>)[sortKey]
    if (av == null) return 1
    if (bv == null) return -1
    const cmp = String(av).localeCompare(String(bv))
    return sortDir === 'asc' ? cmp : -cmp
  })

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-4 px-4 py-3 border-b border-gray-100">
            {columns.map((_, j) => (
              <div key={j} className="h-4 bg-gray-100 rounded flex-1 animate-pulse" />
            ))}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-md overflow-hidden shadow-panel">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-table-header border-b border-gray-200">
              {columns.map(col => (
                <th
                  key={String(col.key)}
                  className={clsx(
                    'px-4 py-2.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide whitespace-nowrap',
                    col.sortable && 'cursor-pointer select-none hover:text-gray-900',
                    col.width && `w-[${col.width}]`
                  )}
                  onClick={() => col.sortable && handleSort(String(col.key))}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable && sortKey === String(col.key) && (
                      <span className="material-symbols-outlined text-xs">
                        {sortDir === 'asc' ? 'arrow_upward' : 'arrow_downward'}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-gray-400 text-sm">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sorted.map(row => (
                <tr
                  key={row.id}
                  className={clsx(
                    'border-b border-gray-100 last:border-0',
                    onRowClick && 'cursor-pointer hover:bg-gray-50 transition-colors'
                  )}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map(col => (
                    <td key={String(col.key)} className="px-4 py-3 text-gray-700">
                      {col.render
                        ? col.render((row as Record<string, unknown>)[String(col.key)], row)
                        : String((row as Record<string, unknown>)[String(col.key)] ?? '—')
                      }
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
