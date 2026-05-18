'use client'
import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { format } from 'date-fns'
import { useLands } from '@/hooks/useLands'
import { TopBar } from '@/components/layout/TopBar'
import { DataTable } from '@/components/ui/DataTable'
import { Button } from '@/components/ui/Button'
import { StatCard } from '@/components/lands/StatCard'
import { LandStatusBadge } from '@/components/lands/LandStatusBadge'
import { ConfidenceBand } from '@/components/lands/ConfidenceBand'
import { TrendIndicator } from '@/components/lands/TrendIndicator'
import { RISK_TIER_COLORS, RISK_TIER_LABELS } from '@/lib/constants'
import type { LandResult, Column } from '@/lib/types'
import { formatFeddan } from '@/lib/geo'

const STATUS_OPTIONS = ['all', 'active', 'intermittent', 'inactive', 'encroachment', 'processing', 'queued'] as const
const CONFIDENCE_OPTIONS = ['all', 'high', 'medium', 'low'] as const

export default function LandsPage() {
  const router = useRouter()
  const { data: lands = [], isLoading } = useLands()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [confidenceFilter, setConfidenceFilter] = useState<string>('all')
  const [search, setSearch] = useState('')

  const stats = useMemo(() => {
    const total     = lands.length
    const active    = lands.filter(l => l.land_status === 'active').length
    const pending   = lands.filter(l => l.job_status === 'running' || l.job_status === 'queued').length
    const highRisk  = lands.filter(l => l.risk_tier === 'high').length
    return { total, active, pending, highRisk }
  }, [lands])

  const filtered = useMemo(() => {
    return lands.filter(l => {
      if (search) {
        const q = search.toLowerCase()
        if (!l.name.toLowerCase().includes(q) && !l.governorate.toLowerCase().includes(q)) return false
      }
      if (statusFilter !== 'all') {
        if (statusFilter === 'processing' && l.job_status !== 'running') return false
        if (statusFilter === 'queued'     && l.job_status !== 'queued')  return false
        if (!['processing', 'queued'].includes(statusFilter) && l.land_status !== statusFilter) return false
      }
      if (confidenceFilter !== 'all' && l.confidence?.status !== confidenceFilter) return false
      return true
    })
  }, [lands, statusFilter, confidenceFilter, search])

  const columns: Column<LandResult>[] = [
    {
      key: 'name',
      label: 'Land / Location',
      sortable: true,
      render: (_, row) => (
        <div>
          <p className="font-medium text-gray-900 text-sm">{row.name}</p>
          <p className="text-xs text-gray-400">{row.governorate}{row.district ? ` · ${row.district}` : ''}</p>
        </div>
      ),
    },
    {
      key: 'land_status',
      label: 'Status',
      sortable: true,
      render: (_, row) => (
        <LandStatusBadge status={row.land_status} jobStatus={row.job_status} />
      ),
    },
    {
      key: 'area_feddan',
      label: 'Area',
      sortable: true,
      render: (v) => <span className="font-mono text-xs">{formatFeddan(v as number)}</span>,
    },
    {
      key: 'submitted_at',
      label: 'Submitted',
      sortable: true,
      render: (v) => (
        <span className="text-xs text-gray-500">
          {v ? format(new Date(v as string), 'dd MMM yyyy') : '—'}
        </span>
      ),
    },
    {
      key: 'confidence',
      label: 'Confidence',
      render: (_, row) => {
        if (!row.confidence) return <span className="text-gray-300 text-xs">—</span>
        const colors = { high: 'text-green-600', medium: 'text-amber-600', low: 'text-red-600' }
        const labels = { high: 'High', medium: 'Medium', low: 'Low' }
        return (
          <span className={`text-xs font-medium ${colors[row.confidence.status]}`}>
            {labels[row.confidence.status]}
          </span>
        )
      },
    },
    {
      key: 'risk_tier',
      label: 'Risk',
      render: (_, row) => {
        if (!row.risk_tier) return <span className="text-gray-300 text-xs">—</span>
        return (
          <span className={`inline-flex px-2 py-0.5 rounded-full border text-xs font-medium ${RISK_TIER_COLORS[row.risk_tier]}`}>
            {RISK_TIER_LABELS[row.risk_tier]}
          </span>
        )
      },
    },
    {
      key: 'trend_2y',
      label: '2Y Trend',
      render: (_, row) => {
        if (!row.trend_2y) return <span className="text-gray-300 text-xs">—</span>
        return <TrendIndicator trend={row.trend_2y} size="sm" />
      },
    },
    {
      key: 'id',
      label: 'Actions',
      render: (_, row) => (
        <div className="flex items-center gap-1">
          {row.job_status === 'succeeded' ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={e => { e.stopPropagation(); router.push(`/lands/${row.id}/summary`) }}
            >
              Summary
            </Button>
          ) : row.job_status === 'running' || row.job_status === 'queued' ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={e => { e.stopPropagation(); router.push(`/lands/${row.id}`) }}
            >
              Status
            </Button>
          ) : (
            <span className="text-xs text-gray-400">Failed</span>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="min-h-full bg-sand">
      <TopBar
        breadcrumbs={[{ label: 'Lands' }]}
        actions={
          <Button icon="add" onClick={() => router.push('/lands/new')}>
            Add Land
          </Button>
        }
      />

      <div className="p-6 space-y-5">
        {/* Stat row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Lands"     value={stats.total}    icon="grid_view"   color="default" />
          <StatCard label="Active"          value={stats.active}   icon="eco"         color="green"   sublabel="Confirmed cultivation" />
          <StatCard label="In Progress"     value={stats.pending}  icon="hourglass_empty" color="indigo" sublabel="Processing or queued" />
          <StatCard label="High Risk"       value={stats.highRisk} icon="warning"     color="red"     sublabel="Require review" />
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-3 bg-white border border-gray-200 rounded-md px-4 py-2.5 shadow-panel">
          <div className="flex-1 flex items-center gap-2">
            <span className="material-symbols-outlined text-gray-400 text-lg">search</span>
            <input
              type="text"
              placeholder="Search by name or governorate..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="flex-1 text-sm bg-transparent focus:outline-none placeholder:text-gray-400"
            />
          </div>
          <div className="h-4 w-px bg-gray-200" />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-sm bg-transparent border-0 focus:outline-none text-gray-600 cursor-pointer"
          >
            <option value="all">All Statuses</option>
            {STATUS_OPTIONS.filter(s => s !== 'all').map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <div className="h-4 w-px bg-gray-200" />
          <select
            value={confidenceFilter}
            onChange={e => setConfidenceFilter(e.target.value)}
            className="text-sm bg-transparent border-0 focus:outline-none text-gray-600 cursor-pointer"
          >
            <option value="all">All Confidence</option>
            {CONFIDENCE_OPTIONS.filter(c => c !== 'all').map(c => (
              <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
            ))}
          </select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
        <DataTable
          columns={columns}
          data={filtered}
          loading={isLoading}
          onRowClick={row => {
            if (row.job_status === 'succeeded') router.push(`/lands/${row.id}/summary`)
            else if (row.job_status === 'running' || row.job_status === 'queued') router.push(`/lands/${row.id}`)
          }}
          emptyMessage="No lands match your filters. Try adjusting the search or status."
        />
        </div>

        <p className="text-xs text-gray-400 text-right">
          {filtered.length} of {lands.length} lands shown
        </p>
      </div>
    </div>
  )
}
