# Cenebook — Product Requirements Document (PRD)

**Version:** 1.2 (aligned with the wireframes, database design, technical design, and API specification)

## 1. Product Overview

**Product Name:** Cenebook

**Product Type:** Movie ticket booking web application

**Purpose:** Cenebook lets users browse currently available movies, check showtimes, select seats, and book tickets online. Administrators manage movies, theatres, and shows.

## 2. Problem Statement

Booking movie tickets manually or through cluttered interfaces is inconvenient. Users need a simple platform where they can find a movie, pick a suitable showtime, choose seats, and receive a confirmed ticket. Cenebook makes this process straightforward and reliable.

## 3. Product Objectives

- Display currently available movies.
- Let users view movie details and showtimes.
- Let users select available seats without conflicts.
- Enable users to book tickets and receive a booking confirmation.
- Let users view and cancel their bookings (within defined rules).
- Provide an admin interface to manage movies, theatres, shows, and bookings.

## 4. Target Users

- **Moviegoers:** people who regularly watch movies in theatres, including students and working professionals who prefer booking online.
- **Administrators:** staff who manage movies, theatres, screens, and show schedules.

## 5. Assumptions and Open Decisions

These must be settled before development begins. Defaults are given so work is not blocked.

| # | Item | Default for MVP |
|---|---|---|
| 1 | Currency | Single currency, configured in one place (e.g., INR) |
| 2 | Cancellation window | Allowed until 2 hours before show start; full simulated refund |
| 3 | Booking cut-off | Booking closes 15 minutes before show start |
| 4 | Max seats per booking | 8 |
| 5 | Seat hold during checkout | 5-minute hold once the user proceeds to the summary page |
| 6 | Admin account creation | Seeded manually/by script; the public registration form only creates `user` accounts |
| 7 | Time zone | Each theatre has a time zone; all times are stored in UTC and displayed in the theatre's local time |
| 8 | Technology stack | HTML, CSS, Bootstrap, JavaScript frontend; Python Django backend; SQLite database (see Section 9) |
| 9 | Cleaning buffer between shows | 15 minutes; a show's end time is movie duration plus this buffer, and shows on the same screen must not overlap including the buffer |
| 10 | Seat map refresh | The seat map refreshes automatically about every 10 seconds so other users' bookings and holds appear |
| 11 | "Filling fast" threshold | A show is labeled "filling fast" when fewer than 20% of its seats remain |

## 6. Core Features

### 6.1 User Authentication

- Registration with name, email, and password; email must be unique.
- Login and logout; sessions (or tokens) expire after a defined period of inactivity.
- Password rules: minimum 8 characters.
- Frontend and backend input validation.
- Passwords stored using a strong salted hash (bcrypt or argon2).
- Basic protection against brute-force login attempts (rate limiting or temporary lockout).
- Password reset is out of scope for the MVP.

### 6.2 Home Page

- Display movies with status "now showing" (see Movies table).
- Show poster, title, genre, and language for each movie.
- Search bar to find movies by title (case-insensitive, partial match).
- Show a friendly empty state when no movies match.
- Clicking a movie opens its details page.

### 6.3 Movie Details

Each movie details page displays:

- Title and poster.
- Description.
- Genre and language.
- Duration.
- Release date.
- Upcoming showtimes, grouped by theatre and date (see 6.4).

### 6.4 Show Selection

Show selection is part of the Movie Details page, not a separate page.

- User selects a theatre/cinema from those currently screening the movie.
- User selects a date (only dates with upcoming shows are shown).
- Showtimes display the ticket price and a seat-availability indicator (available, filling fast, or sold out; "filling fast" means fewer than 20% of seats remain).
- Shows that have started, are past the booking cut-off, or are sold out are visible but disabled.
- Selecting a showtime proceeds to Seat Selection (login required; unauthenticated users are redirected to login and returned to the same show afterward).

### 6.5 Seat Selection

