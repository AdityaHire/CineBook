import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from catalog.models import Show
from .models import Booking
from .services import get_user_active_holds


@login_required
def seat_selection_view(request, show_id):
    """Page route: /shows/<show_id>/seats/"""
    show = get_object_or_404(
        Show.objects.select_related("movie", "screen__theatre"),
        pk=show_id,
    )

    if not show.is_bookable:
        messages.warning(request, "Booking for this show is closed or cancelled.")
        return redirect("movie_details", movie_id=show.movie.id)

    return render(
        request,
        "bookings/seat_selection.html",
        {
            "show": show,
            "movie": show.movie,
            "theatre": show.screen.theatre,
            "screen": show.screen,
            "max_seats": 8,
        },
    )


@login_required
def booking_summary_view(request, show_id):
    """Page route: /shows/<show_id>/summary/"""
    show = get_object_or_404(
        Show.objects.select_related("movie", "screen__theatre"),
        pk=show_id,
    )

    holds = get_user_active_holds(show, request.user)
    if not holds:
        messages.warning(request, "Your seat hold has expired or no seats were held. Please pick your seats.")
        return redirect("seat_selection", show_id=show.id)

    earliest_expiry = min(h.expires_at for h in holds)
    total_amount = show.ticket_price * len(holds)
    seat_labels = ", ".join(h.seat.label for h in holds)

    return render(
        request,
        "bookings/summary.html",
        {
            "show": show,
            "movie": show.movie,
            "theatre": show.screen.theatre,
            "screen": show.screen,
            "holds": holds,
            "seat_labels": seat_labels,
            "total_amount": f"{total_amount:.2f}",
            "ticket_price": f"{show.ticket_price:.2f}",
            "seats_count": len(holds),
            "expires_at": earliest_expiry.isoformat(),
            "server_time": timezone.now().isoformat(),
        },
    )


@login_required
def my_bookings_view(request):
    """Page route: /bookings/ - displays Upcoming and Past booking tabs."""
    tab = request.GET.get("tab", "upcoming").strip().lower()
    if tab not in ["upcoming", "past"]:
        tab = "upcoming"

    now = timezone.now()
    user_bookings = Booking.objects.filter(user=request.user).select_related(
        "show__movie", "show__screen__theatre"
    )

    upcoming_qs = user_bookings.filter(show__start_datetime__gte=now).order_by("show__start_datetime")
    past_qs = user_bookings.filter(show__start_datetime__lt=now).order_by("-show__start_datetime")

    upcoming_count = upcoming_qs.count()
    past_count = past_qs.count()

    active_list = upcoming_qs if tab == "upcoming" else past_qs

    # Augment bookings with cancel eligibility
    bookings_data = []
    cutoff_delta = datetime.timedelta(hours=2)
    for b in active_list:
        can_cancel = (
            b.booking_status == Booking.STATUS_CONFIRMED
            and b.show.start_datetime > (now + cutoff_delta)
            and b.show.status == Show.STATUS_SCHEDULED
        )
        bookings_data.append({
            "booking": b,
            "can_cancel": can_cancel,
            "seat_list": b.seat_labels.split(", "),
            "local_start": b.show.local_start(),
        })

    return render(
        request,
        "bookings/my_bookings.html",
        {
            "tab": tab,
            "bookings_data": bookings_data,
            "upcoming_count": upcoming_count,
            "past_count": past_count,
        },
    )


@login_required
def ticket_details_view(request, reference):
    """Page route: /bookings/<reference>/ - single ticket view."""
    booking = get_object_or_404(
        Booking.objects.select_related("show__movie", "show__screen__theatre", "user"),
        booking_reference=reference,
    )

    if booking.user_id != request.user.id and not getattr(request.user, "is_admin", False):
        raise Http404("Booking not found.")

    now = timezone.now()
    can_cancel = (
        booking.booking_status == Booking.STATUS_CONFIRMED
        and booking.show.start_datetime > (now + datetime.timedelta(hours=2))
        and booking.show.status == Show.STATUS_SCHEDULED
    )

    return render(
        request,
        "bookings/ticket_details.html",
        {
            "booking": booking,
            "movie": booking.show.movie,
            "theatre": booking.show.screen.theatre,
            "screen": booking.show.screen,
            "show": booking.show,
            "can_cancel": can_cancel,
            "local_start": booking.show.local_start(),
            "seat_list": booking.seat_labels.split(", "),
        },
    )


@login_required
def booking_confirmation_view(request, reference):
    """Page route: /bookings/<reference>/confirmation/ - confirmation moment right after booking."""
    booking = get_object_or_404(
        Booking.objects.select_related("show__movie", "show__screen__theatre", "user"),
        booking_reference=reference,
    )

    if booking.user_id != request.user.id and not getattr(request.user, "is_admin", False):
        raise Http404("Booking not found.")

    return render(
        request,
        "bookings/confirmation.html",
        {
            "booking": booking,
            "movie": booking.show.movie,
            "theatre": booking.show.screen.theatre,
            "screen": booking.show.screen,
            "show": booking.show,
            "local_start": booking.show.local_start(),
            "seat_list": booking.seat_labels.split(", "),
        },
    )
