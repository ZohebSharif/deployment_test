export interface Account {
  id: number
  name: string
}

export interface EventSummary {
  name: string
  slug: string
  created_at: string
  yes: number
  maybe: number
  no: number
}

export interface EventInfo {
  name: string
  slug: string
}

export type RsvpChoice = 'Yes' | 'Maybe' | 'No'

export interface Rsvp {
  name: string
  phone: string | null
  response: RsvpChoice
  created_at: string
}

export interface Counts {
  Yes: number
  Maybe: number
  No: number
}
