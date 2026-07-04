import { FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import type { EventInfo, RsvpChoice } from '../types'
import NotFound from './NotFound'

const CHOICES: { value: RsvpChoice; emoji: string; kind: string }[] = [
  { value: 'Yes', emoji: '🎉', kind: 'yes' },
  { value: 'Maybe', emoji: '🤔', kind: 'maybe' },
  { value: 'No', emoji: '😢', kind: 'no' },
]

export default function Rsvp() {
  const { slug } = useParams<{ slug: string }>()
  const [event, setEvent] = useState<EventInfo | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'missing'>('loading')

  const [name, setName] = useState('')
  const [response, setResponse] = useState<RsvpChoice | ''>('')
  const [phone, setPhone] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [submitted, setSubmitted] = useState<RsvpChoice | null>(null)

  useEffect(() => {
    if (!slug) return
    api
      .eventInfo(slug)
      .then((e) => {
        setEvent(e)
        setStatus('ready')
      })
      .catch(() => setStatus('missing'))
  }, [slug])

  if (status === 'loading') return <p className="loading">Loading…</p>
  if (status === 'missing' || !event || !slug) return <NotFound />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErrors([])
    try {
      await api.submitRsvp(slug!, { name, response, phone })
      setSubmitted(response as RsvpChoice)
    } catch (err) {
      setErrors(err instanceof ApiError ? err.messages : ['Something went wrong.'])
    }
  }

  if (submitted) {
    return (
      <div className="card center">
        <p className="big-emoji">
          {submitted === 'Yes' ? '🎉' : submitted === 'Maybe' ? '🤔' : '💌'}
        </p>
        <h1>Thanks for responding!</h1>
        <p className="lead">
          You replied <span className={`badge ${submitted.toLowerCase()}`}>{submitted}</span> to{' '}
          <strong>{event.name}</strong>.
        </p>
        <p>
          <button type="button" className="btn btn-ghost" onClick={() => setSubmitted(null)}>
            Change your response
          </button>
        </p>
      </div>
    )
  }

  return (
    <>
      <p className="eyebrow">You're invited</p>
      <h1>{event.name}</h1>
      <p className="lead">Will you be there? Let them know below.</p>

      {errors.length > 0 && (
        <div className="error">
          <ul>
            {errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <form onSubmit={submit}>
          <label htmlFor="name">Your name</label>
          <input
            type="text"
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />

          <label>Your answer</label>
          <div className="choices">
            {CHOICES.map((c) => (
              <label key={c.value} className={`choice ${c.kind}`}>
                <input
                  type="radio"
                  name="response"
                  value={c.value}
                  checked={response === c.value}
                  onChange={() => setResponse(c.value)}
                />
                <span>
                  {c.emoji} {c.value}
                </span>
              </label>
            ))}
          </div>

          <label htmlFor="phone">
            Phone number <small>(required if Yes or Maybe)</small>
          </label>
          <input
            type="tel"
            id="phone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />

          <p>
            <button type="submit" className="btn btn-primary">
              Send RSVP
            </button>
          </p>
        </form>
      </div>

      <p className="back">
        <Link className="btn btn-ghost" to="/">
          ← Home
        </Link>
      </p>
    </>
  )
}
