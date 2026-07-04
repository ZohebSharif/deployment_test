import { Link, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Rsvp from './pages/Rsvp'
import Responses from './pages/Responses'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <>
      <div className="bg-glow" aria-hidden="true" />
      <header className="site-header">
        <Link className="brand" to="/">
          <span className="brand-mark">🎉</span> RSVP
        </Link>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/rsvp/:slug" element={<Rsvp />} />
          <Route path="/events/:slug/responses" element={<Responses />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  )
}
