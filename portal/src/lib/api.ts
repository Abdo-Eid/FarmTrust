const BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}

export const api = {
  lands: {
    list: ()            => request<import('./types').LandResult[]>('/lands'),
    get:  (id: string)  => request<import('./types').LandResult>(`/lands/${id}`),
    create: (body: unknown) => request<import('./types').LandResult>('/lands', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  },
  jobs: {
    get:  (id: string)  => request<import('./types').JobState>(`/jobs/${id}`),
  },
}
