# Cenebook — URL and API Specification

Version 1.0 · Companion to the PRD v1.1, Database Design, and Technical Design Document

## 1. Overview

Cenebook exposes two kinds of endpoints:

- **Page routes** return server-rendered HTML (Django templates). Forms use standard POST requests with CSRF tokens.
- **JSON API routes** (prefix `/api/`) are called by JavaScript for the interactive seat map, holds, booking, and cancellation.

All routes are served by one Django project. Business rules are described in the Technical Design Document.

## 2. Conventions

| Topic | Rule |
| --- | --- |
| Base URL | `http://localhost:8000` in development |
| Content type | JSON endpoints accept and return `application/json` |
| Authentication | Session cookie set at login |
| CSRF | Every POST and DELETE must include the CSRF token (form field `csrfmiddlewaretoken` or header `X-CSRFToken`) |
| Date and time | ISO 8601 in UTC, for example `2026-10-24T13:30:00Z`; responses also include `start_local` in the theatre's time zone |
| Money | Decimal strings with two places, for example `"300.00"`; currency is a site setting |
| IDs | Numeric IDs for movies, shows, seats, and theatres; bookings are addressed by `booking_reference` |
| Pagination (lists) | Query `?page=N`; HTML pages show page links |
| Unauthenticated JSON requests | Return 401 JSON (no redirect) |
| Unauthenticated page requests | Redirect to `/login/?next=<url>` |

### 2.1 Standard error format

Every JSON error uses this shape:

```json
{
  "error": {
    "code": "SEAT_UNAVAILABLE",
    "message": "Seat B4 is no longer available.",
    "details": { "seats": ["B4"] }
  }
}
```

`code` is stable and used by JavaScript; `message` is human-readable; `details` is optional.

## 3. Permissions Summary

| Level | Meaning |
| --- | --- |
| Public | Anyone, logged in or not |
| User | Logged-in user (any role) |
| Owner | Logged-in user, and the record belongs to them |
| Admin | Logged-in user with `role = admin` |

## 4. Page Routes

### 4.1 Public and account pages

| Method | URL | Purpose | Access | Notes |
| --- | --- | --- | --- | --- |
| GET | `/` | Home: now-showing movies | Public | `?q=` title search, `?page=` |
| GET | `/movies/<movie_id>/` | Movie details and showtimes | Public | 404 if movie archived or missing |
| GET | `/register/` | Registration form | Public | Logged-in users are redirected to `/` |
| POST | `/register/` | Create account | Public | Fields: `name`, `email`, `password`, `password_confirm` |
| GET | `/login/` | Login form | Public | Supports `?next=` |
| POST | `/login/` | Log in | Public | Fields: `email`, `password` |
| POST | `/logout/` | Log out | User | Redirects to `/` |

**Registration validation**

| Field | Rules | Error message |
| --- | --- | --- |
| name | Required, 2 to 100 characters | "Please enter your name." |
| email | Valid format, unique (case-insensitive) | "Enter a valid email." / "This email is already registered." |
| password | Minimum 8 characters, not entirely numeric | "Password must be at least 8 characters." |
| password\_confirm | Matches password | "Passwords do not match." |

**Login:** failure returns the form with "Invalid email or password." Too many failures return "Too many attempts. Try again in a few minutes." (HTTP 429).

### 4.2 Booking pages (login required)

| Method | URL | Purpose | Access | Notes |
| --- | --- | --- | --- | --- |
| GET | `/shows/<show_id>/seats/` | Seat selection | User | 404 if missing; message and redirect to the movie page if the show is closed or cancelled |
| GET | `/shows/<show_id>/summary/` | Booking summary with countdown | User | Redirects to seat selection if the user has no active holds |
| GET | `/bookings/` | My Bookings (Upcoming and Past tabs) | User | `?tab=upcoming` or `?tab=past` |
| GET | `/bookings/<reference>/` | Ticket details | Owner | 404 if not found or not the owner |
| GET | `/bookings/<reference>/confirmation/` | Confirmation after booking | Owner | Same layout as ticket details |

### 4.3 Admin pages (admin only)

All admin pages are under `/manage/`. Non-admins receive 403; logged-out users are redirected to login. If you use the built-in Django admin for catalog data, those routes live under `/admin/` instead and the Movies, Theatres, and Shows rows below are replaced by Django admin screens.

