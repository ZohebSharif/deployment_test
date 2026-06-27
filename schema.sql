-- Database schema for the RSVP app.
-- Run with:  psql "$DATABASE_URL" -f schema.sql
-- or:        psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f schema.sql

CREATE TABLE IF NOT EXISTS events (
    id         SERIAL PRIMARY KEY,
    name       TEXT        NOT NULL,
    slug       TEXT        NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rsvps (
    id         SERIAL PRIMARY KEY,
    event_id   INTEGER     NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name       TEXT        NOT NULL,
    phone      TEXT,
    response   TEXT        NOT NULL CHECK (response IN ('Yes', 'Maybe', 'No')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rsvps_event_id ON rsvps(event_id);
