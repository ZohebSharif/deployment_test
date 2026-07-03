# RSVP App

A minimal RSVP web app: pick a name (that's your account — no password),
create invites, share their links, collect Yes/Maybe/No responses, and manage
everything from your dashboard. Log out and anyone can switch to their own
name from the list.

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
│       ├── home.html      # GET / (logged out)  account picker
│       ├── dashboard.html # GET / (logged in)   your invites + create form
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

| Method | Path                        | Purpose                                        |
|--------|-----------------------------|------------------------------------------------|
| GET    | `/`                         | Account picker (logged out) / dashboard (logged in) |
| POST   | `/login`                    | Log in as a name, creating it if new           |
| POST   | `/logout`                   | Clear the account cookie                       |
| POST   | `/events`                   | Creates an invite owned by the current account |
| POST   | `/events/{slug}/delete`    | Deletes an invite you own (and its RSVPs)      |
| GET    | `/rsvp/{slug}`              | Public RSVP form                               |
| POST   | `/rsvp/{slug}`             | Saves an RSVP                                  |
| GET    | `/events/{slug}/responses` | Dashboard of all RSVPs for one invite          |
| GET    | `/health`                   | Returns `200 OK` for health checks             |

Phone is required only when the response is **Yes** or **Maybe**.

"Accounts" are just names — no passwords. The current account is kept in an
`account_id` cookie. Anyone can log in as any name; this is a toy app.

## Run with Docker (recommended)

This brings up the app, PostgreSQL, and nginx together. The app applies
`schema.sql` automatically at startup (it's idempotent), so new tables and
columns reach the database — local or RDS — on every deploy with no manual
psql step.

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

## CI/CD (GitHub Actions → EC2)

Every push builds the Docker image and smoke-tests it; pushes to `main` then
rsync the code to the instance and run
`docker compose -f docker-compose.prod.yml up -d --build`. See
[.github/workflows/deploy.yml](.github/workflows/deploy.yml).

One-time setup:

1. **Instance**: append the deploy public key to `~/.ssh/authorized_keys`,
   and create `~/rsvp-app/.env` with the RDS credentials (see
   `.env.prod.example`). The security group must allow inbound 22 and 8080.
2. **Repo secrets** (`gh secret set …`): `EC2_HOST` (public IP/DNS),
   `EC2_USER` (e.g. `ec2-user`), `EC2_SSH_KEY` (the private key).

The server's `.env` is never overwritten by a deploy.

## Health check

```bash
curl -i http://localhost:8000/health   # -> 200 OK
```