| Method | URL | Purpose |
| --- | --- | --- |
| GET | `/manage/` | Dashboard with counts and recent bookings |
| GET | `/manage/movies/` | Movie list (`?q=`, `?status=`) |
| GET, POST | `/manage/movies/new/` | Add movie |
| GET, POST | `/manage/movies/<movie_id>/edit/` | Edit movie |
| POST | `/manage/movies/<movie_id>/archive/` | Archive movie |
| POST | `/manage/movies/<movie_id>/restore/` | Restore movie to now showing |
| GET | `/manage/theatres/` | Theatres with their screens |
| GET, POST | `/manage/theatres/new/` | Add theatre |
| GET, POST | `/manage/theatres/<theatre_id>/edit/` | Edit theatre |
| GET, POST | `/manage/theatres/<theatre_id>/screens/new/` | Add screen (generates seats) |
| GET, POST | `/manage/screens/<screen_id>/edit/` | Edit screen; layout fields locked if bookings exist |
| GET | `/manage/shows/` | Show list (`?movie=`, `?theatre=`, `?date=`) |
| GET, POST | `/manage/shows/new/` | Create show |
| GET, POST | `/manage/shows/<show_id>/edit/` | Edit show |
| POST | `/manage/shows/<show_id>/cancel/` | Cancel show and refund its bookings |
| GET | `/manage/bookings/` | All bookings (`?movie=`, `?theatre=`, `?date=`, `?status=`, `?page=`) |

**Admin form rules**

| Form | Field | Validation |
| --- | --- | --- |
| Movie | title | Required, up to 200 characters |
| Movie | description | Required |
| Movie | duration | Whole number, 1 to 600 minutes |
| Movie | release date | Valid date |
| Movie | poster URL | Valid URL (optional) |
| Theatre | time zone | Valid IANA name |
| Screen | rows, seats per row | Rows 1 to 26; seats per row 1 to 30 |
| Show | start | Must be in the future when creating; must not overlap another scheduled show on the same screen (including cleaning buffer) |
| Show | price | Number, 0 or more |
| Show | edit | Screen and start cannot change if the show already has bookings; price changes do not affect existing bookings |

## 5. JSON API Endpoints

All endpoints below require the session cookie and, for POST and DELETE, the CSRF header.

### 5.1 List shows for a movie

`GET /api/movies/<movie_id>/shows/`

**Access:** Public

**Query parameters**

| Name | Required | Description |
| --- | --- | --- |
| `date` | No | `YYYY-MM-DD` in the theatre's local time. If omitted, returns the next 7 days |
| `theatre_id` | No | Limit to one theatre |

**Response 200**

```json
{
  "movie_id": 7,
  "dates": ["2026-10-24", "2026-10-25"],
  "theatres": [
    {
      "theatre_id": 2,
      "theatre_name": "PVR Pune - Kothrud",
      "shows": [
        {
          "show_id": 101,
          "screen_name": "Screen 2",
          "start_utc": "2026-10-24T13:30:00Z",
          "start_local": "2026-10-24 19:00",
          "ticket_price": "300.00",
          "availability": "available",
          "bookable": true
        }
      ]
    }
  ]
}
```

`availability` is one of `available`, `filling_fast` (under 20% of seats free), `sold_out`, or `closed` (started or past the cut-off). `bookable` is false for `sold_out` and `closed`.

**Errors**

| Status | Code | When |
| --- | --- | --- |
| 404 | `MOVIE_NOT_FOUND` | Movie missing or archived |
| 400 | `INVALID_DATE` | `date` is not a valid date |

### 5.2 Get the seat map

`GET /api/shows/<show_id>/seats/`

**Access:** User

**Response 200**

```json
{
  "show_id": 101,
  "ticket_price": "300.00",
  "max_seats": 8,
  "server_time": "2026-10-24T09:10:12Z",
  "bookable": true,
  "rows": [
    {
      "row": "A",
      "seats": [
        { "seat_id": 5001, "label": "A1", "status": "available" },
        { "seat_id": 5002, "label": "A2", "status": "booked" },
        { "seat_id": 5003, "label": "A3", "status": "held" },
        { "seat_id": 5004, "label": "A4", "status": "selected", "expires_at": "2026-10-24T09:15:02Z" }
      ]
    }
  ]
}
```

