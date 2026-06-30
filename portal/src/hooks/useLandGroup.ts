'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useLandGroup(id: string) {
  return useQuery({
    queryKey: ['land-group', id],
    queryFn: () => api.lands.group(id),
    enabled: !!id,
    staleTime: 30_000,
  })
}
