from django.urls import path

from . import views


app_name = "learning"
urlpatterns = [
    path("", views.LearningArticleListView.as_view(), name="list"),
    path("create/", views.LearningArticleCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.LearningArticleUpdateView.as_view(), name="update"),
    path("<int:pk>/submit/", views.SubmitArticleView.as_view(), name="submit"),
    path("article/<slug:slug>/", views.LearningArticleDetailView.as_view(), name="detail"),
]
