import type { Account, Counts, EventInfo, EventSummary, Rsvp, RsvpChoice } from './types'

// FastAPI's HTTPException puts the message (string or string[]) in `detail`.
export class ApiError extends Error {
  status: number
  messages: string[]

  constructor(status: number, detail: unknown) {
    const messages = Array.isArray(detail)
      ? detail.map(String)
      : [typeof detail === 'string' ? detail : 'Something went wrong.']
    super(messages.join(' '))
    this.status = status
    this.messages = messages
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  })
  if (!res.ok) {
    let detail: unknown
    try {
      detail = (await res.json()).detail
    } catch {
      detail = res.statusText
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  me: () => request<{ account: Account | null }>('/api/me'),
  accounts: () => request<{ accounts: Account[] }>('/api/accounts'),
  login: (name: string) =>
    request<{ account: Account }>('/api/login', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  logout: () => request<{ ok: boolean }>('/api/logout', { method: 'POST' }),

  events: () => request<{ events: EventSummary[] }>('/api/events'),
  createEvent: (name: string) =>
    request<EventInfo>('/api/events', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  deleteEvent: (slug: string) =>
    request<{ ok: boolean }>(`/api/events/${slug}`, { method: 'DELETE' }),

  eventInfo: (slug: string) => request<EventInfo>(`/api/events/${slug}`),
  submitRsvp: (slug: string, body: { name: string; response: RsvpChoice | ''; phone: string }) =>
    request<{ ok: boolean }>(`/api/events/${slug}/rsvps`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  responses: (slug: string) =>
    request<{ event: EventInfo; rsvps: Rsvp[]; counts: Counts }>(
      `/api/events/${slug}/responses`,
    ),
}
