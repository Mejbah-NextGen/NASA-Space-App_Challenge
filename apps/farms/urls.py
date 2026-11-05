from django.urls import path

from . import views


app_name = "farms"
urlpatterns = [
    path("farms/", views.FarmListView.as_view(), name="farm_list"),
    path("farms/new/", views.FarmCreateView.as_view(), name="farm_create"),
    path("farms/<int:pk>/", views.FarmDetailView.as_view(), name="farm_detail"),
    path("farms/<int:pk>/edit/", views.FarmUpdateView.as_view(), name="farm_update"),
    path("farms/<int:pk>/archive/", views.FarmArchiveView.as_view(), name="farm_archive"),
    path("farms/<int:farm_pk>/fields/new/", views.FieldCreateView.as_view(), name="field_create"),
    path("fields/<int:pk>/edit/", views.FieldUpdateView.as_view(), name="field_update"),
    path("fields/<int:field_pk>/plantings/new/", views.PlantingCreateView.as_view(), name="planting_create"),
    path("plantings/<int:pk>/edit/", views.PlantingUpdateView.as_view(), name="planting_update"),
    path("farms/<int:farm_pk>/activities/new/", views.FarmActivityCreateView.as_view(), name="activity_create"),
    path("farms/<int:farm_pk>/tasks/new/", views.FarmTaskCreateView.as_view(), name="task_create"),
]

