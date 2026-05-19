'use client'
import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { JobState } from '@/lib/types'

/**
 * Opens an SSE connection to /api/jobs/{jobId}/events and writes updates
 * directly into the TanStack Query cache under the ['job', jobId] key.
 *
 * Returns { connected } so the caller can suppress polling while SSE is live.
 *
 * For mock jobs the server returns 404, onerror fires, and connected stays false —
 * useJobPolling continues to handle those normally.
 */
export function useJobEvents(jobId: string | undefined) {
    const queryClient = useQueryClient()
    const [connected, setConnected] = useState(false)

    useEffect(() => {
        if (!jobId) return

        const source = new EventSource(`/api/jobs/${jobId}/events`)

        source.onopen = () => setConnected(true)

        const handleEvent = (event: MessageEvent) => {
            try {
                const data = JSON.parse(event.data) as JobState
                queryClient.setQueryData(['job', jobId], data)
            } catch {
                // ignore parse errors
            }
        }

        source.addEventListener('job.update', handleEvent)
        source.addEventListener('job.done', handleEvent)
        source.addEventListener('job.error', handleEvent)

        source.onerror = () => {
            setConnected(false)
            source.close()
        }

        return () => {
            source.close()
            setConnected(false)
        }
    }, [jobId, queryClient])

    return { connected }
}
