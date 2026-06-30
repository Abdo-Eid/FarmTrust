'use client'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useEvidencePacket(id: string) {
  return useQuery({
    queryKey: ['evidence-packet', id],
    queryFn: () => api.lands.evidencePacket(id),
    enabled: !!id,
    staleTime: 60_000,
    // A 404 means the packet hasn't been generated yet — don't hammer the backend.
    retry: false,
  })
}
