import datetime
from zoneinfo import ZoneInfo
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import Movie, Show, Theatre
from .services import get_availability_label


def home(request):
    """
    Public home page: lists entertainment offerings divided by categories:
    Live Concerts, Comedy & Shows, Streaming, and Movies.
    Supports category filtering, search, and pagination.
    """
    query = request.GET.get("q", "").strip()
    active_category = request.GET.get("category", "all").strip().lower()

    base_qs = Movie.objects.filter(status=Movie.STATUS_NOW_SHOWING)
    if query:
        base_qs = base_qs.filter(title__icontains=query)

    # Category counts
    all_count = base_qs.count()
    movies_count = base_qs.filter(category=Movie.CATEGORY_MOVIES).count()
    concerts_count = base_qs.filter(category=Movie.CATEGORY_CONCERTS).count()
    shows_count = base_qs.filter(category=Movie.CATEGORY_SHOWS).count()
    streaming_count = base_qs.filter(category=Movie.CATEGORY_STREAMING).count()

    categories_meta = [
        {"id": "all", "label": "All", "icon": "bi-grid-fill", "count": all_count},
        {"id": "movies", "label": "Movies", "icon": "bi-film", "count": movies_count},
        {"id": "concerts", "label": "Live Concerts", "icon": "bi-music-note-beamed", "count": concerts_count},
        {"id": "shows", "label": "Comedy & Shows", "icon": "bi-emoji-laughing", "count": shows_count},
        {"id": "streaming", "label": "Streaming", "icon": "bi-play-circle-fill", "count": streaming_count},
    ]

    valid_categories = [Movie.CATEGORY_MOVIES, Movie.CATEGORY_CONCERTS, Movie.CATEGORY_SHOWS, Movie.CATEGORY_STREAMING]
    if active_category in valid_categories:
        filtered_qs = base_qs.filter(category=active_category)
        paginator = Paginator(filtered_qs, 12)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        sections = None
    else:
        active_category = "all"
        paginator = Paginator(base_qs, 24)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Categorized division sections for rich home page experience
        sections = []
        movies_items = list(base_qs.filter(category=Movie.CATEGORY_MOVIES)[:8])
        if movies_items:
            sections.append({
                "id": "movies",
                "title": "Now Showing in Cinemas",
                "subtitle": "Trending cinema releases and critically acclaimed blockbusters",
                "icon": "bi-film",
                "items": movies_items,
                "view_all_url": "/?category=movies",
                "badge": "In Cinemas",
                "badge_class": "cb-badge-accent",
            })

        concerts_items = list(base_qs.filter(category=Movie.CATEGORY_CONCERTS)[:4])
        if concerts_items:
            sections.append({
                "id": "concerts",
                "title": "Live Concerts & Music Festivals",
                "subtitle": "Unforgettable live arena tours, band concerts, and indie festivals",
                "icon": "bi-music-note-beamed",
                "items": concerts_items,
                "view_all_url": "/?category=concerts",
                "badge": "Live Events",
                "badge_class": "cb-badge-warning",
            })

        shows_items = list(base_qs.filter(category=Movie.CATEGORY_SHOWS)[:4])
        if shows_items:
            sections.append({
                "id": "shows",
                "title": "Comedy & Theatrical Plays",
                "subtitle": "Stand-up comedy specials, theatre plays, and live stage acts",
                "icon": "bi-emoji-laughing",
                "items": shows_items,
                "view_all_url": "/?category=shows",
                "badge": "Stage & Comedy",
                "badge_class": "cb-badge-success",
            })

        streaming_items = list(base_qs.filter(category=Movie.CATEGORY_STREAMING)[:4])
        if streaming_items:
            sections.append({
                "id": "streaming",
                "title": "Streaming Premieres & Digital Cinema",
                "subtitle": "Exclusive 4K HDR digital releases to watch anywhere",
                "icon": "bi-play-circle-fill",
                "items": streaming_items,
                "view_all_url": "/?category=streaming",
                "badge": "Online Premiere",
                "badge_class": "cb-badge-accent",
            })

    return render(
        request,
        "catalog/home.html",
        {
            "page_obj": page_obj,
            "query": query,
            "total_count": paginator.count,
            "active_category": active_category,
            "categories_meta": categories_meta,
            "sections": sections,
        },
    )


