from django.conf import settings
from django.db import models


class SeatHold(models.Model):
    """Temporary reservation on a seat for 5 minutes during checkout."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seat_holds")
    show = models.ForeignKey("catalog.Show", on_delete=models.CASCADE, related_name="seat_holds")
    seat = models.ForeignKey("catalog.Seat", on_delete=models.CASCADE, related_name="seat_holds")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "seat_holds"
        constraints = [
            models.UniqueConstraint(fields=["show", "seat"], name="uniq_hold_show_seat")
        ]
        indexes = [
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"Hold: {self.user.name} -> {self.show.movie.title} @ {self.seat.label} (exp {self.expires_at:%H:%M:%S})"


class Booking(models.Model):
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PAYMENT_PAID = "paid"
    PAYMENT_FAILED = "failed"
    PAYMENT_REFUNDED = "refunded"
    PAYMENT_CHOICES = [
        (PAYMENT_PAID, "Paid"),
        (PAYMENT_FAILED, "Failed"),
        (PAYMENT_REFUNDED, "Refunded"),
    ]

    booking_reference = models.CharField(max_length=20, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    show = models.ForeignKey("catalog.Show", on_delete=models.PROTECT, related_name="bookings")
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    booking_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_PAID)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=64)
    seat_labels = models.CharField(max_length=255)  # Snapshot of seats e.g. "B3,B4"

    class Meta:
        db_table = "bookings"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "idempotency_key"], name="uniq_user_booking_idempotency")
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.booking_reference} ({self.user.name}) — {self.show.movie.title} [{self.seat_labels}]"


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="booking_seats")
    seat = models.ForeignKey("catalog.Seat", on_delete=models.PROTECT, related_name="booking_seats")
    show = models.ForeignKey("catalog.Show", on_delete=models.PROTECT, related_name="booking_seats")

    class Meta:
        db_table = "booking_seats"
        constraints = [
            models.UniqueConstraint(fields=["show", "seat"], name="uniq_booking_show_seat")
        ]

    def __str__(self):
        return f"{self.booking.booking_reference} — {self.seat.label}"
