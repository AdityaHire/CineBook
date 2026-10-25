import secrets
from django.utils import timezone
from .models import Booking

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Excludes ambiguous: 0, O, 1, I


def generate_booking_reference(max_retries=10):
    """
    Generate unique booking reference: CNB-YYYYMMDD-XXXX
    Uses unambiguous alphabet and collision retry backed by database check.
    """
    date_part = timezone.now().strftime("%Y%m%d")

    for _ in range(max_retries):
        random_suffix = "".join(secrets.choice(ALPHABET) for _ in range(4))
        ref = f"CNB-{date_part}-{random_suffix}"
        if not Booking.objects.filter(booking_reference=ref).exists():
            return ref

    raise RuntimeError("Failed to generate unique booking reference after maximum retries.")
