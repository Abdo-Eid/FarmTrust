'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useLands() {
  return useQuery({
    queryKey: ['lands'],
    queryFn: () => api.lands.list(),
    staleTime: 30_000,
  })
}
