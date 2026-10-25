# Cenebook — Database Design

Version 1.0 · Companion to the Cenebook PRD v1.1 · Target: Django ORM on SQLite

## 1. Purpose

This document defines the Cenebook data model: tables, columns, relationships, constraints, and the business rules the database enforces. Each table is implemented as a Django model, and schema changes are applied through Django migrations.

**Change from PRD v1.1:** the `Bookings` table gains an `idempotency_key` column (Section 5.8) so that repeated confirmation requests, such as a double-click, cannot create duplicate bookings.

## 2. Conventions

| Topic | Rule |
| --- | --- |
| Table names | Plural snake\_case in this document; Django generates `app_model` names automatically |
| Primary keys | Auto-incrementing integers (`BigAutoField`) |
| Money | `DecimalField(max_digits=10, decimal_places=2)`; never floats |
| Timestamps | Stored in UTC (`USE_TZ = True`); shown in the theatre's time zone |
| Statuses | Django `choices` backed by short text values |
| Deletion | Movies, theatres, screens, and shows are never hard-deleted once referenced; they are archived or cancelled |
| Foreign keys | `on_delete=PROTECT` for historical data (shows, bookings) so records cannot vanish accidentally |

## 3. Entity Relationship Diagram

```
                    +----------+
                    |  users   |
                    +----+-----+
                         | 1
               +---------+----------+
               | N                  | N
         +-----+------+      +------+-------+
         |  bookings  |      |  seat_holds  |
         +-----+------+      +------+-------+
               | 1                  | N
               | N                  |
      +--------+--------+           |
      |  booking_seats  |           |
      +---+---------+---+           |
          | N       | N             | N
          |         |               |
          |    +----+------+  N   1  |
          |    |   seats   +--------+
          |    +----+------+
          |         | N
          |         | 1
   N      |    +----+------+  1   N  +------------+
   +------+    |  screens  +---------+  theatres  |
   |           +----+------+         +------------+
   |                | 1
   |                | N
+--+-----+      +----+------+  N   1  +----------+
| shows  +------+  (screen) |         |  movies  |
+--------+  N  1                      +----+-----+
   |  N ----------------------------- 1 ---+
```

The diagram above is a sketch; the precise relationships are listed in Section 4.

## 4. Relationships

| Parent (one) | Child (many) | Via | Rule |
| --- | --- | --- | --- |
| users | bookings | `bookings.user_id` | A user has many bookings |
| users | seat\_holds | `seat_holds.user_id` | A user may hold several seats at once |
| movies | shows | `shows.movie_id` | A movie has many shows |
| theatres | screens | `screens.theatre_id` | A theatre has one or more screens |
| screens | seats | `seats.screen_id` | A screen has a fixed set of seats |
| screens | shows | `shows.screen_id` | A screen hosts many shows over time |
| shows | bookings | `bookings.show_id` | A show has many bookings |
| shows | seat\_holds | `seat_holds.show_id` | Temporary holds are per show |
| bookings | booking\_seats | `booking_seats.booking_id` | A booking reserves one or more seats |
| seats | booking\_seats | `booking_seats.seat_id` | A seat can be booked in many shows (not the same show twice) |
| shows | booking\_seats | `booking_seats.show_id` | Denormalised so uniqueness can be enforced |

**Many-to-many:** bookings and seats are related through `booking_seats`. Shows and seats are related through `booking_seats` and `seat_holds`.

## 5. Data Dictionary

### 5.1 users

Implemented as a custom user model extending Django's `AbstractUser`, with email as the login field.

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| user\_id | BigAutoField | No | PK | Unique user ID |
| name | CharField(100) | No |  | Display name |
| email | EmailField(254) | No | Unique | Login identifier; stored lowercase |
| password\_hash | CharField(128+) | No |  | Django-hashed password (PBKDF2, bcrypt, or argon2) |
| role | CharField(10) | No | `user` or `admin`; default `user` | Authorization level |
| is\_active | Boolean | No | Default true | Disabled users cannot log in |
| created\_at | DateTimeField | No | auto | Registration time |

### 5.2 movies

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| movie\_id | BigAutoField | No | PK | Unique movie ID |
| title | CharField(200) | No | Indexed | Title |
| description | TextField | No |  | Synopsis |
| genre | CharField(100) | No |  | Genre label (for example, Action) |
| language | CharField(50) | No |  | Language label |
| duration\_minutes | PositiveSmallInteger | No | > 0 | Running time |
| release\_date | DateField | No |  | Release date |
| poster\_url | URLField | Yes |  | Poster image URL |
| status | CharField(12) | No | `now_showing` or `archived`; default `now_showing` | Visibility to users |

