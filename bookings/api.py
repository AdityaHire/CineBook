import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from catalog.models import Show
from .models import Booking
from .errors import CenebookError, ShowNotFound, ShowNotBookable, InvalidRequest
from .services import get_seat_map_data, hold_seats, release_holds, confirm_booking, cancel_booking


def require_json_auth(view_func):
    """Decorator ensuring user is authenticated; returns 401 JSON if not."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": {"code": "AUTH_REQUIRED", "message": "Please log in to continue."}},
                status=401,
            )
        return view_func(request, *args, **kwargs)
    return wrapper


@require_json_auth
@require_http_methods(["GET"])
def api_show_seats(request, show_id):
    """GET /api/shows/<show_id>/seats/ - return live seat map."""
    try:
        show = Show.objects.select_related("movie", "screen__theatre").get(pk=show_id)
    except Show.DoesNotExist:
        return JsonResponse({"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}}, status=404)

    if not show.is_bookable:
        return JsonResponse(
            {"error": {"code": "SHOW_NOT_BOOKABLE", "message": "Booking for this show is closed."}},
            status=409,
        )

    data = get_seat_map_data(show, request.user)
    return JsonResponse(data)


@require_json_auth
@require_http_methods(["POST", "DELETE"])
def api_show_holds(request, show_id):
    """
    POST /api/shows/<show_id>/holds/ - place atomic hold on selected seats.
    DELETE /api/shows/<show_id>/holds/ - release all active holds for this user on this show.
    """
    try:
        show = Show.objects.select_related("movie", "screen__theatre").get(pk=show_id)
    except Show.DoesNotExist:
        return JsonResponse({"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}}, status=404)

    if request.method == "DELETE":
        release_holds(show, request.user)
        return HttpResponse(status=204)

    # POST - hold seats
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except ValueError:
        return JsonResponse({"error": {"code": "INVALID_JSON", "message": "Malformed JSON body."}}, status=400)

    seat_ids = payload.get("seat_ids")

    try:
        res = hold_seats(show, request.user, seat_ids)
        return JsonResponse(res, status=201)
    except CenebookError as err:
        return JsonResponse(err.as_dict(), status=err.status)


@require_json_auth
@require_http_methods(["POST"])
def api_confirm_booking(request, show_id):
    """
    POST /api/shows/<show_id>/bookings/
    Converts active holds into a confirmed booking.
    """
    try:
        show = Show.objects.select_related("movie", "screen__theatre").get(pk=show_id)
    except Show.DoesNotExist:
        return JsonResponse({"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}}, status=404)

    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except ValueError:
        return JsonResponse({"error": {"code": "INVALID_JSON", "message": "Malformed JSON body."}}, status=400)

    idempotency_key = (payload.get("idempotency_key") or "").strip()
    if not idempotency_key or len(idempotency_key) < 8 or len(idempotency_key) > 64:
        return JsonResponse(
            {"error": {"code": "INVALID_REQUEST", "message": "Valid idempotency_key (8-64 chars) is required."}},
            status=400,
        )

    try:
        booking, created = confirm_booking(request.user, show, idempotency_key)
        status_code = 201 if created else 200

        local_dt = show.local_start()
        res_data = {
            "booking_reference": booking.booking_reference,
            "booking_status": booking.booking_status,
            "payment_status": booking.payment_status,
            "show_id": show.id,
            "movie_title": show.movie.title,
            "theatre_name": show.screen.theatre.theatre_name,
            "screen_name": show.screen.screen_name,
            "start_utc": show.start_datetime.isoformat(),
            "start_local": local_dt.strftime("%Y-%m-%d %H:%M"),
            "seats": booking.seat_labels.split(", "),
            "total_amount": f"{float(booking.total_amount):.2f}",
            "created_at": booking.created_at.isoformat(),
            "confirmation_url": f"/bookings/{booking.booking_reference}/confirmation/",
        }
        return JsonResponse(res_data, status=status_code)

    except CenebookError as err:
        return JsonResponse(err.as_dict(), status=err.status)


@require_json_auth
@require_http_methods(["POST"])
def api_cancel_booking(request, reference):
    """
    POST /api/bookings/<reference>/cancel/
    Cancels booking and refunds (simulated), freeing seats if >= 2 hours before show.
    """
    booking = Booking.objects.select_related("show__movie", "show__screen__theatre", "user").filter(
        booking_reference=reference
    ).first()

    if not booking or (booking.user_id != request.user.id and not getattr(request.user, "is_admin", False)):
        return JsonResponse(
            {"error": {"code": "BOOKING_NOT_FOUND", "message": "Booking not found."}},
            status=404,
        )

    try:
        cancelled_booking = cancel_booking(booking, request.user)
        return JsonResponse({
            "booking_reference": cancelled_booking.booking_reference,
            "booking_status": cancelled_booking.booking_status,
            "payment_status": cancelled_booking.payment_status,
            "refund_amount": f"{float(cancelled_booking.total_amount):.2f}",
            "cancelled_at": cancelled_booking.cancelled_at.isoformat(),
        }, status=200)

    except CenebookError as err:
        return JsonResponse(err.as_dict(), status=err.status)


@require_json_auth
@require_http_methods(["GET"])
def api_get_booking(request, reference):
    """GET /api/bookings/<reference>/ - get booking details (owner only)."""
    booking = Booking.objects.select_related("show__movie", "show__screen__theatre", "user").filter(
        booking_reference=reference
    ).first()

    if not booking or (booking.user_id != request.user.id and not getattr(request.user, "is_admin", False)):
        return JsonResponse(
            {"error": {"code": "BOOKING_NOT_FOUND", "message": "Booking not found."}},
            status=404,
        )

    show = booking.show
    local_dt = show.local_start()
    return JsonResponse({
        "booking_reference": booking.booking_reference,
        "booking_status": booking.booking_status,
        "payment_status": booking.payment_status,
        "show_id": show.id,
        "movie_title": show.movie.title,
        "theatre_name": show.screen.theatre.theatre_name,
        "screen_name": show.screen.screen_name,
        "start_utc": show.start_datetime.isoformat(),
        "start_local": local_dt.strftime("%Y-%m-%d %H:%M"),
        "seats": booking.seat_labels.split(", "),
        "total_amount": f"{float(booking.total_amount):.2f}",
        "created_at": booking.created_at.isoformat(),
        "cancelled_at": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
    })
