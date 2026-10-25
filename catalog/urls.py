from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("movies/<int:movie_id>/", views.movie_details, name="movie_details"),
    path("api/movies/<int:movie_id>/shows/", views.api_movie_shows, name="api_movie_shows"),
]
