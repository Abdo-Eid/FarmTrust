'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { JobState } from '@/lib/types'

export function useJobPolling(
  jobId: string | undefined,
  options?: { disabled?: boolean },
) {
  return useQuery<JobState>({
    queryKey: ['job', jobId],
    queryFn: () => api.jobs.get(jobId!),
    enabled: !!jobId && !options?.disabled,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 3000
      return data.status === 'succeeded' || data.status === 'failed' ? false : 3000
    },
  })
}
