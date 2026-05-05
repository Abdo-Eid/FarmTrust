'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useLand(id: string) {
  return useQuery({
    queryKey: ['land', id],
    queryFn: () => api.lands.get(id),
    enabled: !!id,
    staleTime: 60_000,
  })
}
