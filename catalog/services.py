"""
catalog/services.py
All business logic for the catalog: seat generation, show overlap,
end-datetime calculation, and seat availability labels.
"""
import datetime
import string

from django.conf import settings
from django.utils import timezone


# ── Seat Generation ──────────────────────────────────────────────────────────

def generate_seats(screen):
    """Bulk-create Seat rows for *screen* using its rows × seats_per_row dimensions."""
    from .models import Seat

    row_letters = string.ascii_uppercase
    seats = [
        Seat(
            screen=screen,
            row_label=row_letters[row_idx],
            seat_number=seat_num,
        )
        for row_idx in range(screen.rows)
        for seat_num in range(1, screen.seats_per_row + 1)
    ]
    Seat.objects.bulk_create(seats, ignore_conflicts=True)


# ── Show Timing ───────────────────────────────────────────────────────────────

def compute_end_datetime(movie, start_datetime):
    """Return end_datetime = start + duration + cleaning buffer (UTC)."""
    buffer = getattr(settings, "CLEANING_BUFFER_MINUTES", 15)
    return start_datetime + datetime.timedelta(minutes=movie.duration_minutes + buffer)


def check_show_overlap(screen, start_dt, end_dt, exclude_show_id=None):
    """Return True if a *scheduled* show on *screen* overlaps [start_dt, end_dt)."""
    from .models import Show

    qs = Show.objects.filter(
        screen=screen,
        status=Show.STATUS_SCHEDULED,
        start_datetime__lt=end_dt,
        end_datetime__gt=start_dt,
    )
    if exclude_show_id:
        qs = qs.exclude(pk=exclude_show_id)
    return qs.exists()


def local_to_utc(date, time, tz_str):
    """Combine a local date + time in *tz_str* and return a UTC-aware datetime."""
    from zoneinfo import ZoneInfo

    local_dt = datetime.datetime.combine(date, time).replace(tzinfo=ZoneInfo(tz_str))
    return local_dt.astimezone(datetime.timezone.utc)


# ── Availability ──────────────────────────────────────────────────────────────

def get_availability_label(show):
    """
    Return one of: 'available', 'filling_fast', 'sold_out', 'closed'.
    'closed' means the show has started, is past the booking cut-off, or is cancelled.
    """
    cutoff_minutes = getattr(settings, "BOOKING_CUTOFF_MINUTES", 15)
    filling_threshold = getattr(settings, "FILLING_FAST_THRESHOLD", 0.20)

    cutoff_dt = show.start_datetime - datetime.timedelta(minutes=cutoff_minutes)

    if show.status == "cancelled" or timezone.now() >= cutoff_dt:
        return "closed"

    total = show.screen.seats.count()
    if total == 0:
        return "sold_out"

    # Booked count — graceful if bookings app not yet available
    try:
        from bookings.models import BookingSeat
        booked = BookingSeat.objects.filter(show=show).count()
    except Exception:
        booked = 0

    remaining = total - booked
    if remaining <= 0:
        return "sold_out"
    if remaining / total < filling_threshold:
        return "filling_fast"
    return "available"
