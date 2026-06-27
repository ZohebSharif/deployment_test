"""FastAPI RSVP app — server-rendered HTML, raw SQL via psycopg2."""

import secrets
import string
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from . import db

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="RSVP App")

VALID_RESPONSES = {"Yes", "Maybe", "No"}
SLUG_ALPHABET = string.ascii_lowercase + string.digits


def generate_slug(length=8):
    """Generate a random URL-safe slug."""
    return "".join(secrets.choice(SLUG_ALPHABET) for _ in range(length))


@app.get("/health", response_class=PlainTextResponse)
def health():
    """Lightweight health check for load balancers."""
    return PlainTextResponse("OK", status_code=200)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Form to create a new event."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.post("/events")
def create_event(request: Request, name: str = Form(...)):
    """Create an event with a unique random slug, then show its links."""
    name = name.strip()
    if not name:
        return templates.TemplateResponse(
            "home.html",
            {"request": request, "error": "Event name is required."},
            status_code=400,
        )

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
                "INSERT INTO events (name, slug) VALUES (%s, %s) RETURNING slug",
                (name, slug),
            )
            slug = cur.fetchone()["slug"]
            break
    else:
        return templates.TemplateResponse(
            "home.html",
            {"request": request, "error": "Could not generate a unique link, try again."},
            status_code=500,
        )

    return templates.TemplateResponse(
        "created.html",
        {"request": request, "name": name, "slug": slug},
    )


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

def fetch_event(slug):
    """Return the event row for a slug, or None."""
    with db.get_cursor() as cur:
        cur.execute(
            "SELECT id, name, slug, created_at FROM events WHERE slug = %s",
            (slug,),
        )
        return cur.fetchone()
