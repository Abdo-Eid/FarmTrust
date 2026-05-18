'use client'

import { useParams, useRouter } from 'next/navigation'
import { useLand } from '@/hooks/useLand'
import { TopBar } from '@/components/layout/TopBar'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { DataTable } from '@/components/ui/DataTable'
import { NDVITimeseriesChart } from '@/components/evidence/NDVITimeseriesChart'
import { SeasonTable } from '@/components/evidence/SeasonTable'
import { RiskFlagList } from '@/components/lands/RiskFlagList'
import * as Tabs from '@radix-ui/react-tabs'
import { format, parseISO } from 'date-fns'
import type { Column, NDVIPoint } from '@/lib/types'

interface ComparableRecord {
  id: string
  area_feddan: number
  status: string
  ndvi_peak: number
  risk_tier: string
}

const MOCK_COMPARABLES: ComparableRecord[] = [
  { id: 'FT-2024-0051', area_feddan: 3.5, status: 'Active', ndvi_peak: 0.72, risk_tier: 'Low' },
  { id: 'FT-2024-0052', area_feddan: 4.2, status: 'Active', ndvi_peak: 0.68, risk_tier: 'Low' },
  { id: 'FT-2024-0053', area_feddan: 2.8, status: 'Intermittent', ndvi_peak: 0.54, risk_tier: 'Medium' },
  { id: 'FT-2024-0054', area_feddan: 3.9, status: 'Active', ndvi_peak: 0.75, risk_tier: 'Low' },
  { id: 'FT-2024-0055', area_feddan: 3.2, status: 'Inactive', ndvi_peak: 0.42, risk_tier: 'High' },
]

