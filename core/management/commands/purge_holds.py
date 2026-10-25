from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import SeatHold


class Command(BaseCommand):
    help = "Purge expired seat holds from the database"

    def handle(self, *args, **options):
        now = timezone.now()
        deleted_count, _ = SeatHold.objects.filter(expires_at__lte=now).delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted_count} expired seat hold(s)."))