- Display a seating layout for the show's screen, with rows and seat numbers.
- Seats appear in distinct colors/styles for **available**, **selected**, **held by another user**, and **booked**. Do not rely on color alone (use labels or patterns for accessibility).
- User can select one or more available seats, up to the per-booking maximum.
- Total price updates instantly as seats are selected or deselected.
- Booked and held seats cannot be selected.
- The seat map refreshes automatically about every 10 seconds. If a seat the user selected becomes booked or held by someone else, it is removed from their selection and they are notified.
- Seat availability is re-validated on the server when the user proceeds; if a chosen seat is no longer available, the user is told which seat and returned to selection.

### 6.6 Ticket Booking

- Booking summary shows: movie, theatre, screen, date, showtime, selected seats, price per seat, and total.
- Seats are held for the user for the hold duration (5 minutes by default); a visible countdown is shown. On expiry, seats are released and the user is returned to seat selection.
- For the MVP, payment is simulated: the user clicks "Pay", and the system records a successful payment. Failure simulation should also be supported so the failure path can be tested. A failed payment creates no booking, shows a clear message, and keeps the user's seat hold until it expires so they can retry.
- Booking creation is atomic: seat reservation, payment record, and booking record are saved in a single transaction. If any step fails, nothing is saved and held seats are released.
- Confirmation requests must be idempotent so double-clicking or refreshing does not create duplicate bookings.
- On success, generate a unique, human-readable booking reference (e.g., `CNB-20261024-A7K2`) and show the confirmation page.

### 6.7 My Bookings

- Show the logged-in user's bookings, split into **Upcoming** and **Past**.
- Each entry shows booking reference, movie, theatre, date/time, seats, total, and status.
- User can open the full ticket confirmation.
- Cancel option appears only when allowed by the cancellation rules (Section 5). Cancelling sets the booking to `cancelled`, marks the payment as refunded (simulated), and releases the seats for rebooking.
- A user can only view and cancel their own bookings.

### 6.8 Admin Panel

Administrators can:

- **Movies:** add, edit, and archive movies. A movie that has shows or bookings is archived (hidden from users) rather than deleted, so booking history stays intact.
- **Theatres and screens:** add and edit theatres (name, location, time zone) and their screens, including each screen's seat layout (rows and seats per row).
- **Shows:** create and update shows (movie, screen, start date/time, ticket price). Prevent overlapping shows on the same screen (including the cleaning buffer). Shows with confirmed bookings cannot be deleted; they can be cancelled (see below), and price/time changes do not affect existing bookings.
- **Show cancellation:** cancelling a show cancels all its bookings and marks payments as refunded (simulated).
- **Bookings:** view all bookings with filters (movie, theatre, date, status).
- **Dashboard:** show simple counts only: total movies, upcoming shows, bookings today, and revenue today, plus a list of recent bookings. Charts and analytics are out of scope.
- Admin pages are accessible only to users with the `admin` role, enforced on the server.

## 7. Booking Workflow

1. User opens Cenebook.
2. User browses or searches for a movie.
3. User opens the movie details page.
4. User selects a theatre, date, and showtime.
5. If not logged in, user logs in or registers and returns to the selected show.
6. User selects available seats.
7. System holds the seats and shows the booking summary.
8. User completes (simulated) payment within the hold period.
9. System confirms the booking, saves it, and generates a booking reference.
10. User views the booking on the confirmation page and later in My Bookings.

## 8. Pages Required

| Page | Purpose |
|---|---|
| Home | Browse and search available movies |
| Register | Create a new account |
| Login | Access an existing account |
| Movie Details | View information; choose theatre, date, and showtime |
| Seat Selection | Select available seats |
| Booking Summary | Review details and pay (simulated) |
| Booking Confirmation | Display confirmed ticket details |
| My Bookings | View upcoming and past bookings; cancel |
| Admin Dashboard | Overview and navigation for admin tasks |
| Admin: Movies | Add, edit, archive movies |
| Admin: Theatres and Screens | Manage theatres, screens, and seat layouts |
| Admin: Shows | Create and manage shows |
| Admin: Bookings | View and filter bookings |
| Error pages | 404, 403 (not authorized), and general error |

## 9. Technology Stack

