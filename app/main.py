"""FastAPI RSVP app — JSON API consumed by the React frontend in frontend/."""

import secrets
import string
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from . import db


@asynccontextmanager
async def lifespan(app):
    db.apply_schema()
    yield


app = FastAPI(title="RSVP App", lifespan=lifespan)

VALID_RESPONSES = {"Yes", "Maybe", "No"}
SLUG_ALPHABET = string.ascii_lowercase + string.digits
ACCOUNT_COOKIE = "account_id"


class LoginBody(BaseModel):
    name: str


class EventBody(BaseModel):
    name: str


class RsvpBody(BaseModel):
    name: str
    response: str
    phone: str = ""


def generate_slug(length=8):
    """Generate a random URL-safe slug."""
    return "".join(secrets.choice(SLUG_ALPHABET) for _ in range(length))


@app.get("/health", response_class=PlainTextResponse)
def health():
    """Lightweight health check for load balancers."""
    return PlainTextResponse("OK", status_code=200)


# --- accounts -------------------------------------------------------------

@app.get("/api/me")
def me(request: Request):
    """The account for the session cookie, or null."""
    return {"account": current_account(request)}


@app.get("/api/accounts")
def list_accounts():
    """All account names, for the logged-out picker."""
    with db.get_cursor() as cur:
        cur.execute("SELECT id, name FROM accounts ORDER BY name")
        return {"accounts": cur.fetchall()}


@app.post("/api/login")
def login(body: LoginBody):
    """Log in as a name, creating the account if it doesn't exist yet."""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "A name is required.")

    with db.get_cursor(commit=True) as cur:
        # DO UPDATE (a no-op) instead of DO NOTHING so RETURNING always
        # yields the row, whether it was just created or already existed.
        cur.execute(
            "INSERT INTO accounts (name) VALUES (%s) "
            "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id, name",
            (name,),
        )
        account = cur.fetchone()

    response = JSONResponse({"account": account})
    response.set_cookie(
        ACCOUNT_COOKIE, str(account["id"]),
        max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax",
    )
    return response


@app.post("/api/logout")
def logout():
    """Clear the account cookie."""
    response = JSONResponse({"ok": True})
    response.delete_cookie(ACCOUNT_COOKIE)
    return response


# --- invites --------------------------------------------------------------

@app.get("/api/events")
def list_events(request: Request):
    """The current account's invites with per-response counts."""
    account = require_account(request)
    with db.get_cursor() as cur:
        cur.execute(
            "SELECT e.name, e.slug, e.created_at, "
            "       COUNT(r.id) FILTER (WHERE r.response = 'Yes')   AS yes, "
            "       COUNT(r.id) FILTER (WHERE r.response = 'Maybe') AS maybe, "
            "       COUNT(r.id) FILTER (WHERE r.response = 'No')    AS no "
            "FROM events e LEFT JOIN rsvps r ON r.event_id = e.id "
            "WHERE e.account_id = %s "
            "GROUP BY e.id ORDER BY e.created_at DESC",
            (account["id"],),
        )
        return {"events": cur.fetchall()}


@app.post("/api/events")
def create_event(request: Request, body: EventBody):
    """Create an invite owned by the current account."""
    account = require_account(request)
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Event name is required.")

    # Retry on the (unlikely) chance of a slug collision.
    for _ in range(5):
        slug = generate_slug()
        with db.get_cursor(commit=True) as cur:
            cur.execute("SELECT 1 FROM events WHERE slug = %s", (slug,))
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO events (name, slug, account_id) "
                "VALUES (%s, %s, %s) RETURNING name, slug",
                (name, slug, account["id"]),
            )
            return cur.fetchone()
    raise HTTPException(500, "Could not generate a unique link, try again.")


@app.delete("/api/events/{slug}")
def delete_event(request: Request, slug: str):
    """Delete an invite (and its RSVPs) if the current account owns it."""
    account = require_account(request)
    with db.get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM events WHERE slug = %s AND account_id = %s",
            (slug, account["id"]),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "No such invite under your account.")
    return {"ok": True}


# --- public RSVP endpoints ------------------------------------------------

@app.get("/api/events/{slug}")
def event_info(slug: str):
    """Public event info for the RSVP page."""
    event = fetch_event(slug)
    if not event:
        raise HTTPException(404, "Event not found.")
    return {"name": event["name"], "slug": event["slug"]}


@app.post("/api/events/{slug}/rsvps")
def submit_rsvp(slug: str, body: RsvpBody):
    """Save an RSVP. Phone is required when the response is Yes or Maybe."""
    event = fetch_event(slug)
    if not event:
        raise HTTPException(404, "Event not found.")

    name = body.name.strip()
    phone = body.phone.strip()
    errors = []

    if not name:
        errors.append("Your name is required.")
    if body.response not in VALID_RESPONSES:
        errors.append("Please choose Yes, Maybe, or No.")
    if body.response in {"Yes", "Maybe"} and not phone:
        errors.append("A phone number is required when you respond Yes or Maybe.")

    if errors:
        raise HTTPException(400, errors)

    with db.get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO rsvps (event_id, name, phone, response) "
            "VALUES (%s, %s, %s, %s)",
            (event["id"], name, phone or None, body.response),
        )
    return {"ok": True}


@app.get("/api/events/{slug}/responses")
def responses_dashboard(slug: str):
    """All RSVPs for an event, with counts."""
    event = fetch_event(slug)
    if not event:
        raise HTTPException(404, "Event not found.")

    with db.get_cursor() as cur:
        cur.execute(
            "SELECT name, phone, response, created_at "
            "FROM rsvps WHERE event_id = %s ORDER BY created_at DESC",
            (event["id"],),
        )
        rsvps = cur.fetchall()

    counts = {"Yes": 0, "Maybe": 0, "No": 0}
    for r in rsvps:
        counts[r["response"]] = counts.get(r["response"], 0) + 1

    return {
        "event": {"name": event["name"], "slug": event["slug"]},
        "rsvps": rsvps,
        "counts": counts,
    }


# --- helpers -------------------------------------------------------------

def current_account(request):
    """Return the account row for the session cookie, or None."""
    account_id = request.cookies.get(ACCOUNT_COOKIE)
    if not account_id or not account_id.isdigit():
        return None
    with db.get_cursor() as cur:
        cur.execute(
            "SELECT id, name FROM accounts WHERE id = %s", (int(account_id),)
        )
        return cur.fetchone()


def require_account(request):
    """Return the current account or raise 401."""
    account = current_account(request)
    if not account:
        raise HTTPException(401, "Not logged in.")
    return account


def fetch_event(slug):
    """Return the event row for a slug, or None."""
    with db.get_cursor() as cur:
        cur.execute(
            "SELECT id, name, slug, created_at FROM events WHERE slug = %s",
            (slug,),
        )
        return cur.fetchone()
