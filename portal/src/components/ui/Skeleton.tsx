import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  lines?: number
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={clsx('animate-pulse bg-gray-100 rounded', className)} />
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={clsx('bg-white border border-gray-200 rounded-md p-4 shadow-panel', className)}>
      <Skeleton className="h-4 w-1/3 mb-3" />
      <Skeleton className="h-3 w-full mb-2" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  )
}
