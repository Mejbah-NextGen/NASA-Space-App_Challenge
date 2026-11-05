from django.urls import path

from . import views


app_name = "agricultural_data"
urlpatterns = [
    path("history/", views.PublicHistoryView.as_view(), name="public_history"),
    path("farmer/history/", views.FarmerHistoryView.as_view(), name="farmer_history"),
    path("crop-insights/", views.CropInsightsView.as_view(), name="crop_insights"),
    path("data-sources/", views.DataSourcesView.as_view(), name="data_sources"),
]
