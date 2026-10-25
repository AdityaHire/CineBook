import datetime
from django.db import models
from django.utils import timezone


class Movie(models.Model):
    STATUS_NOW_SHOWING = "now_showing"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_NOW_SHOWING, "Now Showing"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    CATEGORY_MOVIES = "movies"
    CATEGORY_CONCERTS = "concerts"
    CATEGORY_SHOWS = "shows"
    CATEGORY_STREAMING = "streaming"
    CATEGORY_CHOICES = [
        (CATEGORY_MOVIES, "Movies"),
        (CATEGORY_CONCERTS, "Live Concerts"),
        (CATEGORY_SHOWS, "Comedy & Plays"),
        (CATEGORY_STREAMING, "Streaming"),
    ]

    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    genre = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_MOVIES,
        db_index=True,
    )
    language = models.CharField(max_length=50)
    duration_minutes = models.PositiveSmallIntegerField()
    release_date = models.DateField()
    poster_url = models.URLField(max_length=500, blank=True, null=True)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES,
        default=STATUS_NOW_SHOWING, db_index=True,
    )

    class Meta:
        db_table = "movies"
        ordering = ["title"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return self.title

    @property
    def duration_display(self):
        h, m = divmod(self.duration_minutes, 60)
        return f"{h}h {m}m" if h else f"{m}m"


class Theatre(models.Model):
    theatre_name = models.CharField(max_length=150)
    location = models.CharField(max_length=255)
    time_zone = models.CharField(max_length=64, default="Asia/Kolkata")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "theatres"
        ordering = ["theatre_name"]

    def __str__(self):
        return self.theatre_name


class Screen(models.Model):
    theatre = models.ForeignKey(Theatre, on_delete=models.PROTECT, related_name="screens")
    screen_name = models.CharField(max_length=50)
    rows = models.PositiveSmallIntegerField(default=8)
    seats_per_row = models.PositiveSmallIntegerField(default=12)

    class Meta:
        db_table = "screens"
        unique_together = [("theatre", "screen_name")]
        ordering = ["screen_name"]

    def __str__(self):
        return f"{self.theatre.theatre_name} — {self.screen_name}"

    @property
    def total_seats(self):
        return self.seats.count()

    @property
    def layout_display(self):
        return f"{self.rows} rows × {self.seats_per_row} seats"


class Seat(models.Model):
    screen = models.ForeignKey(Screen, on_delete=models.PROTECT, related_name="seats")
    row_label = models.CharField(max_length=2)
    seat_number = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "seats"
        unique_together = [("screen", "row_label", "seat_number")]
        ordering = ["row_label", "seat_number"]

    def __str__(self):
        return f"{self.row_label}{self.seat_number}"

    @property
    def label(self):
        return f"{self.row_label}{self.seat_number}"


class Show(models.Model):
    STATUS_SCHEDULED = "scheduled"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    movie = models.ForeignKey(Movie, on_delete=models.PROTECT, related_name="shows")
    screen = models.ForeignKey(Screen, on_delete=models.PROTECT, related_name="shows")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)

    class Meta:
        db_table = "shows"
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["movie", "start_datetime"]),
            models.Index(fields=["screen", "start_datetime"]),
        ]

    def __str__(self):
        return f"{self.movie.title} @ {self.screen} — {self.start_datetime:%Y-%m-%d %H:%M}"

    @property
    def is_bookable(self):
        from django.conf import settings
        cutoff = getattr(settings, "BOOKING_CUTOFF_MINUTES", 15)
        return (
            self.status == self.STATUS_SCHEDULED
            and self.start_datetime > timezone.now() + datetime.timedelta(minutes=cutoff)
        )

    def local_start(self):
        """Return start_datetime converted to the theatre's local timezone."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(self.screen.theatre.time_zone)
        return self.start_datetime.astimezone(tz)

    def clean(self):
        from django.core.exceptions import ValidationError
        from .services import compute_end_datetime, check_show_overlap

        if not self.movie_id or not self.screen_id or not self.start_datetime:
            return

        if not self.end_datetime:
            self.end_datetime = compute_end_datetime(self.movie, self.start_datetime)

        if self.end_datetime <= self.start_datetime:
            raise ValidationError({"end_datetime": "End time must be after start time."})

        if self.status == self.STATUS_SCHEDULED:
            if check_show_overlap(self.screen, self.start_datetime, self.end_datetime, exclude_show_id=self.pk):
                raise ValidationError("This show overlaps with another scheduled show on this screen (including 15-min cleaning buffer).")

    def save(self, *args, **kwargs):
        if not self.end_datetime and self.movie_id and self.start_datetime:
            from .services import compute_end_datetime
            self.end_datetime = compute_end_datetime(self.movie, self.start_datetime)
        super().save(*args, **kwargs)
