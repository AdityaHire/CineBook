import datetime
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone

from catalog.models import Show, Seat
from .models import SeatHold, BookingSeat
from .errors import ShowNotBookable, InvalidSeats, TooManySeats, SeatUnavailable


def get_seat_map_data(show, user=None):
    """
    Return seat map matrix grouped by row in 3 database queries.
    Status per seat:
      - 'booked' if in BookingSeat for this show
      - 'selected' if in SeatHold for this show and held by the requesting user
      - 'held' if in SeatHold for this show and held by someone else
      - 'available' otherwise
    """
    now = timezone.now()
    seats = Seat.objects.filter(screen=show.screen).order_by("row_label", "seat_number")
    booked_seat_ids = set(
        BookingSeat.objects.filter(show=show).values_list("seat_id", flat=True)
    )
    active_holds = SeatHold.objects.filter(show=show, expires_at__gt=now)
    held_map = {h.seat_id: (h.user_id, h.expires_at) for h in active_holds}

    user_id = user.id if user and user.is_authenticated else None

    # Group seats into rows
    rows_dict = {}
    for seat in seats:
        row = seat.row_label
        if row not in rows_dict:
            rows_dict[row] = []

        if seat.id in booked_seat_ids:
            status = "booked"
            expires_at = None
        elif seat.id in held_map:
            holder_id, exp = held_map[seat.id]
            if user_id and holder_id == user_id:
                status = "selected"
                expires_at = exp.isoformat()
            else:
                status = "held"
                expires_at = None
        else:
            status = "available"
            expires_at = None

        seat_info = {
            "seat_id": seat.id,
            "label": seat.label,
            "row": seat.row_label,
            "number": seat.seat_number,
            "status": status,
        }
        if expires_at:
            seat_info["expires_at"] = expires_at

        rows_dict[row].append(seat_info)

    rows_list = [{"row": r, "seats": seats_in_row} for r, seats_in_row in rows_dict.items()]

    return {
        "show_id": show.id,
        "ticket_price": f"{float(show.ticket_price):.2f}",
        "max_seats": getattr(settings, "MAX_SEATS_PER_BOOKING", 8),
        "server_time": now.isoformat(),
        "bookable": show.is_bookable,
        "rows": rows_list,
    }


def hold_seats(show, user, seat_ids):
    """
    Atomically acquire holds on the specified seats for *show* by *user*.
    Replaces any previous holds the user had for this show.
    All-or-nothing: if any seat is unavailable, transaction rolls back and raises SeatUnavailable.
    """
    if not show.is_bookable:
        raise ShowNotBookable()

    if not isinstance(seat_ids, (list, tuple)) or not seat_ids:
        raise InvalidSeats("Please select at least one seat.")

    # Unique check
    unique_ids = list(dict.fromkeys(seat_ids))
    max_seats = getattr(settings, "MAX_SEATS_PER_BOOKING", 8)
    if len(unique_ids) > max_seats:
        raise TooManySeats(max_seats=max_seats)

    # Validate seats belong to this screen
    seats = list(Seat.objects.filter(screen=show.screen, id__in=unique_ids))
    if len(seats) != len(unique_ids):
        raise InvalidSeats("One or more selected seats do not exist on this screen.")

    now = timezone.now()
    hold_duration = datetime.timedelta(minutes=getattr(settings, "HOLD_MINUTES", 5))
    expires_at = now + hold_duration

    with transaction.atomic():
        # 1. Lazy cleanup of expired holds on this show
        SeatHold.objects.filter(show=show, expires_at__lte=now).delete()

        # 2. Release any existing holds for this user on this show (changing seats)
        SeatHold.objects.filter(show=show, user=user).delete()

        # 3. Check for already booked seats
        booked_clashes = list(
            BookingSeat.objects.filter(show=show, seat__in=seats).select_related("seat")
        )
        if booked_clashes:
            raise SeatUnavailable(seats=[b.seat.label for b in booked_clashes])

        # 4. Check for active holds by other users
        held_clashes = list(
            SeatHold.objects.filter(show=show, seat__in=seats, expires_at__gt=now).select_related("seat")
        )
        if held_clashes:
            raise SeatUnavailable(seats=[h.seat.label for h in held_clashes])

        # 5. Bulk create holds
        new_holds = [
            SeatHold(
                user=user,
                show=show,
                seat=seat,
                expires_at=expires_at,
            )
            for seat in seats
        ]

        try:
            SeatHold.objects.bulk_create(new_holds)
        except IntegrityError:
            # Race condition: another user held one of the seats simultaneously
            clashes = list(
                SeatHold.objects.filter(show=show, seat__in=seats).select_related("seat")
            )
            raise SeatUnavailable(seats=[h.seat.label for h in clashes] if clashes else None)

    price = float(show.ticket_price)
    total_amount = price * len(seats)

    return {
        "show_id": show.id,
        "seats": [{"seat_id": s.id, "label": s.label} for s in sorted(seats, key=lambda x: (x.row_label, x.seat_number))],
        "ticket_price": f"{price:.2f}",
        "total_amount": f"{total_amount:.2f}",
        "expires_at": expires_at.isoformat(),
        "server_time": now.isoformat(),
    }