The stack is fixed for the MVP.

| Layer | Choice | Notes |
|---|---|---|
| Frontend | HTML, CSS, Bootstrap, JavaScript | Django templates render pages; Bootstrap provides the responsive layout; plain JavaScript handles the seat map, live total, and hold countdown. |
| Backend | Python with Django | Django views, forms, and models implement the application logic. |
| Database | SQLite | Zero-setup file database, suitable for development and a low-traffic MVP. |
| Authentication | Django's built-in authentication | Session-based login, password hashing, and CSRF protection are included. |
| Admin | Django admin or custom admin pages | Django admin can cover movies, theatres, screens, and shows quickly; custom pages are needed for the booking filters and show cancellation workflow if the built-in admin is not enough. |
| Payment | Simulated | A real gateway can be added later behind the same payment interface. |

**Django conventions**
- Use Django's built-in `User` model (extended via a profile or custom user model for the `role` field, or use `is_staff` for admins).
- Define all tables in Section 10 as Django models and manage schema changes with migrations.
- Keep `USE_TZ = True` so datetimes are stored in UTC.
- Use `DecimalField` for money.
- Serve JavaScript requests (seat availability, holds) through Django views returning JSON, with CSRF tokens included.

**SQLite considerations for double-booking prevention**
- SQLite enforces unique constraints and supports transactions, so the `(show_id, seat_id)` unique constraint works as designed and is the final safeguard against double booking.
- Wrap booking creation in `transaction.atomic()` and treat a unique-constraint failure (`IntegrityError`) as "seat already taken", returning a clear message to the user.
- Do not rely on `select_for_update()`; SQLite ignores row locking, and it permits only one writer at a time. This is acceptable for the MVP.
- Enable foreign key enforcement (Django does this by default) and keep write transactions short.
- If traffic grows or multiple servers are needed, migrate to PostgreSQL or MySQL; the Django models should require no major changes.

## 10. Database Design

Conventions: implement each table as a Django model; use `DecimalField` for money (never floats), store timestamps in UTC, and use `choices` for statuses. `DECIMAL` below means Django `DecimalField`.

### Users
- user_id (PK)
- name
- email (unique)
- password_hash
- role (`user` | `admin`)
- is_active (disabled users cannot log in)
- created_at

### Movies
- movie_id (PK)
- title
- description
- genre
- language
- duration_minutes
- release_date
- poster_url
- status (`now_showing` | `archived`)

### Theatres
- theatre_id (PK)
- theatre_name
- location
- time_zone
- is_active (inactive theatres are hidden)

### Screens
- screen_id (PK)
- theatre_id (FK)
- screen_name

### Seats
- seat_id (PK)
- screen_id (FK)
- row_label
- seat_number
- Unique on (screen_id, row_label, seat_number)

### Shows
- show_id (PK)
- movie_id (FK)
- screen_id (FK)
- start_datetime (UTC)
- end_datetime (UTC)
- ticket_price (DECIMAL)
- status (`scheduled` | `cancelled`)

### Bookings
- booking_id (PK)
- booking_reference (unique, human-readable)
- user_id (FK)
- show_id (FK)
- created_at
- total_amount (DECIMAL; price captured at time of booking)
- booking_status (`confirmed` | `cancelled`)
- payment_status (`paid` | `failed` | `refunded`)
- cancelled_at (nullable)
- seat_labels (text snapshot such as "B3,B4", so a cancelled booking still shows its seats)
- idempotency_key (client-generated; unique together with user_id, so repeated confirmations return the same booking)

### Booking Seats
- booking_seat_id (PK)
- booking_id (FK)
- seat_id (FK)
- show_id (FK)
- **Unique constraint on (show_id, seat_id)**

