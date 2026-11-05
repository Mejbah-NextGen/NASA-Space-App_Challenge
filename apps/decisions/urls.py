from django.urls import path

from . import views


app_name = "decisions"
urlpatterns = [
    path("", views.DecisionListView.as_view(), name="list"),
    path("new/", views.DecisionCreateView.as_view(), name="create"),
    path("<int:pk>/", views.DecisionDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.DecisionUpdateView.as_view(), name="update"),
    path("<int:decision_pk>/outcome/", views.DecisionOutcomeUpdateView.as_view(), name="outcome"),
]

