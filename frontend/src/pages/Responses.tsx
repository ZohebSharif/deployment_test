import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import type { Counts, EventInfo, Rsvp } from '../types'
import NotFound from './NotFound'

export default function Responses() {
  const { slug } = useParams<{ slug: string }>()
  const [event, setEvent] = useState<EventInfo | null>(null)
  const [rsvps, setRsvps] = useState<Rsvp[]>([])
  const [counts, setCounts] = useState<Counts>({ Yes: 0, Maybe: 0, No: 0 })
  const [status, setStatus] = useState<'loading' | 'ready' | 'missing'>('loading')

  useEffect(() => {
    if (!slug) return
    api
      .responses(slug)
      .then(({ event, rsvps, counts }) => {
        setEvent(event)
        setRsvps(rsvps)
        setCounts(counts)
        setStatus('ready')
      })
      .catch(() => setStatus('missing'))
  }, [slug])

  if (status === 'loading') return <p className="loading">Loading…</p>
  if (status === 'missing' || !event) return <NotFound />

  return (
    <>
      <p className="eyebrow">Responses</p>
      <h1>{event.name}</h1>
      <p className="lead">
        {rsvps.length} response{rsvps.length === 1 ? '' : 's'} so far.
      </p>

      <div className="stats">
        <div className="stat yes">
          <b>{counts.Yes}</b>
          <span>Yes</span>
        </div>
        <div className="stat maybe">
          <b>{counts.Maybe}</b>
          <span>Maybe</span>
        </div>
        <div className="stat no">
          <b>{counts.No}</b>
          <span>No</span>
        </div>
      </div>

      {rsvps.length > 0 ? (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Response</th>
                <th>Phone</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {rsvps.map((r, i) => (
                <tr key={i}>
                  <td>{r.name}</td>
                  <td>
                    <span className={`badge ${r.response.toLowerCase()}`}>{r.response}</span>
                  </td>
                  <td>{r.phone || '—'}</td>
                  <td className="date">
                    {new Date(r.created_at).toLocaleString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card empty">📭 No responses yet — share the RSVP link to get things going.</div>
      )}

      <p className="back">
        <Link className="btn btn-ghost" to="/">
          ← Back to my invites
        </Link>
      </p>
    </>
  )
}
