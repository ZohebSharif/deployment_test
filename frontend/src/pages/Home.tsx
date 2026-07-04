import { FormEvent, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { Account, EventInfo, EventSummary } from '../types'
import CopyButton from '../components/CopyButton'

export default function Home() {
  const [loading, setLoading] = useState(true)
  const [account, setAccount] = useState<Account | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .me()
      .then(({ account }) => setAccount(account))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="loading">Loading…</p>

  return (
    <>
      {error && <p className="error">{error}</p>}
      {account ? (
        <Dashboard account={account} onLogout={() => setAccount(null)} />
      ) : (
        <Picker onLogin={setAccount} />
      )}
    </>
  )
}

function Picker({ onLogin }: { onLogin: (a: Account) => void }) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .accounts()
      .then(({ accounts }) => setAccounts(accounts))
      .catch(() => setAccounts([]))
  }, [])

  async function login(loginName: string) {
    setError(null)
    try {
      const { account } = await api.login(loginName)
      onLogin(account)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    if (name.trim()) void login(name)
  }

  return (
    <>
      <p className="eyebrow">Welcome</p>
      <h1>Who are you?</h1>
      <p className="lead">
        Pick your name to manage your invites, or start fresh with a new one. No
        passwords — it's that kind of party.
      </p>

      {error && <p className="error">{error}</p>}

      <div className="card">
        {accounts.length > 0 && (
          <>
            <div className="names">
              {accounts.map((a) => (
                <button key={a.id} type="button" className="chip" onClick={() => login(a.name)}>
                  {a.name}
                </button>
              ))}
            </div>
            <div className="divider">or start fresh</div>
          </>
        )}
        <form onSubmit={submit} className="form-row">
          <input
            type="text"
            placeholder="Type a new name…"
            aria-label="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
          <button type="submit" className="btn btn-primary">
            Continue
          </button>
        </form>
      </div>
    </>
  )
}

function Dashboard({ account, onLogout }: { account: Account; onLogout: () => void }) {
  const [events, setEvents] = useState<EventSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<EventInfo | null>(null)

  const refresh = useCallback(() => {
    api
      .events()
      .then(({ events }) => setEvents(events))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(refresh, [refresh])

  async function createEvent(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const event = await api.createEvent(name)
      setCreated(event)
      setName('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function deleteEvent(event: EventSummary) {
    if (!window.confirm('Delete this invite and all of its RSVPs?')) return
    try {
      await api.deleteEvent(event.slug)
      if (created?.slug === event.slug) setCreated(null)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function logout() {
    await api.logout()
    onLogout()
  }

  return (
    <>
      <p className="eyebrow">Signed in as {account.name}</p>
      <div className="invite-head">
        <h1>Your invites</h1>
        <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>
          Log out
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card">
        <form onSubmit={createEvent} className="form-row">
          <input
            type="text"
            placeholder="New event name…"
            aria-label="Event name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <button type="submit" className="btn btn-primary">
            Create invite
          </button>
        </form>
      </div>

      {created && <CreatedPanel event={created} onDismiss={() => setCreated(null)} />}

      {loading ? (
        <p className="loading">Loading…</p>
      ) : events.length === 0 ? (
        <div className="card empty">🎈 No invites yet — create your first one above.</div>
      ) : (
        events.map((e) => (
          <InviteCard key={e.slug} event={e} onDelete={() => deleteEvent(e)} />
        ))
      )}
    </>
  )
}

function CreatedPanel({ event, onDismiss }: { event: EventInfo; onDismiss: () => void }) {
  const rsvpUrl = `${window.location.origin}/rsvp/${event.slug}`
  const responsesUrl = `${window.location.origin}/events/${event.slug}/responses`

  return (
    <div className="card">
      <div className="invite-head">
        <h3>🎊 “{event.name}” is live</h3>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onDismiss}>
          Dismiss
        </button>
      </div>

      <label>Share this link so people can RSVP</label>
      <div className="link-box">
        <Link to={`/rsvp/${event.slug}`}>{rsvpUrl}</Link>
        <CopyButton text={rsvpUrl} />
      </div>

      <label>
        View responses <small>(keep this one to yourself)</small>
      </label>
      <div className="link-box">
        <Link to={`/events/${event.slug}/responses`}>{responsesUrl}</Link>
        <CopyButton text={responsesUrl} />
      </div>
    </div>
  )
}

function InviteCard({ event, onDelete }: { event: EventSummary; onDelete: () => void }) {
  const rsvpUrl = `${window.location.origin}/rsvp/${event.slug}`
  const createdAt = new Date(event.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <div className="card">
      <div className="invite-head">
        <h3>{event.name}</h3>
        <span className="date">{createdAt}</span>
      </div>
      <div className="badges">
        <span className="badge yes">{event.yes} yes</span>
        <span className="badge maybe">{event.maybe} maybe</span>
        <span className="badge no">{event.no} no</span>
      </div>
      <div className="invite-actions">
        <Link className="btn btn-sm" to={`/rsvp/${event.slug}`}>
          RSVP page
        </Link>
        <Link className="btn btn-sm" to={`/events/${event.slug}/responses`}>
          Responses
        </Link>
        <CopyButton text={rsvpUrl} label="Copy link" />
        <button type="button" className="btn btn-sm btn-danger" onClick={onDelete}>
          Delete
        </button>
      </div>
    </div>
  )
}
