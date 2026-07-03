"""FastAPI RSVP app — server-rendered HTML, raw SQL via psycopg2."""

import secrets
import string
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from . import db

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app):
    db.apply_schema()
    yield


app = FastAPI(title="RSVP App", lifespan=lifespan)

VALID_RESPONSES = {"Yes", "Maybe", "No"}
SLUG_ALPHABET = string.ascii_lowercase + string.digits
ACCOUNT_COOKIE = "account_id"


def generate_slug(length=8):
    """Generate a random URL-safe slug."""
    return "".join(secrets.choice(SLUG_ALPHABET) for _ in range(length))


@app.get("/health", response_class=PlainTextResponse)
def health():
    """Lightweight health check for load balancers."""
    return PlainTextResponse("OK", status_code=200)


# --- accounts -------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Account picker when logged out, invite dashboard when logged in."""
    account = current_account(request)
    if not account:
        return picker_page(request)
    return dashboard_page(request, account)


@app.post("/login")
def login(request: Request, name: str = Form(...)):
    """Log in as a name, creating the account if it doesn't exist yet."""
    name = name.strip()
    if not name:
        return picker_page(request, error="A name is required.", status_code=400)

    with db.get_cursor(commit=True) as cur:
        # DO UPDATE (a no-op) instead of DO NOTHING so RETURNING always
        # yields the row, whether it was just created or already existed.
        cur.execute(
            "INSERT INTO accounts (name) VALUES (%s) "
            "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id",
            (name,),
        )
        account_id = cur.fetchone()["id"]

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        ACCOUNT_COOKIE, str(account_id),
        max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax",
    )
    return response


@app.post("/logout")
def logout():
    """Clear the account cookie and return to the picker."""
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(ACCOUNT_COOKIE)
    return response


# --- invites --------------------------------------------------------------

@app.post("/events")
def create_event(request: Request, name: str = Form(...)):
    """Create an invite owned by the current account, then show its links."""
    account = current_account(request)
    if not account:
        return RedirectResponse("/", status_code=303)

    name = name.strip()
    if not name:
        return dashboard_page(request, account, "Event name is required.", 400)

    # Retry on the (unlikely) chance of a slug collision.
    for _ in range(5):
        slug = generate_slug()
        with db.get_cursor(commit=True) as cur:
            cur.execute(
                "SELECT 1 FROM events WHERE slug = %s", (slug,)
            )
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO events (name, slug, account_id) "
                "VALUES (%s, %s, %s) RETURNING slug",
                (name, slug, account["id"]),
            )
            slug = cur.fetchone()["slug"]
            break
    else:
        return dashboard_page(
            request, account, "Could not generate a unique link, try again.", 500
        )

    return templates.TemplateResponse(
        "created.html",
        {"request": request, "name": name, "slug": slug},
    )


@app.post("/events/{slug}/delete")
def delete_event(request: Request, slug: str):
    """Delete an invite (and its RSVPs) if the current account owns it."""
    account = current_account(request)
    if account:
        with db.get_cursor(commit=True) as cur:
            cur.execute(
                "DELETE FROM events WHERE slug = %s AND account_id = %s",
                (slug, account["id"]),
            )
    return RedirectResponse("/", status_code=303)


# --- public RSVP pages ----------------------------------------------------

@app.get("/rsvp/{slug}", response_class=HTMLResponse)
def rsvp_form(request: Request, slug: str):
    """Public RSVP page for an event."""
    event = fetch_event(slug)
    if not event:
        return templates.TemplateResponse(
            "not_found.html", {"request": request}, status_code=404
        )
    return templates.TemplateResponse(
        "rsvp.html", {"request": request, "event": event}
    )


@app.post("/rsvp/{slug}", response_class=HTMLResponse)
def submit_rsvp(
    request: Request,
    slug: str,
    name: str = Form(...),
    response: str = Form(...),
    phone: str = Form(""),
):
    """Save an RSVP. Phone is required when the response is Yes or Maybe."""
    event = fetch_event(slug)
    if not event:
        return templates.TemplateResponse(
            "not_found.html", {"request": request}, status_code=404
        )

    name = name.strip()
    phone = phone.strip()
    errors = []

    if not name:
        errors.append("Your name is required.")
    if response not in VALID_RESPONSES:
        errors.append("Please choose Yes, Maybe, or No.")
    if response in {"Yes", "Maybe"} and not phone:
        errors.append("A phone number is required when you respond Yes or Maybe.")

    if errors:
        return templates.TemplateResponse(
            "rsvp.html",
            {
                "request": request,
                "event": event,
                "errors": errors,
                "form": {"name": name, "phone": phone, "response": response},
            },
            status_code=400,
        )

    with db.get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO rsvps (event_id, name, phone, response) "
            "VALUES (%s, %s, %s, %s)",
            (event["id"], name, phone or None, response),
        )

    return templates.TemplateResponse(
        "thanks.html", {"request": request, "event": event, "response": response}
    )


@app.get("/events/{slug}/responses", response_class=HTMLResponse)
def responses_dashboard(request: Request, slug: str):
    """Private dashboard listing all RSVPs for an event."""
    event = fetch_event(slug)
    if not event:
        return templates.TemplateResponse(
            "not_found.html", {"request": request}, status_code=404
        )

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

    return templates.TemplateResponse(
        "responses.html",
        {"request": request, "event": event, "rsvps": rsvps, "counts": counts},
    )


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


def picker_page(request, error=None, status_code=200):
    """Render the logged-out account picker with all existing names."""
    with db.get_cursor() as cur:
        cur.execute("SELECT id, name FROM accounts ORDER BY name")
        accounts = cur.fetchall()
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "accounts": accounts, "error": error},
        status_code=status_code,
    )


def dashboard_page(request, account, error=None, status_code=200):
    """Render the account's invite dashboard with per-invite RSVP counts."""
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
        events = cur.fetchall()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "account": account, "events": events, "error": error},
        status_code=status_code,
    )


def fetch_event(slug):
    """Return the event row for a slug, or None."""
    with db.get_cursor() as cur:
        cur.execute(
            "SELECT id, name, slug, created_at FROM events WHERE slug = %s",
            (slug,),
        )
        return cur.fetchone()
