import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from catalog.models import Movie, Theatre, Screen, Show
from catalog.services import compute_end_datetime, check_show_overlap, local_to_utc


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = [
            "title",
            "description",
            "genre",
            "language",
            "duration_minutes",
            "release_date",
            "poster_url",
            "status",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "cb-input", "placeholder": "e.g. Inception"}),
            "description": forms.Textarea(attrs={"class": "cb-input", "rows": 4, "placeholder": "Movie synopsis..."}),
            "genre": forms.TextInput(attrs={"class": "cb-input", "placeholder": "e.g. Action / Sci-Fi"}),
            "language": forms.TextInput(attrs={"class": "cb-input", "placeholder": "e.g. English, Hindi"}),
            "duration_minutes": forms.NumberInput(attrs={"class": "cb-input", "min": 1, "max": 600}),
            "release_date": forms.DateInput(attrs={"class": "cb-input", "type": "date"}),
            "poster_url": forms.URLInput(attrs={"class": "cb-input", "placeholder": "https://example.com/poster.jpg", "id": "id_poster_url"}),
            "status": forms.Select(attrs={"class": "cb-input"}),
        }

    def clean_duration_minutes(self):
        duration = self.cleaned_data.get("duration_minutes")
        if duration is None or duration < 1 or duration > 600:
            raise ValidationError("Duration must be between 1 and 600 minutes.")
        return duration


class TheatreForm(forms.ModelForm):
    class Meta:
        model = Theatre
        fields = ["theatre_name", "location", "time_zone", "is_active"]
        widgets = {
            "theatre_name": forms.TextInput(attrs={"class": "cb-input", "placeholder": "e.g. PVR INOX — Kothrud"}),
            "location": forms.TextInput(attrs={"class": "cb-input", "placeholder": "e.g. Kothrud, Pune"}),
            "time_zone": forms.TextInput(attrs={"class": "cb-input", "placeholder": "e.g. Asia/Kolkata"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_time_zone(self):
        tz_name = self.cleaned_data.get("time_zone", "").strip()
        try:
            ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError(f"'{tz_name}' is not a valid IANA time zone (e.g. Asia/Kolkata).")
        return tz_name


class ScreenForm(forms.ModelForm):
    class Meta:
        model = Screen
        fields = ["screen_name", "rows", "seats_per_row"]
        widgets = {
            "screen_name": forms.TextInput(attrs={"class": "cb-input", "placeholder": "e.g. Audi 1 or IMAX Screen"}),
            "rows": forms.NumberInput(attrs={"class": "cb-input", "min": 1, "max": 26}),
            "seats_per_row": forms.NumberInput(attrs={"class": "cb-input", "min": 1, "max": 30}),
        }

    def __init__(self, *args, **kwargs):
        self.theatre = kwargs.pop("theatre", None)
        self.lock_layout = kwargs.pop("lock_layout", False)
        super().__init__(*args, **kwargs)

        if self.lock_layout:
            self.fields["rows"].widget.attrs["readonly"] = True
            self.fields["rows"].help_text = "Seat layout is locked because bookings exist for this screen."
            self.fields["seats_per_row"].widget.attrs["readonly"] = True
            self.fields["seats_per_row"].help_text = "Seat layout is locked because bookings exist for this screen."

    def clean_rows(self):
        rows = self.cleaned_data.get("rows")
        if self.lock_layout and self.instance.pk:
            return self.instance.rows
        if rows < 1 or rows > 26:
            raise ValidationError("Rows must be between 1 and 26.")
        return rows

    def clean_seats_per_row(self):
        seats = self.cleaned_data.get("seats_per_row")
        if self.lock_layout and self.instance.pk:
            return self.instance.seats_per_row
        if seats < 1 or seats > 30:
            raise ValidationError("Seats per row must be between 1 and 30.")
        return seats

    def clean_screen_name(self):
        name = self.cleaned_data.get("screen_name", "").strip()
        theatre = self.theatre or (self.instance.theatre if self.instance.pk else None)
        if theatre:
            qs = Screen.objects.filter(theatre=theatre, screen_name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f"A screen named '{name}' already exists in this theatre.")
        return name


class ShowCreateForm(forms.Form):
    movie = forms.ModelChoiceField(
        queryset=Movie.objects.filter(status=Movie.STATUS_NOW_SHOWING),
        widget=forms.Select(attrs={"class": "cb-input"}),
    )
    theatre = forms.ModelChoiceField(
        queryset=Theatre.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "cb-input", "id": "id_theatre_select"}),
    )
    screen = forms.ModelChoiceField(
        queryset=Screen.objects.none(),
        widget=forms.Select(attrs={"class": "cb-input", "id": "id_screen_select"}),
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "cb-input", "type": "date"}),
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"class": "cb-input", "type": "time"}),
    )
    ticket_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "cb-input", "step": "0.50", "placeholder": "250.00"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "theatre" in self.data:
            try:
                theatre_id = int(self.data.get("theatre"))
                self.fields["screen"].queryset = Screen.objects.filter(theatre_id=theatre_id)
            except (ValueError, TypeError):
                self.fields["screen"].queryset = Screen.objects.all()
        else:
            self.fields["screen"].queryset = Screen.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        movie = cleaned_data.get("movie")
        screen = cleaned_data.get("screen")
        theatre = cleaned_data.get("theatre")
        d = cleaned_data.get("date")
        t = cleaned_data.get("start_time")

        if not movie or not screen or not d or not t:
            return cleaned_data

        tz_str = screen.theatre.time_zone
        start_utc = local_to_utc(d, t, tz_str)

        if start_utc <= timezone.now():
            raise ValidationError("Show start time must be in the future.")

        end_utc = compute_end_datetime(movie, start_utc)

        if check_show_overlap(screen, start_utc, end_utc):
            raise ValidationError(
                "This show overlaps with an existing scheduled show on this screen (including the 15-minute cleaning buffer)."
            )

        cleaned_data["start_utc"] = start_utc
        cleaned_data["end_utc"] = end_utc
        return cleaned_data


class ShowEditForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={"class": "cb-input", "type": "date"}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"class": "cb-input", "type": "time"}))

    class Meta:
        model = Show
        fields = ["movie", "ticket_price", "status"]
        widgets = {
            "movie": forms.Select(attrs={"class": "cb-input"}),
            "ticket_price": forms.NumberInput(attrs={"class": "cb-input", "step": "0.50"}),
            "status": forms.Select(attrs={"class": "cb-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.lock_schedule = kwargs.pop("lock_schedule", False)
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            local_dt = self.instance.local_start()
            self.fields["date"].initial = local_dt.date()
            self.fields["start_time"].initial = local_dt.time()

        if self.lock_schedule:
            self.fields["date"].widget.attrs["readonly"] = True
            self.fields["start_time"].widget.attrs["readonly"] = True
            self.fields["date"].help_text = "Schedule locked because this show already has bookings."
            self.fields["start_time"].help_text = "Schedule locked because this show already has bookings."

    def clean(self):
        cleaned_data = super().clean()
        if self.lock_schedule:
            cleaned_data["start_utc"] = self.instance.start_datetime
            cleaned_data["end_utc"] = self.instance.end_datetime
            return cleaned_data

        d = cleaned_data.get("date")
        t = cleaned_data.get("start_time")
        movie = cleaned_data.get("movie") or self.instance.movie
        screen = self.instance.screen

        if d and t:
            start_utc = local_to_utc(d, t, screen.theatre.time_zone)
            end_utc = compute_end_datetime(movie, start_utc)

            if cleaned_data.get("status") == Show.STATUS_SCHEDULED:
                if check_show_overlap(screen, start_utc, end_utc, exclude_show_id=self.instance.pk):
                    raise ValidationError(
                        "This updated time overlaps with another scheduled show on this screen (including 15-min cleaning buffer)."
                    )

            cleaned_data["start_utc"] = start_utc
            cleaned_data["end_utc"] = end_utc

        return cleaned_data
