# Cenebook — Technical Design Document

Version 1.0 · Companion to the PRD v1.1, Database Design, and API Specification

## 1. Purpose and Scope

This document explains how Cenebook is built: architecture, Django project layout, core business logic (especially seat holds and booking), how the browser JavaScript talks to Django, and how the system is secured and tested. It covers the MVP only.

## 2. Architecture Overview

Cenebook is a classic server-rendered Django application with a few JSON endpoints for the interactive seat map.

```
+---------------------------+          +-----------------------------+
|        Browser            |  HTTP    |        Django app           |
|  HTML + CSS + Bootstrap   +--------->+  URL routing                |
|  JavaScript (fetch)       |<---------+  Views (pages + JSON)       |
+---------------------------+          |  Services (business logic)  |
                                       |  Models (ORM)               |
                                       +--------------+--------------+
                                                      |
                                              +-------v-------+
                                              |    SQLite     |
                                              +---------------+
```

| Layer | Responsibility |
| --- | --- |
| Templates (HTML, Bootstrap) | Page structure and styling |
| JavaScript | Seat map rendering, live total, countdown, API calls, cancel confirmations |
| Views | Parse requests, check permissions, call services, return HTML or JSON |
| Services | All business rules (holds, booking, cancellation, show validation) |
| Models | Data structure and database constraints |
| SQLite | Persistent storage; final guard against double booking |

**Key principle:** views stay thin. Every rule that changes data lives in a service function so it can be tested without HTTP and reused by both pages and JSON endpoints.

## 3. Technology Stack and Versions

