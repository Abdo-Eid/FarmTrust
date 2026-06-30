const BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

export const api = {
  lands: {
    list: ()            => request<import('./types').LandResult[]>('/lands'),
    groups: ()          => request<import('./types').LandGroupResult[]>('/lands/groups'),
    group: (id: string) => request<import('./types').LandGroupResult>(`/lands/groups/${id}`),
    get:  (id: string)  => request<import('./types').LandResult>(`/lands/${id}`),
    evidencePacket: (id: string) => request<import('./types').EvidencePacket>(`/lands/${id}/evidence-packet`),
    create: (body: import('./types').CreateLandPayload) => request<import('./types').LandResult>('/lands', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
    delete: (id: string) => request<void>(`/lands/${id}`, { method: 'DELETE' }),
    deleteGroup: (id: string) => request<void>(`/lands/groups/${id}`, { method: 'DELETE' }),
  },
  jobs: {
    get:    (id: string) => request<import('./types').JobState>(`/jobs/${id}`),
    cancel: (id: string) => request<import('./types').JobState>(`/jobs/${id}/cancel`, { method: 'POST' }),
  },
  assistant: {
    narrate: (id: string) =>
      request<import('./types').AssistantResponse>(`/lands/${id}/assistant/narrate`, { method: 'POST' }),
    chat: (id: string, body: import('./types').ChatRequest) =>
      request<import('./types').AssistantResponse>(`/lands/${id}/assistant/chat`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  },
}
