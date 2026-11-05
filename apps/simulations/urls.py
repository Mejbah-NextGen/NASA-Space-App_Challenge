from django.urls import path

from . import views


app_name = "simulations"
urlpatterns = [
    path("", views.SimulatorView.as_view(), name="simulator"),
    path("history/", views.SimulationHistoryView.as_view(), name="history"),
    path("compare/", views.SimulationCompareView.as_view(), name="compare"),
    path("<int:pk>/", views.SimulationDetailView.as_view(), name="detail"),
]

