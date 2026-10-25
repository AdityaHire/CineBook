from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("", include("bookings.urls")),
    path("manage/", include("adminpanel.urls")),
]

# Custom error handlers
handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