| Item | Choice |
| --- | --- |
| Language | Python 3.11 or newer |
| Framework | Django 5.x (LTS preferred) |
| Database | SQLite (Django default) |
| Frontend | Django templates, Bootstrap 5, vanilla JavaScript (ES6) |
| Auth | Django authentication with a custom user model (email login) |
| Testing | Django `TestCase` and `TransactionTestCase`, plus manual browser checks |
| Config | Environment variables (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`) |

## 4. Project Structure

```
cenebook/
├── manage.py
├── requirements.txt
├── .env.example
├── cenebook/                # project package
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                # users, auth
│   ├── models.py            # User
│   ├── forms.py             # RegisterForm, LoginForm
│   ├── views.py
│   └── urls.py
├── catalog/                 # movies, theatres, screens, seats, shows
│   ├── models.py
│   ├── views.py             # home, movie detail
│   ├── services.py          # show overlap checks, seat generation
│   ├── api.py               # shows listing JSON
│   └── urls.py
├── bookings/                # holds, bookings, cancellation
│   ├── models.py            # SeatHold, Booking, BookingSeat
│   ├── services.py         # hold_seats, confirm_booking, cancel_booking
│   ├── views.py             # seats page, summary, confirmation, my bookings
│   ├── api.py               # JSON endpoints
│   ├── errors.py            # custom exceptions mapped to API error codes
│   └── urls.py
├── adminpanel/              # custom admin pages (/manage/)
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── core/                    # shared helpers
│   ├── permissions.py       # admin_required decorator
│   ├── json.py              # JSON response/error helpers
│   └── management/commands/seed_demo.py
├── templates/
│   ├── base.html
│   ├── accounts/ catalog/ bookings/ adminpanel/
│   └── errors/ (403.html, 404.html, 500.html)
└── static/
    ├── css/site.css
    └── js/ (api.js, seatmap.js, countdown.js, pay.js, cancel.js, showtimes.js)
```

### Django apps and their responsibilities

| App | Owns | Depends on |
| --- | --- | --- |
| `accounts` | User model, registration, login, logout | none |
| `catalog` | Movie, Theatre, Screen, Seat, Show | none |
| `bookings` | SeatHold, Booking, BookingSeat and all booking logic | `accounts`, `catalog` |
| `adminpanel` | Admin pages for movies, theatres, shows, bookings | `catalog`, `bookings` |
| `core` | Decorators, helpers, seed command | none |

If you prefer, use the built-in Django admin for Movies, Theatres, Screens, and Shows and write only the Bookings list and show-cancellation pages by hand. The service layer stays the same.

## 5. Key Settings

| Setting | Value | Reason |
| --- | --- | --- |
| `AUTH_USER_MODEL` | `accounts.User` | Email login and `role` field; set before the first migration |
| `USE_TZ` | `True` | Store UTC |
| `TIME_ZONE` | `UTC` | Convert for display per theatre |
| `SESSION_COOKIE_HTTPONLY` | `True` | Block script access to the session |
| `SESSION_COOKIE_AGE` | 1,209,600 (2 weeks) or shorter | Session expiry |
| `CSRF_COOKIE_HTTPONLY` | `False` | JavaScript reads the CSRF token for `fetch` calls (or use a hidden input) |
| `LOGIN_URL` | `/login/` | Redirect for protected pages |
| `PASSWORD_HASHERS` | Argon2 first, PBKDF2 fallback | Secure hashing |
| `AUTH_PASSWORD_VALIDATORS` | Minimum length 8 | PRD rule |
| Business constants | `HOLD_MINUTES=5`, `MAX_SEATS=8`, `CANCEL_CUTOFF_HOURS=2`, `BOOKING_CUTOFF_MINUTES=15` | Kept in one `bookings/constants.py` so rules can change in one place |

In production also set `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE`.

## 6. Core Logic: Seat Availability

Seat status for a show is computed, not stored (see Database Design, Section 9).

```python
def seat_map(show, user):
    seats = Seat.objects.filter(screen=show.screen).order_by("row_label", "seat_number")
    booked = set(BookingSeat.objects.filter(show=show).values_list("seat_id", flat=True))
    holds = SeatHold.objects.filter(show=show, expires_at__gt=now())
    held = {h.seat_id: h.user_id for h in holds}
    for seat in seats:
        if seat.id in booked:
            status = "booked"
        elif seat.id in held:
            status = "selected" if held[seat.id] == user.id else "held"
        else:
            status = "available"
        yield seat, status
```

This uses three queries per request regardless of screen size.

## 7. Core Logic: Seat Hold and Booking, Step by Step

Two defences protect each seat: a **short-lived hold** while the user reviews the summary, and a **unique database constraint** at confirmation. The constraint is the final authority; holds only improve user experience.

### 7.1 Placing a hold (user clicks "Continue to summary")

Endpoint: `POST /api/shows/<id>/holds/` with `{ "seat_ids": [..] }`. All steps run inside `transaction.atomic()`.

1. **Authenticate** the user (401 if not logged in).
2. **Load the show**; reject if missing (404), cancelled, or past the booking cut-off (409 `SHOW_NOT_BOOKABLE`).
3. **Validate input:** 1 to 8 unique seat IDs (400 `INVALID_SEATS`; 400 `TOO_MANY_SEATS`).
4. **Verify seats belong to the show's screen** (400 `INVALID_SEATS`).
5. **Clean up:** delete expired holds for this show; delete this user's existing holds for this show (they are choosing again).
6. **Check booked seats:** if any chosen seat is in `booking_seats` for the show, abort with 409 `SEAT_UNAVAILABLE`, listing the seat labels.
7. **Check held seats:** if any chosen seat has an unexpired hold by someone else, abort with 409 `SEAT_UNAVAILABLE`.
8. **Create holds** for all seats with `expires_at = now + 5 minutes` using `bulk_create`.
9. If `bulk_create` raises `IntegrityError` (another user won a race between steps 7 and 8), the transaction rolls back and the API returns 409 `SEAT_UNAVAILABLE`.
10. **Return** the held seats, price per seat, total, and `expires_at`.

Because either all seats are held or none are, a user never ends up with a partial selection.

### 7.2 Confirming the booking (user clicks "Pay")

Endpoint: `POST /api/shows/<id>/bookings/` with `{ "idempotency_key": "..." }`.

1. **Authenticate** the user.
2. **Idempotency check:** if a booking exists for (`user`, `idempotency_key`), return it with 200 and stop. A double-click or page refresh therefore cannot create a second booking.
3. Open `transaction.atomic()`.
4. **Re-validate the show** (scheduled, before cut-off).
5. **Load the user's holds** for this show where `expires_at > now`. If there are none, abort with 409 `HOLD_EXPIRED`.
6. **Recompute the total** on the server: `ticket_price × number of held seats`. Never accept a price from the browser.
7. **Simulated payment:** call `payments.charge(amount)`. In the MVP it returns success; in test or demo mode it can be configured to fail. On failure, abort with 402 `PAYMENT_FAILED`; the holds remain so the user can retry until expiry.
8. **Create the booking** with a generated `booking_reference`, `total_amount`, `booking_status=confirmed`, `payment_status=paid`, the `idempotency_key`, and `seat_labels` (for example, "B3,B4").
9. **Create `booking_seats`** rows (one per held seat). The unique constraint (`show_id`, `seat_id`) guarantees no seat can be sold twice. If an `IntegrityError` occurs, the transaction rolls back and the API returns 409 `SEAT_UNAVAILABLE`.
10. **Delete the user's holds** for this show.
11. Commit and **return** the booking reference and details (201).

```python
@transaction.atomic
def confirm_booking(user, show, idempotency_key):
    existing = Booking.objects.filter(user=user, idempotency_key=idempotency_key).first()
    if existing:
        return existing, False
    ensure_bookable(show)
    holds = list(SeatHold.objects.select_related("seat")
                 .filter(user=user, show=show, expires_at__gt=now()))
    if not holds:
        raise HoldExpired()
    total = show.ticket_price * len(holds)
    payments.charge(total)                       # may raise PaymentFailed
    booking = Booking.objects.create(
        user=user, show=show, total_amount=total,
        booking_status="confirmed", payment_status="paid",
        booking_reference=new_reference(), idempotency_key=idempotency_key,
        seat_labels=",".join(h.seat.label for h in holds))
    try:
        BookingSeat.objects.bulk_create(
            [BookingSeat(booking=booking, seat=h.seat, show=show) for h in holds])
    except IntegrityError:
        raise SeatUnavailable()
    SeatHold.objects.filter(user=user, show=show).delete()
    return booking, True
```

**Caution:** catching `IntegrityError` inside an `atomic` block must be done outside or via a savepoint, so the exception propagates to roll the transaction back. The simplest approach is to catch it in the view or a wrapper around `confirm_booking`.

### 7.3 SQLite concurrency notes

- SQLite allows one writer at a time. Concurrent requests queue briefly; this is acceptable for an MVP.
- `select_for_update()` has no effect on SQLite, so the design does not depend on it.
- Enable a busy timeout (`OPTIONS: {"timeout": 20}` in `DATABASES`) so waiting writers do not fail immediately.
- Keep transactions short: no network calls and no template rendering inside `atomic` blocks.
- In Django 5.1 and later, `OPTIONS: {"transaction_mode": "IMMEDIATE"}` reduces "database is locked" errors for write transactions.

### 7.4 Cancelling a booking

Endpoint: `POST /api/bookings/<reference>/cancel/`.

1. Authenticate; load the booking **owned by the user** (404 if not found or not theirs, so existence of others' bookings is not revealed).
2. If it is already cancelled, return 409 `ALREADY_CANCELLED`.
3. If the show starts in less than 2 hours (or already started), return 409 `CANCELLATION_NOT_ALLOWED`.
4. Inside `atomic`: set `booking_status=cancelled`, `payment_status=refunded`, `cancelled_at=now`; delete the booking's `booking_seats` rows.
5. Return the updated booking. The freed seats appear as available on the next seat-map refresh.

### 7.5 Cancelling a show (admin)

Inside `atomic`: set `show.status=cancelled`; for every confirmed booking of the show, apply the cancellation steps above without the time-window check. Bookings stay in history with status `cancelled`.

### 7.6 Expired holds

- **Lazy cleanup:** expired holds are deleted whenever a hold is placed for that show and are ignored by every availability query because those filter on `expires_at > now`.
- **Optional scheduled cleanup:** `python manage.py purge_holds` deletes all expired rows; run it from cron or the Windows Task Scheduler every few minutes. No background worker such as Celery is needed.

### 7.7 Booking reference format

`CNB-YYYYMMDD-XXXX`, where `XXXX` is four random characters from an unambiguous alphabet (no 0, O, 1, I). Generation retries on the rare collision, backed by the unique constraint.

## 8. JavaScript and Django Interaction

### 8.1 General pattern

- Pages are rendered by Django. JavaScript only enhances the seat selection, summary, My Bookings, and showtime pages.
- JavaScript calls JSON endpoints with `fetch`, sending cookies (`credentials: "same-origin"`) and the CSRF token in the `X-CSRFToken` header.
- All endpoints return JSON of a fixed shape. Success: the resource data. Failure: `{ "error": { "code": "SEAT_UNAVAILABLE", "message": "...", "details": {...} } }` with a matching HTTP status.

```javascript
// static/js/api.js
function getCookie(name) {
  const m = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[2]) : null;
}

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data?.error?.message || "Request failed"), { status: res.status, error: data.error });
  return data;
}
```

### 8.2 Seat selection page

1. The template passes the show ID, price, and max seats through `data-` attributes on the page container.
2. `seatmap.js` calls `GET /api/shows/<id>/seats/` and draws the grid by row.
3. Clicking a seat toggles it in a local `selected` set (enforcing the 8-seat limit) and updates the total shown (price × count). This total is only a display; the server recomputes it.
4. Every 10 seconds the script refreshes the map. If a selected seat became booked or held by someone else, it is removed from the selection and a notice is shown.
5. **Continue** sends `POST /api/shows/<id>/holds/`. On success it navigates to `/shows/<id>/summary/`. On 409 `SEAT_UNAVAILABLE` it refreshes the map and tells the user which seats were lost.

### 8.3 Summary and payment page

1. The summary page is rendered by Django from the user's active holds. If there are none, it redirects back to seat selection with a message.
2. `countdown.js` counts down to `expires_at`. To avoid wrong device clocks, the page also receives the server's current time and uses the offset. At zero it shows the "hold expired" message.
3. `pay.js` generates an `idempotency_key` (`crypto.randomUUID()`) when the page loads, stores it in the page, and on click disables the button, then calls `POST /api/shows/<id>/bookings/` with that key.
4. On 201 or 200, it navigates to `/bookings/<reference>/confirmation/`. On 402 it re-enables the button with a message. On 409 `HOLD_EXPIRED` or `SEAT_UNAVAILABLE` it links back to seat selection.
5. On a network error, it tells the user to check My Bookings; retrying with the same key is safe.

### 8.4 Other pages

| Page | JavaScript behavior |
| --- | --- |
| Movie Details | `showtimes.js` switches the date chips and loads shows from `GET /api/movies/<id>/shows/?date=...` |
| My Bookings | `cancel.js` opens a confirmation modal and calls the cancel endpoint, then updates the card |
| Admin | Mostly plain Django forms; small scripts for confirmations and poster preview |

## 9. Authorization

| Resource | Rule | Implementation |
| --- | --- | --- |
| Seat selection, summary, My Bookings, booking APIs | Logged-in users | `@login_required`; JSON endpoints return 401 rather than redirecting |
| A booking's details | Owner only | Query filtered by `user=request.user`; else 404 |
| Admin pages and admin JSON | `role == "admin"` | `@admin_required` decorator in `core/permissions.py`; returns 403 |
| Registration | Public | Always creates `role="user"`; admins are created with `createsuperuser` or the seed command |

## 10. Security Checklist

- Use the Django ORM only; no SQL built from user input.
- Keep template auto-escaping on; never mark user text as `safe`.
- CSRF middleware enabled; all state-changing requests are POST (or DELETE) with the token.
- Passwords hashed with Argon2 or PBKDF2; minimum length 8.
- Login attempts limited (for example, 5 failures per 15 minutes per email and IP) using the `django-axes` package or a small cache-based counter.
- Server validates every input again, regardless of frontend checks.
- Never trust prices, totals, user IDs, or statuses from the client.
- Secrets in environment variables; `.env` excluded from version control.
- `DEBUG=False` and HTTPS in production.
- Generic error messages for login; avoid revealing whether an email exists.

## 11. Error Handling

- Services raise typed exceptions (`SeatUnavailable`, `HoldExpired`, `ShowNotBookable`, `PaymentFailed`, `CancellationNotAllowed`, and so on) defined in `bookings/errors.py`.
- A small wrapper converts each exception to the standard JSON error with the right HTTP status; page views convert them to messages.
- Unexpected exceptions are logged with the user ID and request path, and the user sees the 500 page or a generic JSON error.
- Custom 403, 404, and 500 templates are provided.

## 12. Performance Notes

- Use `select_related` and `prefetch_related` on lists (for example, bookings with show, movie, and theatre).
- Paginate the home page (12), My Bookings (10), and admin lists (25).
- Add the indexes listed in the Database Design.
- Compute the seat map in three queries (Section 6).
- Serve static files with `collectstatic` and WhiteNoise in production.

## 13. Testing Strategy

| Level | What to test |
| --- | --- |
| Unit (services) | Seat status computation; hold rules (limits, other user's hold, expired hold); total calculation; cancellation window; booking reference uniqueness |
| Integration (views and APIs) | Full flow: register, login, hold, confirm, view in My Bookings, cancel; every error code in the API specification |
| Concurrency | Two threads or clients confirm the same seat for the same show; exactly one succeeds and the other receives `SEAT_UNAVAILABLE` (use `TransactionTestCase`) |
| Idempotency | Posting the same key twice returns the same booking and creates one row |
| Authorization | A user cannot read or cancel another user's booking; a non-admin gets 403 on `/manage/` |
| Time-based | Use `freezegun` or patch `now()` to test hold expiry, booking cut-off, and cancellation cut-off |
| Manual | Mobile layout, seat map readability, keyboard navigation |

Target: every acceptance item in PRD Section 14 maps to at least one automated test.

## 14. Development Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # django, argon2-cffi, python-dotenv, whitenoise
cp .env.example .env              # set SECRET_KEY, DEBUG=True
python manage.py migrate
python manage.py createsuperuser  # then set role=admin
python manage.py seed_demo
python manage.py runserver
```