def movie_details(request, movie_id):
    """
    Movie details page: poster, metadata, synopsis, and show selection UI.
    Shows are grouped by local date and by theatre.
    """
    movie = get_object_or_404(Movie, pk=movie_id)
    if movie.status == Movie.STATUS_ARCHIVED and not getattr(request.user, "is_admin", False):
        raise Http404("This movie is not currently available.")

    # Get upcoming scheduled shows
    now = timezone.now()
    shows_qs = (
        Show.objects.filter(
            movie=movie,
            status=Show.STATUS_SCHEDULED,
            start_datetime__gt=now,
        )
        .select_related("screen__theatre")
        .order_by("start_datetime")
    )

    # Collect distinct local dates
    dates_dict = {}
    for show in shows_qs:
        local_dt = show.local_start()
        d = local_dt.date()
        if d not in dates_dict:
            dates_dict[d] = {
                "date_str": d.strftime("%Y-%m-%d"),
                "date_obj": d,
                "day_label": "Today" if d == local_dt.date() and d == timezone.localdate() else (
                    "Tomorrow" if d == timezone.localdate() + datetime.timedelta(days=1) else d.strftime("%a")
                ),
                "formatted_date": d.strftime("%d %b"),
            }

    sorted_dates = sorted(dates_dict.values(), key=lambda x: x["date_obj"])

    # Determine active selected date
    selected_date_str = request.GET.get("date")
    if not selected_date_str and sorted_dates:
        selected_date_str = sorted_dates[0]["date_str"]

    # Filter shows for selected date and group by theatre
    theatres_data = []
    if selected_date_str:
        theatres_map = {}
        for show in shows_qs:
            local_dt = show.local_start()
            if local_dt.date().strftime("%Y-%m-%d") == selected_date_str:
                theatre = show.screen.theatre
                if theatre.id not in theatres_map:
                    theatres_map[theatre.id] = {
                        "theatre": theatre,
                        "shows": [],
                    }
                theatres_map[theatre.id]["shows"].append({
                    "show": show,
                    "local_time": local_dt.strftime("%I:%M %p"),
                    "screen_name": show.screen.screen_name,
                    "price": f"{show.ticket_price:.2f}",
                    "availability": get_availability_label(show),
                    "is_bookable": show.is_bookable,
                })
        theatres_data = list(theatres_map.values())

    return render(
        request,
        "catalog/movie_details.html",
        {
            "movie": movie,
            "dates": sorted_dates,
            "selected_date": selected_date_str,
            "theatres_data": theatres_data,
            "has_shows": len(sorted_dates) > 0,
        },
    )


def api_movie_shows(request, movie_id):
    """
    JSON API endpoint: GET /api/movies/<id>/shows/
    Optional params: ?date=YYYY-MM-DD and ?theatre_id=N
    """
    movie = get_object_or_404(Movie, pk=movie_id)
    if movie.status == Movie.STATUS_ARCHIVED and not getattr(request.user, "is_admin", False):
        return JsonResponse({"error": {"code": "NOT_FOUND", "message": "Movie not found"}}, status=404)

    now = timezone.now()
    shows_qs = (
        Show.objects.filter(
            movie=movie,
            status=Show.STATUS_SCHEDULED,
            start_datetime__gt=now,
        )
        .select_related("screen__theatre")
        .order_by("start_datetime")
    )

    theatre_id_param = request.GET.get("theatre_id")
    if theatre_id_param:
        shows_qs = shows_qs.filter(screen__theatre_id=theatre_id_param)

    # Collect dates
    date_set = set()
    for s in shows_qs:
        date_set.add(s.local_start().date().strftime("%Y-%m-%d"))
    dates_list = sorted(list(date_set))

    filter_date = request.GET.get("date")
    theatres_map = {}
    for show in shows_qs:
        local_dt = show.local_start()
        show_date_str = local_dt.date().strftime("%Y-%m-%d")
        if filter_date and show_date_str != filter_date:
            continue

        th = show.screen.theatre
        if th.id not in theatres_map:
            theatres_map[th.id] = {
                "theatre_id": th.id,
                "theatre_name": th.theatre_name,
                "location": th.location,
                "shows": [],
            }

        theatres_map[th.id]["shows"].append({
            "show_id": show.id,
            "screen_name": show.screen.screen_name,
            "start_utc": show.start_datetime.isoformat(),
            "start_local": local_dt.strftime("%Y-%m-%d %H:%M"),
            "ticket_price": f"{show.ticket_price:.2f}",
            "availability": get_availability_label(show),
        })

    return JsonResponse({
        "movie_id": movie.id,
        "dates": dates_list,
        "theatres": list(theatres_map.values()),
    })
