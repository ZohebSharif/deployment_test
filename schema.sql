-- Database schema for the RSVP app.
-- Idempotent: the app applies this automatically at startup (see app/db.py),
-- so it is safe to re-run against an existing database.
-- Manual run:  psql "$DATABASE_URL" -f schema.sql

CREATE TABLE IF NOT EXISTS accounts (
    id         SERIAL PRIMARY KEY,
    name       TEXT        NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
    id         SERIAL PRIMARY KEY,
    account_id INTEGER     REFERENCES accounts(id) ON DELETE CASCADE,
    name       TEXT        NOT NULL,
    slug       TEXT        NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Upgrade path for databases created before accounts existed.
ALTER TABLE events ADD COLUMN IF NOT EXISTS
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS rsvps (
    id         SERIAL PRIMARY KEY,
    event_id   INTEGER     NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name       TEXT        NOT NULL,
    phone      TEXT,
    response   TEXT        NOT NULL CHECK (response IN ('Yes', 'Maybe', 'No')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rsvps_event_id ON rsvps(event_id);
CREATE INDEX IF NOT EXISTS idx_events_account_id ON events(account_id);