function downloadCSV(data: Record<string, unknown>[], filename: string) {
  if (!data.length) return
  const keys = Object.keys(data[0])
  const rows = [
    keys.join(','),
    ...data.map((r) =>
      keys
        .map((k) => {
          const val = r[k]
          if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
            return `"${val.replace(/"/g, '""')}"`
          }
          return val ?? ''
        })
        .join(',')
    ),
  ]
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function EvidencePage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const { data: land, isLoading } = useLand(id)

  if (isLoading) {
    return (
      <div className="min-h-full bg-sand">
        <PageHeader title="Evidence & Data" subtitle="Loading..." />
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-500 text-sm">Loading evidence data...</div>
        </div>
      </div>
    )
  }

  if (!land) {
    return (
      <div className="min-h-full bg-sand">
        <PageHeader title="Evidence & Data" subtitle="Land parcel not found" />
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-500 text-sm">Unable to load land data</div>
        </div>
      </div>
    )
  }

  const ndviColumns: Column<NDVIPoint>[] = [
    {
      key: 'date',
      label: 'Date',
      render: (value) => format(parseISO(value as string), 'dd MMM yyyy'),
    },
    {
      key: 'ndvi',
      label: 'NDVI',
      render: (value) => (value as number).toFixed(3),
    },
    {
      key: 'evi',
      label: 'EVI',
      render: (value) => (value ? (value as number).toFixed(3) : '—'),
    },
    {
      key: 'cloud_coverage',
      label: 'Cloud Coverage',
      render: (value) => `${((value as number) * 100).toFixed(1)}%`,
    },
    {
      key: 'flag',
      label: 'Flag',
      render: (value) => (value ? `⚠ ${value}` : '—'),
    },
  ]

  const comparableColumns: Column<ComparableRecord>[] = [
    { key: 'id', label: 'Land ID' },
    {
      key: 'area_feddan',
      label: 'Area (feddan)',
      render: (value) => (value as number).toFixed(1),
    },
    { key: 'status', label: 'Status' },
    {
      key: 'ndvi_peak',
      label: 'NDVI Peak',
      render: (value) => (value as number).toFixed(3),
    },
    { key: 'risk_tier', label: 'Risk Tier' },
  ]

  const getRiskDescription = (flag: string): string => {
    const descriptions: Record<string, string> = {
      waterlogging: 'Excess water retention detected in soil profile',
      salinity: 'Elevated salt concentration affecting crop yield',
      abandonment: 'Insufficient vegetation activity for 2+ seasons',
      encroachment: 'Boundary violation or unauthorized land use detected',
    }
    return descriptions[flag] || 'Unknown risk flag'
  }

  const getRiskIcon = (flag: string): string => {
    const icons: Record<string, string> = {
      waterlogging: 'water_drop',
      salinity: 'science',
      abandonment: 'grass',
      encroachment: 'warning',
    }
    return icons[flag] || 'info'
  }

  const totalSeasons = land.season_records?.length ?? 0
  const goodSeasons = land.season_records?.filter((r) => r.outcome === 'good').length ?? 0
  const avgNDVIPeak =
    totalSeasons > 0
      ? (land.season_records?.reduce((sum, r) => sum + r.ndvi_peak, 0) ?? 0) / totalSeasons
      : 0

  return (
    <div className="min-h-full bg-sand">
      <TopBar
        breadcrumbs={[
          { label: 'Lands', href: '/lands' },
          { label: land.name, href: `/lands/${land.id}/summary` },
          { label: 'Evidence' },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              icon="summarize"
              onClick={() => router.push(`/lands/${land.id}/summary`)}
            >
              Summary
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon="download"
              onClick={() => router.push(`/lands/${land.id}/report`)}
            >
              Export PDF
            </Button>
          </div>
        }
      />

      <PageHeader title={land.name} subtitle="Evidence & Data" />

      <div className="p-6">
        <Tabs.Root defaultValue="vegetation" className="w-full">
          <Tabs.List className="border-b border-gray-200 bg-transparent flex gap-0 mb-0">
            <Tabs.Trigger
              value="vegetation"
              className="px-4 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent data-[state=active]:border-teal-600 data-[state=active]:text-teal-700 hover:text-gray-900"
            >
              Vegetation Indices
            </Tabs.Trigger>
            <Tabs.Trigger
              value="seasonal"
              className="px-4 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent data-[state=active]:border-teal-600 data-[state=active]:text-teal-700 hover:text-gray-900"
            >
              Seasonal Performance
            </Tabs.Trigger>
            <Tabs.Trigger
              value="risk"
              className="px-4 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent data-[state=active]:border-teal-600 data-[state=active]:text-teal-700 hover:text-gray-900"
            >
              Risk Signals
            </Tabs.Trigger>
            <Tabs.Trigger
              value="comparables"
              className="px-4 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent data-[state=active]:border-teal-600 data-[state=active]:text-teal-700 hover:text-gray-900"
            >
              Comparables
            </Tabs.Trigger>
          </Tabs.List>

          {/* Vegetation Indices Tab */}
          <Tabs.Content value="vegetation" className="pt-6">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>NDVI & EVI Time-Series</CardTitle>
                </CardHeader>
                <NDVITimeseriesChart data={land.ndvi_series} />
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Raw Vegetation Data</CardTitle>
                    <button
                      onClick={() => {
                        const csvData = (land.ndvi_series ?? []).map((point) => ({
                          Date: point.date,
                          NDVI: point.ndvi.toFixed(3),
                          EVI: point.evi?.toFixed(3) ?? '',
                          CloudCoverage: (point.cloud_coverage * 100).toFixed(1),
                          Flag: point.flag ?? '',
                        }))
                        downloadCSV(csvData, `vegetation-data-${land.id}.csv`)
                      }}
                      className="px-3 py-1.5 bg-teal-50 text-teal-700 text-xs font-medium rounded-md hover:bg-teal-100 transition-colors"
                    >
                      <span className="material-symbols-outlined inline text-sm mr-1">download</span>
                      Export CSV
                    </button>
                  </div>
                </CardHeader>
                <DataTable
                  columns={ndviColumns}
                  data={(land.ndvi_series ?? []).map((point, idx) => ({ ...point, id: String(idx) }))}
                  emptyMessage="No vegetation data available"
                />
              </Card>
            </div>
          </Tabs.Content>

          {/* Seasonal Performance Tab */}
          <Tabs.Content value="seasonal" className="pt-6">
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <div className="p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                      Total Seasons
                    </p>
                    <p className="text-2xl font-bold text-gray-900">{totalSeasons}</p>
                  </div>
                </Card>
                <Card>
                  <div className="p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                      Good Seasons
                    </p>
                    <p className="text-2xl font-bold text-teal-700">{goodSeasons}</p>
                  </div>
                </Card>
                <Card>
                  <div className="p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                      Avg NDVI Peak
                    </p>
                    <p className="text-2xl font-bold text-gray-900">{avgNDVIPeak.toFixed(3)}</p>
                  </div>
                </Card>
              </div>

              {/* Seasonal Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Seasonal Records</CardTitle>
                </CardHeader>
                <SeasonTable records={land.season_records} />
              </Card>
            </div>
          </Tabs.Content>

          {/* Risk Signals Tab */}
          <Tabs.Content value="risk" className="pt-6">
            <div className="space-y-6">
              {/* Risk Flags */}
              <Card>
                <CardHeader>
                  <CardTitle>Risk Flags</CardTitle>
                </CardHeader>
                <div className="space-y-3">
                  {land.flags && land.flags.length > 0 ? (
                    land.flags.map((flag) => (
                      <div
                        key={flag}
                        className="flex items-start gap-3 p-3 rounded-md border border-red-200 bg-red-50"
                      >
                        <span className="material-symbols-outlined text-red-700 mt-0.5 flex-shrink-0">
                          {getRiskIcon(flag)}
                        </span>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-red-900 text-sm capitalize">
                            {flag.replace(/_/g, ' ')}
                          </h4>
                          <p className="text-red-700 text-xs mt-0.5">{getRiskDescription(flag)}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="flex items-center gap-3 p-4 rounded-md border border-green-200 bg-green-50">
                      <span className="material-symbols-outlined text-green-700">check_circle</span>
                      <p className="text-green-800 text-sm font-medium">
                        No risk signals detected for this land parcel
                      </p>
                    </div>
                  )}
                </div>
              </Card>

              {/* Indicators Grid */}
              {land.indicators && (
                <Card>
                  <CardHeader>
                    <CardTitle>Indicators</CardTitle>
                  </CardHeader>
                  <div className="grid grid-cols-2 gap-4">
                    {land.indicators.ndvi_peak !== undefined && (
                      <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                          NDVI Peak
                        </p>
                        <p className="text-lg font-semibold text-gray-900">
                          {land.indicators.ndvi_peak.toFixed(3)}
                        </p>
                      </div>
                    )}
                    {land.indicators.ndvi_auc !== undefined && (
                      <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                          NDVI AUC
                        </p>
                        <p className="text-lg font-semibold text-gray-900">
                          {land.indicators.ndvi_auc.toFixed(3)}
                        </p>
                      </div>
                    )}
                    {land.indicators.cloud_free_scenes !== undefined && (
                      <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                          Cloud-Free Scenes
                        </p>
                        <p className="text-lg font-semibold text-gray-900">
                          {land.indicators.cloud_free_scenes}
                        </p>
                      </div>
                    )}
                    {land.indicators.neighbor_comparison && (
                      <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                          Neighbor Comparison
                        </p>
                        <p className="text-lg font-semibold text-gray-900 capitalize">
                          {land.indicators.neighbor_comparison.replace(/_/g, ' ')}
                        </p>
                      </div>
                    )}
                    {land.indicators.observation_coverage !== undefined && (
                      <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">
                          Observation Coverage
                        </p>
                        <p className="text-lg font-semibold text-gray-900">
                          {(land.indicators.observation_coverage * 100).toFixed(1)}%
                        </p>
                      </div>
                    )}
                  </div>
                </Card>
              )}
            </div>
          </Tabs.Content>

          {/* Comparables Tab */}
          <Tabs.Content value="comparables" className="pt-6">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle>Comparable Parcels (Sample)</CardTitle>
                      <p className="text-xs text-gray-400 mt-1">
                        Sample data for illustration — will be replaced with real comparable parcels when backend is connected.
                      </p>
                    </div>
                  </div>
                </CardHeader>
                <DataTable
                  columns={comparableColumns}
                  data={MOCK_COMPARABLES}
                  emptyMessage="No comparable data available"
                />
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-xs text-gray-500">
                    Comparables sourced from same governorate, ±20% area range
                  </p>
                </div>
              </Card>
            </div>
          </Tabs.Content>
        </Tabs.Root>
      </div>
    </div>
  )
}
