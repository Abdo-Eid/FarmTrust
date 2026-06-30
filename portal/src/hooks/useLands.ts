'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useLands() {
  return useQuery({
    queryKey: ['land-groups'],
    queryFn: () => api.lands.groups(),
    staleTime: 30_000,
  })
}
