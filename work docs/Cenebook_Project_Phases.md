# Cenebook: Project Plan in 5 Phases

Stack: HTML, CSS, Bootstrap, JavaScript, Python Django, SQLite.
References: PRD v1.2, Wireframes and UI Design v1.1, Database Design, Technical Design Document, URL and API Specification.

## Overview

| Phase | Name | Outcome |
|---|---|---|
| 1 | Foundation and Accounts | Project runs; users can register, log in, and log out |
| 2 | Catalog and Admin | Admin can build a full schedule; users can browse movies and showtimes |
| 3 | Seat Selection and Holds | Users can see live seats and hold them without conflicts |
| 4 | Booking, My Bookings, and Cancellation | The complete booking flow works end to end |
| 5 | Polish, Testing, and Release | Apple-style UI finish, full test suite, documentation, final QA |

Each phase ends with a working, demonstrable build, so you can stop and check before moving on.

---

## Phase 1: Foundation and Accounts

**Goal:** a running Django project with a design foundation and working authentication.

### Tasks

- [ ] Create the repository, virtual environment, `requirements.txt`, `.env.example`, and `.gitignore`.
- [ ] Create the Django project and the apps: `accounts`, `catalog`, `bookings`, `adminpanel`, `core`.
- [ ] Configure settings: `AUTH_USER_MODEL`, `USE_TZ`, session and CSRF cookies, password validators, environment variables.
- [ ] Build the custom `User` model (email login, `name`, `role`, `is_active`, `created_at`) and run the first migration.
- [ ] Build `base.html`: translucent sticky navbar, message alerts, footer, dark and light color tokens, system font stack, spacing and radius variables.
- [ ] Add Bootstrap 5 and a `site.css` that overrides it with the design tokens (accent color, type scale, shapes).
- [ ] Build Register, Login, and Logout pages with frontend and backend validation.
- [ ] Add login rate limiting (for example, `django-axes` or a cache-based counter).
- [ ] Add the `admin_required` decorator in `core/permissions.py`.
- [ ] Add custom 403, 404, and 500 pages.
- [ ] Add the first lines of the README (setup steps).

### Deliverables

- Running project with auth pages, base layout, and design tokens.
- Admin account creatable via `createsuperuser`.

### Done when

- A user can register, log in, and log out.
- Wrong credentials show a generic error; repeated failures are limited.
- Registration always creates `role = user`.
- Pages look correct at 360 px and on desktop, in light and dark mode.

---

## Phase 2: Catalog and Admin

**Goal:** the data that bookings depend on exists, and users can browse it.

### Tasks

**Models and data**
- [ ] Build `Movie`, `Theatre`, `Screen`, `Seat`, and `Show` models with the constraints from the Database Design.
- [ ] Write the service that generates seats when a screen is created (rows × seats per row).
- [ ] Write the show overlap check (including the 15-minute cleaning buffer) and compute `end_datetime`.
- [ ] Write the `seed_demo` management command (movies, theatres, screens, shows, sample users).

**Public pages**
- [ ] Home page: now-showing movies in a responsive grid, title search, pagination, empty states.
- [ ] Movie Details page: poster, description, genre, language, duration, release date.
- [ ] `GET /api/movies/<id>/shows/`: dates, theatres, showtimes, price, availability labels.
- [ ] Show selection UI on Movie Details: date chips, theatre groups, showtime buttons (disabled when closed or sold out).
- [ ] Press feedback on cards and buttons (instant, 100 ms).

**Admin pages (`/manage/`)**
- [ ] Dashboard with four counts and recent bookings.
- [ ] Movies: list, add, edit, archive, restore.
- [ ] Theatres and screens: list, add, edit, seat layout generation.
- [ ] Shows: list with filters, add, edit (with locks when bookings exist), overlap validation.

### Deliverables

- An admin can create a complete schedule; a visitor can find a movie and see its showtimes.

### Done when

- Archived movies are hidden from users but remain in the database.
- Overlapping shows on one screen are rejected with a clear message.
- Showtimes appear in the theatre's local time.
- Search is case-insensitive and partial.

---

## Phase 3: Seat Selection and Holds

**Goal:** a live seat map with a conflict-free hold system. This is the technical core of the project.

### Tasks

**Backend**
- [ ] Build the `SeatHold` model with the `(show, seat)` unique constraint.
- [ ] Write the seat map query (booked, held, selected, available) in three queries.
- [ ] Write the `hold_seats` service: validate, clean up expired holds, all-or-nothing creation, `IntegrityError` handling.
- [ ] Endpoints: `GET /api/shows/<id>/seats/`, `POST /api/shows/<id>/holds/`, `DELETE /api/shows/<id>/holds/`.
- [ ] JSON error helpers and typed exceptions (`SeatUnavailable`, `ShowNotBookable`, and others).
- [ ] `purge_holds` management command (optional cleanup).

**Frontend**
- [ ] Seat Selection page: seat grid with text labels and patterns for each state.
- [ ] `seatmap.js`: render grid, select and deselect, 8-seat limit, live total, refresh every 10 seconds.
- [ ] Seat interactions: pressed state on pointer-down, 44 px touch targets, state fade on refresh.
- [ ] Mobile pan and pinch zoom with 1:1 tracking, momentum projection, and rubber-banding.
- [ ] Selection sheet with two snap points (spring 0.8 damping, 0.3 s response).
- [ ] Booking Summary page with the hold countdown and server-time offset.
- [ ] Keyboard control: arrow keys, Space or Enter.
- [ ] Conflict handling: pulse affected seats, announce to screen readers, trim selection.

