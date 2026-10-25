import datetime
from django.test import TestCase, Client
from django.utils import timezone
from accounts.models import User
from catalog.models import Movie, Theatre, Screen, Seat, Show
from catalog.services import generate_seats, compute_end_datetime, check_show_overlap, get_availability_label


class CatalogModelAndServiceTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title="Dune: Part Two",
            description="Epic sci-fi adventure",
            genre="Sci-Fi",
            language="English",
            duration_minutes=166,
            release_date=datetime.date(2026, 10, 1),
            status=Movie.STATUS_NOW_SHOWING,
        )
        self.theatre = Theatre.objects.create(
            theatre_name="PVR Pune",
            location="Kothrud",
            time_zone="Asia/Kolkata",
            is_active=True,
        )
        self.screen = Screen.objects.create(
            theatre=self.theatre,
            screen_name="Audi 1",
            rows=3,
            seats_per_row=4,
        )

    def test_movie_duration_display(self):
        self.assertEqual(self.movie.duration_display, "2h 46m")

    def test_generate_seats(self):
        generate_seats(self.screen)
        self.assertEqual(self.screen.seats.count(), 12)
        # Check first and last seat label
        self.assertTrue(self.screen.seats.filter(row_label="A", seat_number=1).exists())
        self.assertTrue(self.screen.seats.filter(row_label="C", seat_number=4).exists())

    def test_compute_end_datetime(self):
        start = timezone.now()
        # duration 166 min + 15 min buffer = 181 min
        end = compute_end_datetime(self.movie, start)
        delta = (end - start).total_seconds() / 60
        self.assertEqual(delta, 181)

    def test_show_overlap_check(self):
        start = timezone.now() + datetime.timedelta(days=1)
        end = compute_end_datetime(self.movie, start)

        show = Show.objects.create(
            movie=self.movie,
            screen=self.screen,
            start_datetime=start,
            end_datetime=end,
            ticket_price="250.00",
            status=Show.STATUS_SCHEDULED,
        )

        # Exact overlap
        self.assertTrue(check_show_overlap(self.screen, start, end))

        # Partial overlap inside the range
        self.assertTrue(check_show_overlap(self.screen, start + datetime.timedelta(minutes=30), end + datetime.timedelta(minutes=30)))

        # Non-overlapping before
        self.assertFalse(check_show_overlap(self.screen, start - datetime.timedelta(hours=4), start - datetime.timedelta(minutes=1)))

        # Exclude current show id
        self.assertFalse(check_show_overlap(self.screen, start, end, exclude_show_id=show.id))


class CatalogViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.movie_active = Movie.objects.create(
            title="Inception",
            description="Dream inside dream",
            genre="Sci-Fi",
            language="English",
            duration_minutes=148,
            release_date=datetime.date(2026, 10, 1),
            status=Movie.STATUS_NOW_SHOWING,
        )
        self.movie_archived = Movie.objects.create(
            title="Old Classic",
            description="Classic movie",
            genre="Drama",
            language="English",
            duration_minutes=120,
            release_date=datetime.date(2020, 1, 1),
            status=Movie.STATUS_ARCHIVED,
        )
        self.theatre = Theatre.objects.create(
            theatre_name="PVR Kothrud",
            location="Pune",
            time_zone="Asia/Kolkata",
            is_active=True,
        )
        self.screen = Screen.objects.create(
            theatre=self.theatre,
            screen_name="Audi 1",
            rows=2,
            seats_per_row=2,
        )
        generate_seats(self.screen)

        # Future show for active movie
        self.show = Show.objects.create(
            movie=self.movie_active,
            screen=self.screen,
            start_datetime=timezone.now() + datetime.timedelta(days=1),
            end_datetime=timezone.now() + datetime.timedelta(days=1, hours=3),
            ticket_price="200.00",
            status=Show.STATUS_SCHEDULED,
        )

    def test_home_page_displays_now_showing(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inception")
        self.assertNotContains(response, "Old Classic")

    def test_home_page_search(self):
        response = self.client.get("/?q=incept")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inception")

        response_empty = self.client.get("/?q=nonexistentmovie")
        self.assertEqual(response_empty.status_code, 200)
        self.assertContains(response_empty, "No movies found for")

    def test_movie_details_active_movie(self):
        response = self.client.get(f"/movies/{self.movie_active.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inception")
        self.assertContains(response, "PVR Kothrud")

    def test_movie_details_archived_movie_returns_404(self):
        response = self.client.get(f"/movies/{self.movie_archived.id}/")
        self.assertEqual(response.status_code, 404)

    def test_api_movie_shows(self):
        response = self.client.get(f"/api/movies/{self.movie_active.id}/shows/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["movie_id"], self.movie_active.id)
        self.assertTrue(len(data["dates"]) > 0)
        self.assertTrue(len(data["theatres"]) > 0)
        self.assertEqual(data["theatres"][0]["theatre_name"], "PVR Kothrud")