### 5.3 theatres

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| theatre\_id | BigAutoField | No | PK | Unique theatre ID |
| theatre\_name | CharField(150) | No |  | Cinema name |
| location | CharField(255) | No |  | Address or area |
| time\_zone | CharField(64) | No | Valid IANA name; default `Asia/Kolkata` | Used to display show times |
| is\_active | Boolean | No | Default true | Inactive theatres are hidden |

### 5.4 screens (new in v1.1)

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| screen\_id | BigAutoField | No | PK | Unique screen ID |
| theatre\_id | ForeignKey(theatres) | No | PROTECT | Owning theatre |
| screen\_name | CharField(50) | No | Unique with theatre\_id | For example, Screen 2 |

### 5.5 seats

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| seat\_id | BigAutoField | No | PK | Unique seat ID |
| screen\_id | ForeignKey(screens) | No | PROTECT | The screen this seat belongs to |
| row\_label | CharField(2) | No |  | Row letter (A, B, ...) |
| seat\_number | PositiveSmallInteger | No | > 0 | Seat position in the row |

**Unique:** (`screen_id`, `row_label`, `seat_number`). Seats are generated automatically when an admin creates a screen with a number of rows and seats per row.

### 5.6 shows

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| show\_id | BigAutoField | No | PK | Unique show ID |
| movie\_id | ForeignKey(movies) | No | PROTECT | Movie being screened |
| screen\_id | ForeignKey(screens) | No | PROTECT | Where it is screened |
| start\_datetime | DateTimeField | No | UTC | Start time |
| end\_datetime | DateTimeField | No | > start\_datetime | Calculated from duration plus buffer |
| ticket\_price | DecimalField(10,2) | No | >= 0 | Price per seat |
| status | CharField(10) | No | `scheduled` or `cancelled`; default `scheduled` | Show state |

**Rule:** two scheduled shows on the same screen must not overlap in time. SQLite cannot enforce this with a constraint, so it is checked in `Show.clean()` and in the admin service layer inside a transaction.

### 5.7 seat\_holds (new in v1.1)

Temporary reservations created when a user proceeds from seat selection to the summary page.

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| hold\_id | BigAutoField | No | PK | Unique hold ID |
| user\_id | ForeignKey(users) | No | CASCADE | Who holds the seat |
| show\_id | ForeignKey(shows) | No | CASCADE | The show |
| seat\_id | ForeignKey(seats) | No | CASCADE | The held seat |
| created\_at | DateTimeField | No | auto | When the hold started |
| expires\_at | DateTimeField | No | Indexed | Hold end (created\_at + 5 minutes) |

**Unique:** (`show_id`, `seat_id`). A seat can have at most one hold row at any time. An expired row is treated as free: it is deleted or overwritten when someone else holds the seat.

