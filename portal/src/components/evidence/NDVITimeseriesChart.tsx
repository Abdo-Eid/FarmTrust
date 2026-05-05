'use client'

import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { format, parseISO } from 'date-fns'
import type { NDVIPoint } from '@/lib/types'

interface NDVITimeseriesChartProps {
  data?: NDVIPoint[]
}

export function NDVITimeseriesChart({ data }: NDVITimeseriesChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-80 bg-gray-50 rounded-md border border-gray-100">
        <p className="text-gray-400 text-sm">No vegetation data available</p>
      </div>
    )
  }

  const chartData = data.map(point => ({
    ...point,
    formattedDate: format(parseISO(point.date), 'MMM yy'),
  }))

  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props
    const isHighCloud = payload.cloud_coverage > 0.3
    return (
      <circle
        cx={cx}
        cy={cy}
        r={isHighCloud ? 4 : 3}
        fill={isHighCloud ? '#ef4444' : 'currentColor'}
        opacity={isHighCloud ? 0.8 : 0.5}
      />
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
        <XAxis
          dataKey="formattedDate"
          tick={{ fontSize: 12 }}
          stroke="#999"
        />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          tick={{ fontSize: 12 }}
          stroke="#999"
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '0.375rem',
            padding: '0.75rem',
          }}
          formatter={(value) => {
            if (typeof value === 'number') {
              return value.toFixed(3)
            }
            return value
          }}
          labelFormatter={(label) => `Date: ${label}`}
        />
        <Legend wrapperStyle={{ paddingTop: '1rem', fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="ndvi"
          stroke="#1abc9c"
          dot={<CustomDot />}
          isAnimationActive={false}
          name="NDVI"
        />
        {chartData.some(d => d.evi !== undefined) && (
          <Line
            type="monotone"
            dataKey="evi"
            stroke="#D4A373"
            dot={<CustomDot />}
            isAnimationActive={false}
            name="EVI"
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}
