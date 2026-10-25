import datetime
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.permissions import admin_required
from catalog.models import Movie, Theatre, Screen, Show
from catalog.services import generate_seats
from .forms import MovieForm, TheatreForm, ScreenForm, ShowCreateForm, ShowEditForm


from django.db import models, transaction
from django.db.models import Sum, Q
from bookings.models import Booking, BookingSeat, SeatHold


@admin_required
def dashboard(request):
    """Admin dashboard with high-level metrics and recent upcoming shows and bookings."""
    now = timezone.now()
    movies_count = Movie.objects.filter(status=Movie.STATUS_NOW_SHOWING).count()
    theatres_count = Theatre.objects.filter(is_active=True).count()
    screens_count = Screen.objects.count()
    upcoming_shows_count = Show.objects.filter(status=Show.STATUS_SCHEDULED, start_datetime__gt=now).count()

    today_date = timezone.localdate()
    bookings_today = Booking.objects.filter(created_at__date=today_date).count()
    revenue_today = Booking.objects.filter(
        created_at__date=today_date,
        booking_status=Booking.STATUS_CONFIRMED,
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    recent_shows = (
        Show.objects.filter(status=Show.STATUS_SCHEDULED, start_datetime__gt=now)
        .select_related("movie", "screen__theatre")
        .order_by("start_datetime")[:6]
    )

    recent_bookings = (
        Booking.objects.select_related("user", "show__movie", "show__screen__theatre")
        .order_by("-created_at")[:6]
    )

    return render(
        request,
        "manage/dashboard.html",
        {
            "movies_count": movies_count,
            "theatres_count": theatres_count,
            "screens_count": screens_count,
            "upcoming_shows_count": upcoming_shows_count,
            "bookings_today": bookings_today,
            "revenue_today": f"{float(revenue_today):.2f}",
            "recent_shows": recent_shows,
            "recent_bookings": recent_bookings,
            "active_tab": "dashboard",
        },
    )


# ── Movies Management ─────────────────────────────────────────────────────────

@admin_required
def movie_list(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all")

    movies_qs = Movie.objects.all().order_by("-release_date")
    if query:
        movies_qs = movies_qs.filter(title__icontains=query)
    if status_filter in [Movie.STATUS_NOW_SHOWING, Movie.STATUS_ARCHIVED]:
        movies_qs = movies_qs.filter(status=status_filter)

    paginator = Paginator(movies_qs, 15)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "manage/movie_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "active_tab": "movies",
        },
    )


@admin_required
def movie_create(request):
    if request.method == "POST":
        form = MovieForm(request.POST)
        if form.is_valid():
            movie = form.save()
            messages.success(request, f"Movie “{movie.title}” has been created.")
            return redirect("admin_movie_list")
    else:
        form = MovieForm(initial={"status": Movie.STATUS_NOW_SHOWING, "release_date": timezone.localdate()})

    return render(
        request,
        "manage/movie_form.html",
        {
            "form": form,
            "is_create": True,
            "active_tab": "movies",
        },
    )