### Deliverables

- A user can pick seats, see them held, and reach the summary page; another user sees those seats as held.

### Done when

- Two users cannot hold the same seat at the same time.
- A hold expires after 5 minutes and the seats become available again.
- A user can change seats, which replaces the previous hold.
- The map is usable by touch, mouse, and keyboard.

---

## Phase 4: Booking, My Bookings, and Cancellation

**Goal:** the full end-to-end flow, from browsing to a confirmed ticket and its cancellation.

### Tasks

**Booking**
- [ ] Build `Booking` and `BookingSeat` models with all constraints (`idempotency_key`, `seat_labels`, unique `(show, seat)`).
- [ ] Booking reference generator (`CNB-YYYYMMDD-XXXX`) with collision retry.
- [ ] Simulated payment module with a switch for forced failure (for tests and demos).
- [ ] `confirm_booking` service: idempotency check, atomic transaction, server-side total, convert holds to booking, delete holds.
- [ ] `POST /api/shows/<id>/bookings/` with all error codes.
- [ ] Booking Summary "Pay" flow in `pay.js`: idempotency key, disabled button, error states.
- [ ] Confirmation page with ticket details and a print stylesheet.

**My Bookings and cancellation**
- [ ] My Bookings page with Upcoming and Past tabs, status badges, and empty states.
- [ ] Ticket details page (owner only).
- [ ] `cancel_booking` service and `POST /api/bookings/<ref>/cancel/` with the 2-hour rule.
- [ ] Cancel dialog (grows from the button on desktop; bottom sheet on mobile).

**Admin**
- [ ] Bookings list with filters and pagination.
- [ ] Cancel show: cancels and refunds all of the show's bookings.
- [ ] Dashboard revenue and booking counts.

### Deliverables

- The complete flow works: register, find a movie, choose seats, pay (simulated), see the ticket, view it in My Bookings, and cancel it.

### Done when

- The same seat cannot be booked twice for the same show.
- Double-clicking Pay or refreshing creates only one booking.
- A failed payment creates no booking and keeps the hold.
- A user cannot see or cancel another user's booking.
- Cancelling frees the seats for rebooking.

---

## Phase 5: Polish, Testing, and Release

**Goal:** a finished, accessible, tested product that meets every PRD success criterion.

### Tasks

**UI polish (Apple-inspired)**
- [ ] Page transitions with the View Transitions API: slide forward and back, shared poster element.
- [ ] Translucent materials and scroll-edge fades; no translucent surface on another.
- [ ] Typography pass: size-specific tracking and leading, `rem` units, check at larger text sizes.
- [ ] Reduced motion, reduced transparency, and high contrast fallbacks tested.
- [ ] Confirmation moment (check mark draw) and haptics for confirmation and failure only.
- [ ] Run the UI Quality Checklist from the Wireframes document on every page.

**Testing**
- [ ] Unit tests for services: seat status, holds, totals, cancellation window, reference uniqueness.
- [ ] Integration tests for the full flow and every API error code.
- [ ] Concurrency test: two simultaneous bookings of one seat, exactly one succeeds (`TransactionTestCase`).
- [ ] Idempotency test: the same key twice creates one booking.
- [ ] Authorization tests: another user's booking returns 404; non-admins get 403 on `/manage/`.
- [ ] Time-based tests: hold expiry, booking cut-off, cancellation cut-off.
- [ ] Manual tests: phone, tablet, desktop; light and dark; keyboard only; screen reader spot-check.

**Release**
- [ ] SQLite settings: busy timeout and `IMMEDIATE` transaction mode.
- [ ] Production settings: `DEBUG=False`, HTTPS cookies, `ALLOWED_HOSTS`, `collectstatic`, WhiteNoise.
- [ ] Finish the README: setup, migrations, admin creation, seed data, running tests.
- [ ] Verify every item in PRD Section 14 (Success Criteria) and tick it off.
- [ ] Tag version 1.0.

### Deliverables

- A tested, documented MVP and a completed success-criteria checklist.

### Done when

- All automated tests pass, including the concurrency test.
- Every PRD success criterion is verified.
- The app works on phone and desktop, in light and dark mode, and with reduced motion on.
- A new developer can set up and run the project from the README alone.

---

## Dependencies Between Phases

```
Phase 1 --> Phase 2 --> Phase 3 --> Phase 4 --> Phase 5
 accounts     data       holds      bookings    polish
 + design   + schedule   + seats    + cancel    + tests
```

- Phase 2 needs the user model and admin permission from Phase 1.
- Phase 3 needs shows, screens, and seats from Phase 2.
- Phase 4 needs holds from Phase 3.
- Phase 5 depends on all earlier phases but can begin earlier for UI polish on finished pages.

## Risks to Watch

| Risk | Phase | Mitigation |
|---|---|---|
| Custom user model added too late | 1 | Set `AUTH_USER_MODEL` before the first migration |
| Seat map gesture code takes longer than expected | 3 | Ship tap-only selection first, then add pan, zoom, and sheet |
| SQLite "database is locked" under concurrent writes | 3, 4 | Busy timeout, short transactions, `IMMEDIATE` mode |
| Scope creep | All | Follow the PRD exclusions list |
| Motion and materials delay the core flow | 5 | Core flow works without them; add them as enhancements |

## Suggested Working Rules

- Finish and demo each phase before starting the next.
- Keep business rules in service functions; views stay thin.
- Write tests for each service as you build it, not only in Phase 5.
- Commit at the end of every task; tag at the end of every phase (`phase-1` to `phase-5`).