## 15. Suggested Build Order

| Step | Deliverable | Done when |
| --- | --- | --- |
| 1 | Project, custom user, auth pages | Register, login, and logout work |
| 2 | Catalog models, seed data, Home, Movie Details | Movies and showtimes display and search works |
| 3 | Admin pages for movies, theatres, screens, shows | Admin can create a full schedule |
| 4 | Seat map API and Seat Selection page | Seat statuses display correctly |
| 5 | Hold service and Summary page | Holds placed, expire, and block others |
| 6 | Booking service, Confirmation page | Booking saved with unique reference |
| 7 | My Bookings and cancellation | Cancel frees seats |
| 8 | Admin bookings list and show cancellation | Admin sees bookings; cancelling a show refunds |
| 9 | Error pages, validation polish, responsive fixes | Works on phone and desktop |
| 10 | Test suite, README | All success criteria verified |

## 16. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| SQLite "database is locked" errors under concurrent writes | Busy timeout, short transactions, `IMMEDIATE` transaction mode; move to PostgreSQL if usage grows |
| Users' device clocks distort the hold countdown | Countdown uses a server-time offset; the server is the only authority on expiry |
| Hold abandoned by closing the tab | Holds expire automatically after 5 minutes |
| Overlapping shows created by two admins at once | Overlap check inside a transaction; low risk in the MVP |
| Scope growth | Follow the PRD exclusions list; defer anything not in the MVP |
