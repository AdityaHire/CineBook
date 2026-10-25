from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="admin_dashboard"),
    # Movies
    path("movies/", views.movie_list, name="admin_movie_list"),
    path("movies/new/", views.movie_create, name="admin_movie_create"),
    path("movies/<int:movie_id>/edit/", views.movie_edit, name="admin_movie_edit"),
    path("movies/<int:movie_id>/archive/", views.movie_archive, name="admin_movie_archive"),
    path("movies/<int:movie_id>/restore/", views.movie_restore, name="admin_movie_restore"),
    # Theatres & Screens
    path("theatres/", views.theatre_list, name="admin_theatre_list"),
    path("theatres/new/", views.theatre_create, name="admin_theatre_create"),
    path("theatres/<int:theatre_id>/edit/", views.theatre_edit, name="admin_theatre_edit"),
    path("theatres/<int:theatre_id>/screens/new/", views.screen_create, name="admin_screen_create"),
    path("screens/<int:screen_id>/edit/", views.screen_edit, name="admin_screen_edit"),
    # Shows
    path("shows/", views.show_list, name="admin_show_list"),
    path("shows/new/", views.show_create, name="admin_show_create"),
    path("shows/<int:show_id>/edit/", views.show_edit, name="admin_show_edit"),
    path("shows/<int:show_id>/cancel/", views.show_cancel, name="admin_show_cancel"),
    # Bookings
    path("bookings/", views.booking_list, name="admin_booking_list"),
]