When a booking is cancelled, its Booking Seats rows are deleted (the seat list remains visible through the booking's `seat_labels`), so the unique constraint applies only to active reservations and cancelled seats can be rebooked.

### Seat Holds
- hold_id (PK)
- user_id (FK)
- show_id (FK)
- seat_id (FK)
- created_at
- expires_at
- **Unique constraint on (show_id, seat_id)**

Expired holds are ignored when checking availability and cleaned up periodically. Booking a seat must verify the user's own active hold, then convert it to a booking inside one transaction.

### Recommended indexes
- Shows: (movie_id, start_datetime) and (screen_id, start_datetime)
- Bookings: (user_id, created_at)
- Movies: (title)

## 11. Functional Requirements

- Users must be able to register, log in, and log out.
- Movie listings must be retrieved from the database.
- Only upcoming, scheduled shows before their booking cut-off can be booked.
- Users cannot select or book seats that are booked or held by someone else.
- The total price must update as seats are selected, and the server must recompute it independently; client-submitted prices are never trusted.
- A confirmed booking must be saved in the database along with its seats and payment status.
- Users can only view and cancel their own bookings.
- Only administrators can access admin functions; authorization is checked on every admin request on the server.
- Cancelling a booking or a show releases the seats and updates statuses.

## 12. Non-Functional Requirements

**Usability and compatibility**
- Responsive on desktop and mobile.
- Errors are shown clearly and in user-friendly language.
- Basic accessibility: keyboard navigation, sufficient color contrast, and labels on seat states.

**Security**
- Passwords securely hashed; HTTPS in production.
- Input validated on both frontend and backend.
- Protection against SQL injection (use the Django ORM; no raw string-built SQL), XSS (Django template auto-escaping), and CSRF (Django's CSRF middleware).
- Authorization checks ensure users cannot access other users' bookings by changing IDs in URLs.
- Secrets (database credentials, session keys) kept in environment variables, not in code.

**Reliability and data integrity**
- Double-booking is prevented at the database level (unique constraint) and in application logic (`transaction.atomic()`).
- Concurrent attempts to book the same seat result in exactly one success and a clear message for the other.
- Booking confirmation is idempotent.

**Performance (normal usage)**
- Main pages load in under 3 seconds on a typical connection.
- Seat map loads and booking confirmation completes in under 2 seconds under normal load.

## 13. MVP Scope

### Included in Version 1

- User registration and login.
- Movie listing and search by title.
- Movie details, theatre/date/showtime selection.
- Seat selection with short-term seat holds.
- Booking summary and confirmation with a unique booking reference.
- Simulated payment.
- My Bookings with cancellation.
- Basic admin dashboard (movies, theatres/screens, shows, bookings).

### Excluded from Version 1

- Real payment gateway integration.
- Multi-city discovery, location-based recommendations, and geolocation (theatres are chosen from a simple list).
- Password reset and social login.
- Coupons and loyalty points.
- Reviews and ratings.
- AI-based movie recommendations.
- Email, SMS, and push notifications.
- Complex analytics dashboards.
- Variable seat pricing (e.g., premium or recliner seats); one price per show.

## 14. Success Criteria

The MVP is complete when:

- A user can register, log in, and log out successfully.
- A user can find a movie, choose a theatre and showtime, and select seats.
- The displayed total matches the server-calculated total.
- The system confirms a booking and saves it, with its seats, in the database.
- The same seat cannot be booked twice for the same show, verified by a test in which two users attempt to book the same seat simultaneously and exactly one succeeds.
- Held seats expire and become available again after the hold period.
- A user can view their upcoming and past bookings and cancel an eligible one, after which the seats can be rebooked.
- A non-admin user cannot access admin pages or APIs.
- An administrator can manage movies, theatres/screens, and shows, and view bookings.
- Shows past their booking cut-off cannot be booked.

## 15. Future Enhancements

After the MVP is stable: migrating from SQLite to PostgreSQL or MySQL, real online payments, email confirmations and e-tickets with QR codes, password reset, refined cancellation and refund policies, variable seat pricing, movie ratings and reviews, and multi-city support.

## 16. Final Product Vision

Cenebook should be a simple, reliable, and user-friendly movie ticket booking application that demonstrates the complete booking process, from browsing movies to receiving a confirmed ticket.

The primary focus is a working end-to-end booking flow, correct seat availability, and clean database design rather than a large number of features.