### 5.8 bookings

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| booking\_id | BigAutoField | No | PK | Internal ID |
| booking\_reference | CharField(20) | No | Unique | Public ID, for example `CNB-20261024-A7K2` |
| user\_id | ForeignKey(users) | No | PROTECT | Owner |
| show\_id | ForeignKey(shows) | No | PROTECT | Booked show |
| created\_at | DateTimeField | No | auto | Booking time (the PRD's booking\_date) |
| total\_amount | DecimalField(10,2) | No | >= 0 | Price captured at booking time |
| booking\_status | CharField(10) | No | `confirmed` or `cancelled` | Booking state |
| payment\_status | CharField(10) | No | `paid`, `failed`, or `refunded` | Simulated payment state |
| cancelled\_at | DateTimeField | Yes |  | When cancelled |
| idempotency\_key | CharField(64) | No | Unique with user\_id | Client-generated token; repeated submits return the same booking |

**Note on failed payments:** a failed simulated payment does not create a booking row. `failed` is retained for audit if you choose to log failed attempts later.

### 5.9 booking\_seats

| Column | Type | Null | Constraints | Description |
| --- | --- | --- | --- | --- |
| booking\_seat\_id | BigAutoField | No | PK | Row ID (Django needs a single-column key) |
| booking\_id | ForeignKey(bookings) | No | CASCADE | Parent booking |
| seat\_id | ForeignKey(seats) | No | PROTECT | The reserved seat |
| show\_id | ForeignKey(shows) | No | PROTECT | Same show as the booking (denormalised) |

**Unique:** (`show_id`, `seat_id`) — the final safeguard against double booking.

**Cancellation:** when a booking is cancelled, its `booking_seats` rows are deleted so the seats can be sold again. To retain the seat list for the ticket history, store it in `bookings.seat_labels` (a text snapshot such as "B3,B4") when the booking is created.

**Addition:** `bookings.seat_labels` (CharField(255), not null) holds the seat snapshot described above.

## 6. Integrity Rules

### 6.1 Enforced by the database

| Rule | Mechanism |
| --- | --- |
| One account per email | Unique on `users.email` |
| A seat cannot be sold twice for a show | Unique on `booking_seats (show_id, seat_id)` |
| A seat has at most one active hold per show | Unique on `seat_holds (show_id, seat_id)` |
| Seat labels unique within a screen | Unique on `seats (screen_id, row_label, seat_number)` |
| Booking references are unique | Unique on `bookings.booking_reference` |
| Repeated submits do not duplicate bookings | Unique on `bookings (user_id, idempotency_key)` |
| Historical records cannot be removed | `PROTECT` foreign keys |

### 6.2 Enforced by application logic

| Rule | Where |
| --- | --- |
| Shows on the same screen must not overlap | `Show.clean()` and admin service |
| Booking only for scheduled shows before the cut-off (15 minutes before start) | Booking service |
| Maximum 8 seats per booking | Hold service and booking service |
| The seats booked belong to the show's screen | Booking service |
| The user confirming holds the seats | Booking service |
| Total is recalculated on the server as price × seats | Booking service |
| Cancellation allowed only until 2 hours before start | Cancellation service |
| Seat layout locked once bookings exist for the screen | Admin service |
| Only `admin` users manage movies, theatres, and shows | Permission decorators |

## 7. Status Values

| Entity | Field | Values | Transitions |
| --- | --- | --- | --- |
| Movie | status | `now_showing`, `archived` | Either direction, by admin |
| Show | status | `scheduled`, `cancelled` | scheduled → cancelled |
| Booking | booking\_status | `confirmed`, `cancelled` | confirmed → cancelled |
| Booking | payment\_status | `paid`, `failed`, `refunded` | paid → refunded |

## 8. Indexes

| Table | Index | Purpose |
| --- | --- | --- |
| movies | `title` | Title search |
| movies | `status` | Home page filter |
| shows | `(movie_id, start_datetime)` | Showtimes for a movie |
| shows | `(screen_id, start_datetime)` | Overlap checks |
| bookings | `(user_id, created_at)` | My Bookings |
| bookings | `booking_reference` (unique) | Ticket lookup |
| booking\_seats | `(show_id, seat_id)` (unique) | Seat map and double-booking guard |
| seat\_holds | `(show_id, seat_id)` (unique) | Seat map |
| seat\_holds | `expires_at` | Cleanup of expired holds |

## 9. Derived Data: Seat Status for a Show

Seat status is not stored. It is computed per seat for a given show:

1. If the seat appears in `booking_seats` for the show: **booked**.
2. Else if it appears in `seat_holds` for the show with `expires_at` in the future: **held** (shown as **selected** to the user who owns the hold).
3. Otherwise: **available**.

This is a single query joining `seats` for the show's screen with `booking_seats` and `seat_holds`, so the data always has one source of truth.

## 10. Django Model Sketch

```python
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=[("user", "User"), ("admin", "Admin")], default="user")
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.PROTECT)
    screen = models.ForeignKey(Screen, on_delete=models.PROTECT)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, default="scheduled")

class SeatHold(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["show", "seat"], name="uniq_hold_show_seat")]

class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)
    show = models.ForeignKey(Show, on_delete=models.PROTECT)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["show", "seat"], name="uniq_booking_show_seat")]
```

The remaining models follow the data dictionary above.

## 11. Sample Data for Development

A Django management command (`python manage.py seed_demo`) should create:

- 1 admin user and 2 normal users
- 8 movies (6 now showing, 2 archived)
- 2 theatres with 2 screens each (for example, 8 rows × 12 seats)
- Shows for the next 7 days, 3 per screen per day
- A few confirmed and cancelled bookings, for testing My Bookings and the admin list

## 12. Open Points

| Point | Suggested decision |
| --- | --- |
| Store payment attempts separately? | Not in MVP; add a `payments` table when a real gateway is integrated |
| Seat categories (premium, recliner)? | Out of scope for MVP; later, add `seat_type` and a price per type |
| Soft-delete users? | Use `is_active=false`; do not delete users who have bookings |
| SQLite to PostgreSQL later? | Models are portable; add an exclusion constraint for show overlap when moving |
