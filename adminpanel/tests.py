import datetime
from django.test import TestCase, Client
from django.utils import timezone
from accounts.models import User
from catalog.models import Movie, Theatre, Screen, Show
from catalog.services import generate_seats


class AdminPanelTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Regular user
        self.user = User.objects.create_user(
            email="regular@cenebook.com",
            name="Regular User",
            password="UserPass123!",
            role="user",
        )

        # Admin user
        self.admin = User.objects.create_user(
            email="admin@cenebook.com",
            name="Admin User",
            password="AdminPass123!",
            role="admin",
        )

        # Initial movie & theatre
        self.movie = Movie.objects.create(
            title="Kalki 2898 AD",
            description="Epic mythology sci-fi",
            genre="Action",
            language="Hindi",
            duration_minutes=180,
            release_date=datetime.date(2026, 9, 1),
            status=Movie.STATUS_NOW_SHOWING,
        )
        self.theatre = Theatre.objects.create(
            theatre_name="Cinepolis Seasons",
            location="Magarpatta, Pune",
            time_zone="Asia/Kolkata",
            is_active=True,
        )
        self.screen = Screen.objects.create(
            theatre=self.theatre,
            screen_name="Screen 1",
            rows=8,
            seats_per_row=10,
        )
        generate_seats(self.screen)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get("/manage/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/?next=/manage/"))

    def test_non_admin_gets_403(self):
        self.client.force_login(self.user)
        response = self.client.get("/manage/")
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_access(self):
        self.client.force_login(self.admin)
        response = self.client.get("/manage/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Bookings Today")
        self.assertContains(response, "Upcoming Shows")
        self.assertEqual(response.context["theatres_count"], 1)

    def test_admin_theatre_list(self):
        self.client.force_login(self.admin)
        response = self.client.get("/manage/theatres/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cinepolis Seasons")
        self.assertContains(response, "Screen 1")

    def test_admin_movie_archive_and_restore(self):
        self.client.force_login(self.admin)

        # Archive
        archive_res = self.client.post(f"/manage/movies/{self.movie.id}/archive/")
        self.assertEqual(archive_res.status_code, 302)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.status, Movie.STATUS_ARCHIVED)

        # Restore
        restore_res = self.client.post(f"/manage/movies/{self.movie.id}/restore/")
        self.assertEqual(restore_res.status_code, 302)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.status, Movie.STATUS_NOW_SHOWING)

    def test_admin_screen_creation_generates_seats(self):
        self.client.force_login(self.admin)
        post_data = {
            "screen_name": "Screen 2",
            "rows": 4,
            "seats_per_row": 5,
        }
        res = self.client.post(f"/manage/theatres/{self.theatre.id}/screens/new/", data=post_data)
        self.assertEqual(res.status_code, 302)
        new_screen = Screen.objects.get(theatre=self.theatre, screen_name="Screen 2")
        self.assertEqual(new_screen.seats.count(), 20)

    def test_admin_schedule_show_and_overlap_rejection(self):
        self.client.force_login(self.admin)

        # Schedule first show tomorrow at 14:00
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        show_data = {
            "movie": self.movie.id,
            "theatre": self.theatre.id,
            "screen": self.screen.id,
            "date": tomorrow.strftime("%Y-%m-%d"),
            "start_time": "14:00",
            "ticket_price": "250.00",
        }
        res = self.client.post("/manage/shows/new/", data=show_data)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Show.objects.filter(screen=self.screen).count(), 1)

        # Attempt to schedule an overlapping show tomorrow at 15:00 (movie is 180 min + 15 min buffer)
        overlapping_data = {
            "movie": self.movie.id,
            "theatre": self.theatre.id,
            "screen": self.screen.id,
            "date": tomorrow.strftime("%Y-%m-%d"),
            "start_time": "15:00",
            "ticket_price": "300.00",
        }
        res_overlap = self.client.post("/manage/shows/new/", data=overlapping_data)
        self.assertEqual(res_overlap.status_code, 200)  # Re-rendered form with error
        self.assertContains(res_overlap, "overlaps with an existing scheduled show")
        self.assertEqual(Show.objects.filter(screen=self.screen).count(), 1)

    def test_admin_cancel_show(self):
        self.client.force_login(self.admin)
        start = timezone.now() + datetime.timedelta(days=2)
        show = Show.objects.create(
            movie=self.movie,
            screen=self.screen,
            start_datetime=start,
            end_datetime=start + datetime.timedelta(hours=3),
            ticket_price="220.00",
            status=Show.STATUS_SCHEDULED,
        )
        res = self.client.post(f"/manage/shows/{show.id}/cancel/")
        self.assertEqual(res.status_code, 302)
        show.refresh_from_db()
        self.assertEqual(show.status, Show.STATUS_CANCELLED)
