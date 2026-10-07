from django.urls import path

from . import views

app_name = "tungamap"

urlpatterns = [
    path("", views.map_page, name="map"),
    path("api/places/", views.places, name="places"),
    path("api/places/<int:pk>/", views.place_detail, name="place_detail"),
]