def release_holds(show, user):
    """Release all holds owned by *user* for *show*."""
    SeatHold.objects.filter(show=show, user=user).delete()


def get_user_active_holds(show, user):
    """Return active (unexpired) holds for *user* on *show*."""
    now = timezone.now()
    return list(
        SeatHold.objects.filter(show=show, user=user, expires_at__gt=now)
        .select_related("seat")
        .order_by("seat__row_label", "seat__seat_number")
    )


def confirm_booking(user, show, idempotency_key):
    """
    Convert active holds into a confirmed booking with simulated payment and idempotency protection.
    Returns: (booking, created: bool)
    """
    from .models import Booking, BookingSeat
    from .utils import generate_booking_reference
    from . import payments
    from .errors import HoldExpired, SeatUnavailable, ShowNotBookable

    # 1. Idempotency check: repeated submits return the existing booking
    existing = Booking.objects.filter(user=user, idempotency_key=idempotency_key).first()
    if existing:
        return existing, False

    # 2. Re-validate show bookability
    if not show.is_bookable or show.status != Show.STATUS_SCHEDULED:
        raise ShowNotBookable()

    # 3. Load active holds
    now = timezone.now()
    holds = list(
        SeatHold.objects.filter(user=user, show=show, expires_at__gt=now)
        .select_related("seat")
        .order_by("seat__row_label", "seat__seat_number")
    )
    if not holds:
        raise HoldExpired()

    # 4. Compute total price on server
    price = float(show.ticket_price)
    total_amount = price * len(holds)

    # 5. Process simulated payment (may raise PaymentFailed; holds remain intact)
    payments.charge(total_amount)

    # 6. Atomic creation and hold deletion
    with transaction.atomic():
        ref = generate_booking_reference()
        seat_labels = ", ".join(h.seat.label for h in holds)

        booking = Booking.objects.create(
            booking_reference=ref,
            user=user,
            show=show,
            total_amount=f"{total_amount:.2f}",
            booking_status=Booking.STATUS_CONFIRMED,
            payment_status=Booking.PAYMENT_PAID,
            idempotency_key=idempotency_key,
            seat_labels=seat_labels,
        )

        booking_seats = [
            BookingSeat(booking=booking, seat=h.seat, show=show)
            for h in holds
        ]

        try:
            BookingSeat.objects.bulk_create(booking_seats)
        except IntegrityError:
            # Final safeguard against double booking
            raise SeatUnavailable()

        # Delete holds
        SeatHold.objects.filter(user=user, show=show).delete()

    return booking, True


def cancel_booking(booking, user):
    """
    Cancel an existing booking and free its seats, enforcing the 2-hour cutoff rule.
    """
    from .models import Booking, BookingSeat
    from .errors import BookingNotFound, AlreadyCancelled, CancellationNotAllowed

    if booking.user_id != user.id and not getattr(user, "is_admin", False):
        raise BookingNotFound()

    if booking.booking_status == Booking.STATUS_CANCELLED:
        raise AlreadyCancelled()

    cutoff_hours = getattr(settings, "CANCEL_CUTOFF_HOURS", 2)
    cutoff_time = booking.show.start_datetime - datetime.timedelta(hours=cutoff_hours)

    if timezone.now() >= cutoff_time:
        raise CancellationNotAllowed(cutoff_hours=cutoff_hours)

    with transaction.atomic():
        booking.booking_status = Booking.STATUS_CANCELLED
        booking.payment_status = Booking.PAYMENT_REFUNDED
        booking.cancelled_at = timezone.now()
        booking.save()

        # Delete booking_seats so the seats immediately become available for re-booking
        BookingSeat.objects.filter(booking=booking).delete()

    return booking
