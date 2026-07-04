import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="card center">
      <p className="big-emoji">🕵️</p>
      <h1>Event not found</h1>
      <p className="lead">
        That link doesn't match any event. Double-check it with whoever sent it to you.
      </p>
      <p>
        <Link className="btn btn-ghost" to="/">
          ← Go home
        </Link>
      </p>
    </div>
  )
}
