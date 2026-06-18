'use client'

import { format, parseISO } from 'date-fns'
import type { SeasonRecord } from '@/lib/types'

interface SeasonTableProps {
  records?: SeasonRecord[]
}

export function SeasonTable({ records }: SeasonTableProps) {
  if (!records || records.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500 text-sm bg-gray-50 rounded-md border border-gray-100">
        No activity-window records available
      </div>
    )
  }

  const getOutcomeBadgeClass = (outcome: string) => {
    switch (outcome) {
      case 'good':
        return 'bg-teal-100 text-teal-800'
      case 'interrupted':
        return 'bg-amber-100 text-amber-800'
      case 'weak':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getNDVIPeakColor = (value: number) => {
    if (value >= 0.6) return 'text-green-700 font-semibold'
    if (value >= 0.4) return 'text-amber-700 font-semibold'
    return 'text-red-700 font-semibold'
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-gray-600 font-medium border-b border-gray-100">
            <th className="px-4 py-3 text-left">Activity Window</th>
            <th className="px-4 py-3 text-left">Period</th>
            <th className="px-4 py-3 text-left">NDVI Peak</th>
            <th className="px-4 py-3 text-left">Outcome</th>
            <th className="px-4 py-3 text-left">Anomaly</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record, idx) => (
            <tr key={idx} className="border-t border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-900">{record.season}</td>
              <td className="px-4 py-3 text-gray-700">
                {format(parseISO(record.start_date), 'dd MMM yyyy')} -{' '}
                {format(parseISO(record.end_date), 'dd MMM yyyy')}
              </td>
              <td className={`px-4 py-3 ${getNDVIPeakColor(record.ndvi_peak)}`}>
                {record.ndvi_peak.toFixed(3)}
              </td>
              <td className="px-4 py-3">
                <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${getOutcomeBadgeClass(record.outcome)}`}>
                  {record.outcome.charAt(0).toUpperCase() + record.outcome.slice(1)}
                </span>
              </td>
              <td className="px-4 py-3">
                {record.anomaly ? (
                  <span className="text-gray-500 italic text-xs">{record.anomaly}</span>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