@admin_required
def movie_edit(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    if request.method == "POST":
        form = MovieForm(request.POST, instance=movie)
        if form.is_valid():
            form.save()
            messages.success(request, f"Movie “{movie.title}” updated successfully.")
            return redirect("admin_movie_list")
    else:
        form = MovieForm(instance=movie)

    return render(
        request,
        "manage/movie_form.html",
        {
            "form": form,
            "movie": movie,
            "is_create": False,
            "active_tab": "movies",
        },
    )


@admin_required
@require_POST
def movie_archive(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    movie.status = Movie.STATUS_ARCHIVED
    movie.save()
    messages.success(request, f"“{movie.title}” has been archived. It is now hidden from visitors.")
    return redirect("admin_movie_list")


@admin_required
@require_POST
def movie_restore(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    movie.status = Movie.STATUS_NOW_SHOWING
    movie.save()
    messages.success(request, f"“{movie.title}” has been restored to Now Showing.")
    return redirect("admin_movie_list")


# ── Theatres & Screens ────────────────────────────────────────────────────────

@admin_required
def theatre_list(request):
    theatres = Theatre.objects.prefetch_related("screens__seats").all()
    return render(
        request,
        "manage/theatre_list.html",
        {
            "theatres": theatres,
            "active_tab": "theatres",
        },
    )


@admin_required
def theatre_create(request):
    if request.method == "POST":
        form = TheatreForm(request.POST)
        if form.is_valid():
            theatre = form.save()
            messages.success(request, f"Theatre “{theatre.theatre_name}” created successfully.")
            return redirect("admin_theatre_list")
    else:
        form = TheatreForm(initial={"time_zone": "Asia/Kolkata", "is_active": True})

    return render(
        request,
        "manage/theatre_form.html",
        {
            "form": form,
            "is_create": True,
            "active_tab": "theatres",
        },
    )


@admin_required
def theatre_edit(request, theatre_id):
    theatre = get_object_or_404(Theatre, pk=theatre_id)
    if request.method == "POST":
        form = TheatreForm(request.POST, instance=theatre)
        if form.is_valid():
            form.save()
            messages.success(request, f"Theatre “{theatre.theatre_name}” updated successfully.")
            return redirect("admin_theatre_list")
    else:
        form = TheatreForm(instance=theatre)

    return render(
        request,
        "manage/theatre_form.html",
        {
            "form": form,
            "theatre": theatre,
            "is_create": False,
            "active_tab": "theatres",
        },
    )


@admin_required
def screen_create(request, theatre_id):
    theatre = get_object_or_404(Theatre, pk=theatre_id)
    if request.method == "POST":
        form = ScreenForm(request.POST, theatre=theatre)
        if form.is_valid():
            screen = form.save(commit=False)
            screen.theatre = theatre
            screen.save()
            # Generate seats automatically (rows x seats_per_row)
            generate_seats(screen)
            messages.success(
                request,
                f"Screen “{screen.screen_name}” created with {screen.total_seats} seats generated!"
            )
            return redirect("admin_theatre_list")
    else:
        form = ScreenForm(theatre=theatre, initial={"rows": 8, "seats_per_row": 12})

    return render(
        request,
        "manage/screen_form.html",
        {
            "form": form,
            "theatre": theatre,
            "is_create": True,
            "active_tab": "theatres",
        },
    )


@admin_required
def screen_edit(request, screen_id):
    screen = get_object_or_404(Screen, pk=screen_id)

    # Check if bookings exist for this screen
    has_bookings = False
    try:
        from bookings.models import BookingSeat
        has_bookings = BookingSeat.objects.filter(show__screen=screen).exists()
    except Exception:
        has_bookings = False

    if request.method == "POST":
        form = ScreenForm(request.POST, instance=screen, lock_layout=has_bookings)
        if form.is_valid():
            form.save()
            if not has_bookings:
                # Regenerate seats if dimensions changed
                screen.seats.all().delete()
                generate_seats(screen)
            messages.success(request, f"Screen “{screen.screen_name}” updated successfully.")
            return redirect("admin_theatre_list")
    else:
        form = ScreenForm(instance=screen, lock_layout=has_bookings)

    return render(
        request,
        "manage/screen_form.html",
        {
            "form": form,
            "screen": screen,
            "theatre": screen.theatre,
            "has_bookings": has_bookings,
            "is_create": False,
            "active_tab": "theatres",
        },
    )


# ── Shows Management ──────────────────────────────────────────────────────────

@admin_required
def show_list(request):
    movie_id = request.GET.get("movie")
    theatre_id = request.GET.get("theatre")
    date_str = request.GET.get("date")

    shows_qs = Show.objects.select_related("movie", "screen__theatre").order_by("-start_datetime")

    if movie_id:
        shows_qs = shows_qs.filter(movie_id=movie_id)
    if theatre_id:
        shows_qs = shows_qs.filter(screen__theatre_id=theatre_id)

    paginator = Paginator(shows_qs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    all_movies = Movie.objects.all().order_by("title")
    all_theatres = Theatre.objects.filter(is_active=True).order_by("theatre_name")

    return render(
        request,
        "manage/show_list.html",
        {
            "page_obj": page_obj,
            "all_movies": all_movies,
            "all_theatres": all_theatres,
            "selected_movie": movie_id,
            "selected_theatre": theatre_id,
            "selected_date": date_str,
            "active_tab": "shows",
        },
    )


@admin_required
def show_create(request):
    if request.method == "POST":
        form = ShowCreateForm(request.POST)
        if form.is_valid():
            show = Show.objects.create(
                movie=form.cleaned_data["movie"],
                screen=form.cleaned_data["screen"],
                start_datetime=form.cleaned_data["start_utc"],
                end_datetime=form.cleaned_data["end_utc"],
                ticket_price=form.cleaned_data["ticket_price"],
                status=Show.STATUS_SCHEDULED,
            )
            messages.success(request, f"Show for “{show.movie.title}” scheduled successfully!")
            return redirect("admin_show_list")
    else:
        form = ShowCreateForm(initial={
            "date": timezone.localdate() + datetime.timedelta(days=1),
            "start_time": "18:00",
            "ticket_price": "250.00",
        })

    return render(
        request,
        "manage/show_form.html",
        {
            "form": form,
            "is_create": True,
            "active_tab": "shows",
        },
    )


@admin_required
def show_edit(request, show_id):
    show = get_object_or_404(Show.objects.select_related("screen__theatre", "movie"), pk=show_id)

    has_bookings = False
    try:
        from bookings.models import BookingSeat
        has_bookings = BookingSeat.objects.filter(show=show).exists()
    except Exception:
        has_bookings = False

    if request.method == "POST":
        form = ShowEditForm(request.POST, instance=show, lock_schedule=has_bookings)
        if form.is_valid():
            updated_show = form.save(commit=False)
            if not has_bookings and "start_utc" in form.cleaned_data:
                updated_show.start_datetime = form.cleaned_data["start_utc"]
                updated_show.end_datetime = form.cleaned_data["end_utc"]
            updated_show.save()
            messages.success(request, f"Show for “{show.movie.title}” updated successfully.")
            return redirect("admin_show_list")
    else:
        form = ShowEditForm(instance=show, lock_schedule=has_bookings)

    return render(
        request,
        "manage/show_form.html",
        {
            "form": form,
            "show": show,
            "has_bookings": has_bookings,
            "is_create": False,
            "active_tab": "shows",
        },
    )


@admin_required
@require_POST
def show_cancel(request, show_id):
    show = get_object_or_404(Show.objects.select_related("screen__theatre", "movie"), pk=show_id)

    with transaction.atomic():
        show.status = Show.STATUS_CANCELLED
        show.save()

        now = timezone.now()
        confirmed_bookings = list(
            Booking.objects.filter(show=show, booking_status=Booking.STATUS_CONFIRMED)
        )
        for b in confirmed_bookings:
            b.booking_status = Booking.STATUS_CANCELLED
            b.payment_status = Booking.PAYMENT_REFUNDED
            b.cancelled_at = now
            b.save()

        BookingSeat.objects.filter(show=show).delete()
        SeatHold.objects.filter(show=show).delete()

    messages.warning(
        request,
        f"Show on {show.screen} for “{show.movie.title}” has been cancelled. {len(confirmed_bookings)} customer booking(s) refunded."
    )
    return redirect("admin_show_list")


# ── Bookings Audit (Admin) ────────────────────────────────────────────────────

@admin_required
def booking_list(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all")
    movie_id = request.GET.get("movie")
    theatre_id = request.GET.get("theatre")

    bookings_qs = Booking.objects.select_related("user", "show__movie", "show__screen__theatre").order_by("-created_at")

    if query:
        bookings_qs = bookings_qs.filter(
            models.Q(booking_reference__icontains=query)
            | models.Q(user__email__icontains=query)
            | models.Q(user__name__icontains=query)
        )
    if status_filter in [Booking.STATUS_CONFIRMED, Booking.STATUS_CANCELLED]:
        bookings_qs = bookings_qs.filter(booking_status=status_filter)
    if movie_id:
        bookings_qs = bookings_qs.filter(show__movie_id=movie_id)
    if theatre_id:
        bookings_qs = bookings_qs.filter(show__screen__theatre_id=theatre_id)

    paginator = Paginator(bookings_qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    all_movies = Movie.objects.all().order_by("title")
    all_theatres = Theatre.objects.filter(is_active=True).order_by("theatre_name")

    return render(
        request,
        "manage/booking_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "all_movies": all_movies,
            "all_theatres": all_theatres,
            "selected_movie": movie_id,
            "selected_theatre": theatre_id,
            "active_tab": "bookings",
        },
    )
