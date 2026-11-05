from django.urls import path

from . import views


app_name = "weather"
urlpatterns = [
    path("weather/", views.PublicWeatherView.as_view(), name="public_weather"),
    path("farmer/weather/", views.FarmerWeatherView.as_view(), name="farmer_weather"),
]
