from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = "dashboard"
urlpatterns = [
    path("farmer/dashboard/", views.FarmerDashboardView.as_view(), name="farmer_dashboard"),
    path("farmer/learning/", RedirectView.as_view(pattern_name="learning:list", permanent=False), name="farmer_learning"),
    path("farmer/support/", RedirectView.as_view(pattern_name="core:help", permanent=False), name="farmer_support"),
    path("farmer/data-sources/", RedirectView.as_view(pattern_name="agricultural_data:data_sources", permanent=False), name="farmer_data_sources"),
    path("agriculturalist/dashboard/", views.AgriculturalistDashboardView.as_view(), name="agriculturalist_dashboard"),
]
