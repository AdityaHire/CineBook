from django.urls import path
from . import views, api

urlpatterns = [
    # Pages
    path("shows/<int:show_id>/seats/", views.seat_selection_view, name="seat_selection"),
    path("shows/<int:show_id>/summary/", views.booking_summary_view, name="booking_summary"),
    path("bookings/", views.my_bookings_view, name="my_bookings"),
    path("bookings/<str:reference>/", views.ticket_details_view, name="ticket_details"),
    path("bookings/<str:reference>/confirmation/", views.booking_confirmation_view, name="booking_confirmation"),

    # JSON APIs
    path("api/shows/<int:show_id>/seats/", api.api_show_seats, name="api_show_seats"),
    path("api/shows/<int:show_id>/holds/", api.api_show_holds, name="api_show_holds"),
    path("api/shows/<int:show_id>/bookings/", api.api_confirm_booking, name="api_confirm_booking"),
    path("api/bookings/<str:reference>/cancel/", api.api_cancel_booking, name="api_cancel_booking"),
    path("api/bookings/<str:reference>/", api.api_get_booking, name="api_get_booking"),
]
