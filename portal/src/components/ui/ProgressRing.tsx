interface ProgressRingProps {
  percent: number
  size?: number
  strokeWidth?: number
  label?: string
  sublabel?: string
  color?: string
}

export function ProgressRing({
  percent,
  size = 120,
  strokeWidth = 8,
  label,
  sublabel,
  color = '#1abc9c',
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (percent / 100) * circumference

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center text-center">
        {label !== undefined && (
          <span className="text-xl font-bold text-gray-900">{label}</span>
        )}
        {sublabel && (
          <span className="text-xs text-gray-500 mt-0.5">{sublabel}</span>
        )}
      </div>
    </div>
  )
}