**Seat statuses:** `available`, `selected` (your active hold), `held` (someone else's hold), `booked`.

**Errors**

| Status | Code | When |
| --- | --- | --- |
| 401 | `AUTH_REQUIRED` | Not logged in |
| 404 | `SHOW_NOT_FOUND` | Show does not exist |
| 409 | `SHOW_NOT_BOOKABLE` | Show cancelled, started, or past the cut-off |

### 5.3 Place a hold on seats

`POST /api/shows/<show_id>/holds/`

**Access:** User

Replaces any holds this user already has for the show with the new set, atomically (all seats are held or none).

**Request**

```json
{ "seat_ids": [5004, 5005] }
```

| Field | Type | Rules |
| --- | --- | --- |
| `seat_ids` | array of integers | 1 to 8 unique IDs; all must belong to the show's screen |

**Response 201**

```json
{
  "show_id": 101,
  "seats": [
    { "seat_id": 5004, "label": "A4" },
    { "seat_id": 5005, "label": "A5" }
  ],
  "ticket_price": "300.00",
  "total_amount": "600.00",
  "expires_at": "2026-10-24T09:15:02Z",
  "server_time": "2026-10-24T09:10:02Z"
}
```

**Errors**

| Status | Code | When | `details` |
| --- | --- | --- | --- |
| 400 | `INVALID_SEATS` | Empty list, duplicates, non-integers, or seats from another screen |  |
| 400 | `TOO_MANY_SEATS` | More than 8 seats | `{ "max": 8 }` |
| 401 | `AUTH_REQUIRED` | Not logged in |  |
| 404 | `SHOW_NOT_FOUND` | Show does not exist |  |
| 409 | `SEAT_UNAVAILABLE` | A seat is booked or held by another user, or a race was lost | `{ "seats": ["A5"] }` |
| 409 | `SHOW_NOT_BOOKABLE` | Show cancelled, started, or past the cut-off |  |

### 5.4 Release holds

`DELETE /api/shows/<show_id>/holds/`

**Access:** User

Releases all of the user's holds for the show (for example, when they click "Change seats" or leave the summary).

**Response 204:** no body. Also returns 204 if the user had no holds.

**Errors:** 401 `AUTH_REQUIRED`; 404 `SHOW_NOT_FOUND`.

### 5.5 Confirm a booking (simulated payment)

`POST /api/shows/<show_id>/bookings/`

**Access:** User

Converts the user's active holds for the show into a confirmed booking.

**Request**

```json
{ "idempotency_key": "b4c7e0c2-3f4d-4a5e-9d3e-5d0a2d1f7a11" }
```

| Field | Type | Rules |
| --- | --- | --- |
| `idempotency_key` | string | Required, 8 to 64 characters; generated by the browser once per summary page load |

The client never sends seats, prices, or totals; they come from the server's holds.

**Response 201 (new booking) or 200 (same key already used)**

```json
{
  "booking_reference": "CNB-20261024-A7K2",
  "booking_status": "confirmed",
  "payment_status": "paid",
  "show_id": 101,
  "movie_title": "Movie Title",
  "theatre_name": "PVR Pune - Kothrud",
  "screen_name": "Screen 2",
  "start_utc": "2026-10-24T13:30:00Z",
  "start_local": "2026-10-24 19:00",
  "seats": ["A4", "A5"],
  "total_amount": "600.00",
  "created_at": "2026-10-24T09:12:40Z",
  "confirmation_url": "/bookings/CNB-20261024-A7K2/confirmation/"
}
```

**Errors**

| Status | Code | When | Holds after error |
| --- | --- | --- | --- |
| 400 | `INVALID_REQUEST` | Missing or malformed `idempotency_key` | Kept |
| 401 | `AUTH_REQUIRED` | Not logged in | Kept |
| 402 | `PAYMENT_FAILED` | Simulated payment failed | Kept until expiry |
| 404 | `SHOW_NOT_FOUND` | Show does not exist | n/a |
| 409 | `HOLD_EXPIRED` | No active holds for this user and show | None |
| 409 | `SEAT_UNAVAILABLE` | Database rejected a seat as already booked (final safeguard) | Released |
| 409 | `SHOW_NOT_BOOKABLE` | Show cancelled, started, or past the cut-off | Released |

### 5.6 Cancel a booking

`POST /api/bookings/<reference>/cancel/`

**Access:** Owner

**Request:** empty body.

**Response 200**

```json
{
  "booking_reference": "CNB-20261024-A7K2",
  "booking_status": "cancelled",
  "payment_status": "refunded",
  "refund_amount": "600.00",
  "cancelled_at": "2026-10-24T09:20:00Z"
}
```

**Errors**

| Status | Code | When |
| --- | --- | --- |
| 401 | `AUTH_REQUIRED` | Not logged in |
| 404 | `BOOKING_NOT_FOUND` | Reference unknown or not owned by the user |
| 409 | `ALREADY_CANCELLED` | Booking is already cancelled |
| 409 | `CANCELLATION_NOT_ALLOWED` | Show starts in under 2 hours, has started, or was cancelled. `details`: `{ "cutoff_hours": 2 }` |

### 5.7 Get a booking

`GET /api/bookings/<reference>/`

**Access:** Owner

Returns the same object as the confirmation response in 5.5, plus `cancelled_at` when applicable. Errors: 401 `AUTH_REQUIRED`; 404 `BOOKING_NOT_FOUND`.

## 6. Error Code Reference

| Code | HTTP | Meaning | Suggested user message |
| --- | --- | --- | --- |
| `AUTH_REQUIRED` | 401 | Not logged in or session expired | "Please log in to continue." |
| `FORBIDDEN` | 403 | Logged in without permission | "You don't have permission to do that." |
| `INVALID_REQUEST` | 400 | Malformed or missing input | "Something went wrong with your request." |
| `INVALID_DATE` | 400 | Bad date parameter | "Please choose a valid date." |
| `INVALID_SEATS` | 400 | Bad seat list | "Please select valid seats." |
| `TOO_MANY_SEATS` | 400 | More than 8 seats | "You can select up to 8 seats." |
| `PAYMENT_FAILED` | 402 | Simulated payment failed | "Payment failed. Please try again." |
| `MOVIE_NOT_FOUND` | 404 | Movie missing or archived | "This movie is not available." |
| `SHOW_NOT_FOUND` | 404 | Show missing | "This show could not be found." |
| `BOOKING_NOT_FOUND` | 404 | Booking missing or not owned | "Booking not found." |
| `SEAT_UNAVAILABLE` | 409 | Seat taken | "Seat B4 is no longer available. Please choose another." |
| `HOLD_EXPIRED` | 409 | Hold lapsed | "Your seats were released. Please select them again." |
| `SHOW_NOT_BOOKABLE` | 409 | Show closed or cancelled | "Booking for this show is closed." |
| `ALREADY_CANCELLED` | 409 | Already cancelled | "This booking is already cancelled." |
| `CANCELLATION_NOT_ALLOWED` | 409 | Outside cancellation window | "Bookings can be cancelled up to 2 hours before the show." |
| `RATE_LIMITED` | 429 | Too many requests or login attempts | "Too many attempts. Please wait and try again." |
| `SERVER_ERROR` | 500 | Unexpected failure | "Something went wrong. Please try again." |

A 500 or network failure during booking confirmation should tell the user to check My Bookings before retrying. Retrying with the same `idempotency_key` is always safe.

## 7. Endpoint-to-Requirement Traceability

| PRD requirement | Routes |
| --- | --- |
| Register, log in, log out | `/register/`, `/login/`, `/logout/` |
| Browse and search movies | `/`, `/movies/<id>/` |
| Show selection | `GET /api/movies/<id>/shows/` |
| Seat selection, prevent booked seats | `GET /api/shows/<id>/seats/`, `POST /api/shows/<id>/holds/` |
| Booking summary and confirmation | `/shows/<id>/summary/`, `POST /api/shows/<id>/bookings/`, `/bookings/<ref>/confirmation/` |
| My Bookings and cancellation | `/bookings/`, `/bookings/<ref>/`, `POST /api/bookings/<ref>/cancel/` |
| Admin: movies, theatres, shows, bookings | `/manage/...` |
| Users see only their own bookings | Owner checks on `/bookings/<ref>/`, `/api/bookings/<ref>/` |
| No double booking | Hold endpoint plus unique constraint on confirmation |

## 8. Example End-to-End Call Sequence

| Step | Request | Result |
| --- | --- | --- |
| 1 | `GET /api/movies/7/shows/?date=2026-10-24` | Showtimes listed |
| 2 | User opens `GET /shows/101/seats/` | Seat page rendered |
| 3 | `GET /api/shows/101/seats/` (repeated every 10 s) | Seat map drawn |
| 4 | `POST /api/shows/101/holds/` with `{"seat_ids":[5004,5005]}` | 201, hold for 5 minutes |
| 5 | `GET /shows/101/summary/` | Summary page with countdown |
| 6 | `POST /api/shows/101/bookings/` with an idempotency key | 201, booking reference returned |
| 7 | `GET /bookings/CNB-20261024-A7K2/confirmation/` | Confirmation page |
| 8 | `GET /bookings/` | Booking listed under Upcoming |
| 9 | `POST /api/bookings/CNB-20261024-A7K2/cancel/` | 200, refunded, seats freed |

## 9. Testing Checklist for the API

- Every endpoint returns 401 when logged out and the documented 4xx for invalid input.
- A user cannot fetch or cancel another user's booking (404).
- A non-admin receives 403 on every `/manage/` route.
- Two simultaneous holds or confirmations for the same seat: exactly one succeeds, the other gets `SEAT_UNAVAILABLE`.
- Sending the same `idempotency_key` twice creates one booking.
- Prices and totals in requests are ignored; the server's calculation is used.
- Expired holds return `HOLD_EXPIRED` on confirmation and show as `available` in the seat map.
