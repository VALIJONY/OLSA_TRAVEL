from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("destinations/", views.DestinationListView.as_view(), name="destination_list"),
    path("destinations/<slug:slug>/", views.DestinationDetailView.as_view(), name="destination_detail"),
    path("booking/", views.BookingCreateView.as_view(), name="booking"),
    path("booking/<str:reference>/", views.BookingDoneView.as_view(), name="booking_done"),
    path("about/", views.AboutView.as_view(), name="about"),
]
