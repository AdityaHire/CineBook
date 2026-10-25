import datetime
from zoneinfo import ZoneInfo
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from catalog.models import Movie, Theatre, Screen, Show
from catalog.services import generate_seats, compute_end_datetime, local_to_utc


class Command(BaseCommand):
    help = "Seed database with demo movies, theatres, screens, seats, shows, and sample users"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        # 1. Users
        admin, created = User.objects.get_or_create(
            email="admin@cenebook.com",
            defaults={
                "name": "Cenebook Admin",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("AdminPass123!")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin user: admin@cenebook.com"))
        else:
            admin.role = "admin"
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password("AdminPass123!")
            admin.save()

        user1, created = User.objects.get_or_create(
            email="user1@cenebook.com",
            defaults={"name": "Asha Sharma", "role": "user"},
        )
        if created:
            user1.set_password("UserPass123!")
            user1.save()

        user2, created = User.objects.get_or_create(
            email="user2@cenebook.com",
            defaults={"name": "Rohan Verma", "role": "user"},
        )
        if created:
            user2.set_password("UserPass123!")
            user2.save()

        self.stdout.write("Users ready.")

        # 2. Movies
        movies_data = [
            {
                "title": "Inception",
                "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O., but his tragic past may doom the project and his team to disaster.",
                "genre": "Sci-Fi / Action",
                "language": "English",
                "duration_minutes": 148,
                "release_date": datetime.date(2026, 10, 1),
                "poster_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_NOW_SHOWING,
            },
            {
                "title": "Kalki 2898 AD",
                "description": "A modern-day avatar of Vishnu, a Hindu god, who is believed to have descended to earth in the dystopian city of Kasi to protect the world from evil forces.",
                "genre": "Action / Mythological Sci-Fi",
                "language": "Hindi",
                "duration_minutes": 180,
                "release_date": datetime.date(2026, 9, 25),
                "poster_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_NOW_SHOWING,
            },
            {
                "title": "Dune: Part Two",
                "description": "Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family. Facing a choice between the love of his life and the fate of the known universe.",
                "genre": "Sci-Fi / Adventure",
                "language": "English",
                "duration_minutes": 166,
                "release_date": datetime.date(2026, 10, 5),
                "poster_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_NOW_SHOWING,
            },
            {
                "title": "Stree 2",
                "description": "After the events of Stree, the town of Chanderi is being haunted again. This time, women are mysteriously abducted by a headless entity named Sarkata. Vicky and his friends band together to save the town.",
                "genre": "Comedy / Horror",
                "language": "Hindi",
                "duration_minutes": 147,
                "release_date": datetime.date(2026, 9, 15),
                "poster_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_NOW_SHOWING,
            },
            {
                "title": "Interstellar",
                "description": "When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot, Joseph Cooper, is tasked to pilot a spacecraft, along with a team of researchers, to find a new planet for humans.",
                "genre": "Sci-Fi / Drama",
                "language": "English",
                "duration_minutes": 169,
                "release_date": datetime.date(2026, 8, 20),
                "poster_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_NOW_SHOWING,
            },
            {
                "title": "Manjummel Boys",
                "description": "A group of friends from a small town in Kochi embark on a trip to Kodaikanal, where one of them accidentally falls into the perilous Guna Caves, triggering an extraordinary rescue effort.",
                "genre": "Survival / Thriller",
                "language": "Malayalam",
                "duration_minutes": 135,
                "release_date": datetime.date(2026, 9, 10),
                "poster_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_NOW_SHOWING,
            },
            {
                "title": "Oppenheimer",
                "description": "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.",
                "genre": "Biography / Drama",
                "language": "English",
                "duration_minutes": 180,
                "release_date": datetime.date(2023, 7, 21),
                "poster_url": "https://images.unsplash.com/photo-1440404653325-ab127d49abc1?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_ARCHIVED,
            },
            {
                "title": "Jawan",
                "description": "A high-octane action thriller outlining the emotional journey of a man who is set to rectify the wrongs in the society while honouring a promise made years ago.",
                "genre": "Action / Thriller",
                "language": "Hindi",
                "duration_minutes": 169,
                "release_date": datetime.date(2023, 9, 7),
                "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80",
                "status": Movie.STATUS_ARCHIVED,
            },
        ]

        created_movies = []
        for m in movies_data:
            obj, _ = Movie.objects.update_or_create(
                title=m["title"],
                defaults=m,
            )
            created_movies.append(obj)

        self.stdout.write(f"Loaded {len(created_movies)} movies.")

        # 3. Theatres and Screens
        theatres_data = [
            {
                "name": "PVR INOX — Kothrud",
                "location": "Kothrud, Pune",
                "time_zone": "Asia/Kolkata",
                "screens": [
                    {"name": "Audi 1", "rows": 8, "seats_per_row": 12},
                    {"name": "Audi 2 (IMAX)", "rows": 8, "seats_per_row": 10},
                ],
            },
            {
                "name": "Cinepolis — Seasons Mall",
                "location": "Magarpatta, Pune",
                "time_zone": "Asia/Kolkata",
                "screens": [
                    {"name": "Screen 1", "rows": 8, "seats_per_row": 12},
                    {"name": "VIP Lounge", "rows": 6, "seats_per_row": 8},
                ],
            },
        ]

        all_screens = []
        for t_info in theatres_data:
            theatre, _ = Theatre.objects.get_or_create(
                theatre_name=t_info["name"],
                defaults={
                    "location": t_info["location"],
                    "time_zone": t_info["time_zone"],
                    "is_active": True,
                },
            )
            for s_info in t_info["screens"]:
                screen, s_created = Screen.objects.get_or_create(
                    theatre=theatre,
                    screen_name=s_info["name"],
                    defaults={
                        "rows": s_info["rows"],
                        "seats_per_row": s_info["seats_per_row"],
                    },
                )
                if screen.seats.count() == 0:
                    generate_seats(screen)
                all_screens.append(screen)

        self.stdout.write("Theatres and screens with seats ready.")

        # 4. Shows for next 7 days
        # Clear existing bookings, holds, and scheduled shows to avoid overlaps on reseeding
        from bookings.models import Booking, BookingSeat, SeatHold
        BookingSeat.objects.all().delete()
        Booking.objects.all().delete()
        SeatHold.objects.all().delete()
        Show.objects.filter(status=Show.STATUS_SCHEDULED).delete()

        now_showing_movies = [m for m in created_movies if m.status == Movie.STATUS_NOW_SHOWING]
        tz = ZoneInfo("Asia/Kolkata")
        today = timezone.localdate(timezone.now(), tz)

        # 3 show slots per day per screen
        slots = [
            (datetime.time(10, 0), "220.00"),
            (datetime.time(14, 30), "280.00"),
            (datetime.time(19, 0), "350.00"),
        ]

        show_count = 0
        movie_idx = 0
        for day_offset in range(7):
            current_date = today + datetime.timedelta(days=day_offset)
            for screen in all_screens:
                for slot_time, price in slots:
                    movie = now_showing_movies[movie_idx % len(now_showing_movies)]
                    movie_idx += 1

                    start_utc = local_to_utc(current_date, slot_time, screen.theatre.time_zone)
                    end_utc = compute_end_datetime(movie, start_utc)

                    Show.objects.create(
                        movie=movie,
                        screen=screen,
                        start_datetime=start_utc,
                        end_datetime=end_utc,
                        ticket_price=price,
                        status=Show.STATUS_SCHEDULED,
                    )
                    show_count += 1
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded shows: {show_count} shows created across 7 days."))

        # 5. Sample Bookings (for testing My Bookings and Admin bookings list)
        from bookings.models import Booking, BookingSeat
        from bookings.utils import generate_booking_reference

        # Clean existing demo bookings
        Booking.objects.all().delete()

        first_show = Show.objects.filter(status=Show.STATUS_SCHEDULED).first()
        if first_show:
            seats_sample = list(first_show.screen.seats.all()[:2])
            b1 = Booking.objects.create(
                booking_reference=generate_booking_reference(),
                user=user1,
                show=first_show,
                total_amount=f"{float(first_show.ticket_price) * len(seats_sample):.2f}",
                booking_status=Booking.STATUS_CONFIRMED,
                payment_status=Booking.PAYMENT_PAID,
                idempotency_key="demo-seed-key-1",
                seat_labels=", ".join(s.label for s in seats_sample),
            )
            for s in seats_sample:
                BookingSeat.objects.create(booking=b1, seat=s, show=first_show)

            b2 = Booking.objects.create(
                booking_reference=generate_booking_reference(),
                user=user2,
                show=first_show,
                total_amount=f"{float(first_show.ticket_price):.2f}",
                booking_status=Booking.STATUS_CANCELLED,
                payment_status=Booking.PAYMENT_REFUNDED,
                cancelled_at=timezone.now(),
                idempotency_key="demo-seed-key-2",
                seat_labels="C1",
            )
            self.stdout.write("Created sample confirmed & cancelled bookings for demo users.")

        self.stdout.write(self.style.SUCCESS("Demo database seeding complete!"))
