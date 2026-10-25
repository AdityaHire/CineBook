# Cenebook

A movie ticket booking web application built with Django — browse movies, pick a showtime, select seats, and confirm a booking with a unique ticket reference. 

## Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.9+, Django 4.2 |
| **Frontend** | Bootstrap 5.3, Vanilla JavaScript (ES2022) |
| **Database** | SQLite (WAL mode, busy-timeout, FK enforcement via `core/apps.py`) |
| **Auth** | Custom email-based `User`, Argon2 password hashing, django-axes rate-limiting |
| **Static serving** | WhiteNoise |
| **Design** | Apple-inspired token system, dark mode, View Transitions API, animated SVG |

---

## Quick Start

```bash
# 1. Clone and enter the directory
cd cenibook

# 2. Create & activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env
# Open .env and set a strong SECRET_KEY value

# 5. Apply database migrations
python manage.py migrate

# 6. Create an admin user
python manage.py createsuperuser
# Enter your email and display name; the account is promoted to admin automatically.

# 7. (Optional) Load demo data
python manage.py seed_demo
# Creates movies, theatres, screens, 7 days of shows, and 3 demo accounts.

# 8. Start the development server
python manage.py runserver
```

Open <http://localhost:8000>

---

## Demo Accounts (after `seed_demo`)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@cenebook.com` | `AdminPass123!` |
| Customer 1 | `user1@cenebook.com` | `UserPass123!` |
| Customer 2 | `user2@cenebook.com` | `UserPass123!` |

Admin panel is at `/manage/`.

---

## Project Structure

```
cenebook/         Django project package (settings, urls, wsgi)
accounts/         Custom User model (email-based), registration, login views
catalog/          Movie, Theatre, Screen, Seat, Show models and services
bookings/         SeatHold, Booking, BookingSeat models + booking/cancel services
adminpanel/       Staff-only admin pages at /manage/ (movies, shows, bookings)
core/             Shared decorators, management commands (purge_holds, seed_demo)
templates/        All HTML templates (Jinja-free Django templates)
static/
  css/site.css    Design system (tokens, dark mode, animations, print styles)
  js/             seat-map.js, pay.js, cancel.js, hold-timer.js
work docs/        Project PRD and phase specifications
```

---

## Key Features

- **Movie catalogue** — search, genre/language/status filters, paginated grid
- **Seat selection** — live SVG seat map; atomically held for 5 minutes via `SeatHold`
- **Booking confirmation** — idempotent (`idempotency_key`); server-side total; simulated payment
- **My Bookings** — Upcoming / Past tabs; printable ticket cards; cancel modal
- **Cancellation** — 2-hour cut-off enforced in service layer; seats freed on cancel
- **Admin panel** — full CRUD for movies, theatres, screens, shows; booking list with search & filters; revenue / bookings-today metrics; show cancellation with bulk refund
- **Security** — CSRF, XSS protection (Django defaults), Axes rate-limiting, FK authorization on every booking endpoint

---

## Running Tests

```bash
python manage.py test
```

### What is tested (60 tests across 4 apps)

| Test class | Description |
|---|---|
| `SeatHoldServiceTests` | Holds, conflicts, expiry, seat-map statuses |
| `BookingsAPITests` | Seat, hold, and release JSON endpoints |
| `BookingsPagesTests` | Seat-selection and summary page rendering |
| `BookingConfirmationAndPaymentTests` | Service-level confirm, idempotency, payment failure, cancel |
| `BookingAPIsPhase4Tests` | Confirm and cancel JSON API responses |
| `BookingPagesPhase4Tests` | My Bookings, ticket details, confirmation page |
| `ConcurrentBookingTest` | DB unique-constraint enforcement; idempotency under concurrent calls |
| `TimingTests` | Hold expiry, booking cut-off, 2-hour cancellation cut-off |
| `AuthorizationTests` | Cross-user 404, non-admin 403 on `/manage/`, unauthenticated redirects |
| `AdminPanelTests` | Dashboard, CRUD, overlap rejection, show cancellation |
| `CatalogModelAndServiceTests` | Duration, seat generation, overlap logic |
| `CatalogViewsTests` | Home, search, movie details, show API |

---

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `insecure-dev-key-change-me` | **Must be changed for production** |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames |
| `SESSION_COOKIE_SECURE` | `False` | Set `True` when behind HTTPS |
| `CSRF_COOKIE_SECURE` | `False` | Set `True` when behind HTTPS |

---

## Production Checklist

- [ ] `DEBUG=False` and a strong `SECRET_KEY` in `.env`
- [ ] `ALLOWED_HOSTS` set to your actual domain
- [ ] `SESSION_COOKIE_SECURE=True` and `CSRF_COOKIE_SECURE=True` (requires HTTPS)
- [ ] `python manage.py collectstatic` — WhiteNoise serves static files automatically
- [ ] Run `python manage.py test` — all 60 tests must pass

---

## Build Phases

| Phase | Status | Goal |
|-------|--------|------|
| 1 | ✅ Done | Foundation — project scaffold, custom User, auth pages, Apple design system |
| 2 | ✅ Done | Catalog & Admin — movies, theatres, screens, shows, admin CRUD |
| 3 | ✅ Done | Seat Selection & Holds — live seat map, atomic 5-min holds, summary page |
| 4 | ✅ Done | Booking, My Bookings & Cancellation — payment simulation, printable tickets |
| 5 | ✅ Done | Polish, Testing & Release — View Transitions, animations, 60-test suite, docs |
