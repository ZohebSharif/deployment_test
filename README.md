# RSVP App

A minimal RSVP web app: create an event, share a link, collect Yes/Maybe/No
responses, and view them on a private dashboard.

- **Backend:** FastAPI + psycopg2 (raw SQL)
- **Frontend:** Server-rendered Jinja2 templates
- **Database:** PostgreSQL

## Project structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app + all routes
│   ├── db.py              # psycopg2 connection helper (reads env vars)
│   └── templates/
│       ├── base.html
│       ├── home.html      # GET /          create-event form
│       ├── created.html   # shows shareable + dashboard links
│       ├── rsvp.html      # GET /rsvp/{slug}   public RSVP form
│       ├── thanks.html
│       ├── responses.html # GET /events/{slug}/responses  dashboard
│       └── not_found.html
├── nginx/
│   └── nginx.conf         # reverse proxy -> app:8000
├── Dockerfile             # builds the FastAPI app image
├── docker-compose.yml     # app + postgres + nginx
├── schema.sql             # events + rsvps tables
├── requirements.txt
├── .env.example
└── README.md
```

## Routes

| Method | Path                        | Purpose                                  |
|--------|-----------------------------|------------------------------------------|
| GET    | `/`                         | Form to create a new event               |
| POST   | `/events`                   | Creates event, generates random slug     |
| GET    | `/rsvp/{slug}`              | Public RSVP form                         |
| POST   | `/rsvp/{slug}`             | Saves an RSVP                            |
| GET    | `/events/{slug}/responses` | Private dashboard of all RSVPs           |
| GET    | `/health`                   | Returns `200 OK` for health checks       |

Phone is required only when the response is **Yes** or **Maybe**.

## Run with Docker (recommended)

This brings up the app, PostgreSQL, and nginx together. `schema.sql` is loaded
automatically the first time the database volume is created.

```bash
docker compose up --build
```

Then open **http://localhost:8080** (nginx). The app itself isn't published to
the host — all traffic goes through nginx, matching a typical deployment.

Override credentials by exporting `DB_USER` / `DB_PASSWORD` / `DB_NAME` (or
putting them in a `.env` file) before `up`; compose reads them as defaults.

```bash
docker compose down        # stop
docker compose down -v      # stop + wipe the database volume
```

> Re-running `schema.sql` after the first boot requires removing the volume
> (`docker compose down -v`), since Postgres only runs init scripts on a fresh
> data directory.

## Run it locally (without Docker)

### 1. Install Python deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL and create the database

If you have Postgres installed locally:

```bash
createdb rsvp
psql -d rsvp -f schema.sql
```

Or with Docker:

```bash
docker run --name rsvp-pg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rsvp -p 5432:5432 -d postgres:16

psql "postgresql://postgres:postgres@localhost:5432/rsvp" -f schema.sql
```

### 3. Configure environment variables

```bash
cp .env.example .env
# edit .env if your credentials differ, then load it:
export $(grep -v '^#' .env | xargs)
```

The app reads `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

### 4. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 to create an event.

## Health check

```bash
curl -i http://localhost:8000/health   # -> 200 OK
```
