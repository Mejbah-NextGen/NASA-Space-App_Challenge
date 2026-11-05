from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = "agriculturalist"
urlpatterns = [
    path("farmers/", views.AssignedFarmerListView.as_view(), name="assigned_farmers"),
    path("analysis/", views.AgriculturalistAnalysisView.as_view(), name="analysis"),
    path("history/", views.AgriculturalistHistoryView.as_view(), name="history"),
    path("simulator/", views.AgriculturalistSimulatorView.as_view(), name="simulator"),
    path("recommendations/", views.RecommendationListView.as_view(), name="recommendations"),
    path("questions/", views.AgriculturalistQuestionListView.as_view(), name="questions"),
    path("questions/<int:pk>/", views.AgriculturalistQuestionDetailView.as_view(), name="question_detail"),
    path(
        "questions/<int:pk>/media/question-image/",
        views.ConsultationQuestionImageView.as_view(),
        name="question_image",
    ),
    path(
        "questions/<int:pk>/media/messages/<int:message_pk>/attachment/",
        views.ConsultationMessageAttachmentView.as_view(),
        name="message_attachment",
    ),
    path("questions/<int:pk>/reply/", views.AgriculturalistReplyView.as_view(), name="reply"),
    path("questions/<int:pk>/recommend/", views.RecommendationCreateView.as_view(), name="recommend"),
    path("questions/<int:pk>/complete/", views.CompleteConsultationView.as_view(), name="complete"),
    path("weather/", views.AgriculturalistWeatherView.as_view(), name="weather"),
    path("learning/", RedirectView.as_view(pattern_name="learning:list", permanent=False), name="learning"),
    path("support/", views.AgriculturalistModuleView.as_view(
        page_title="Help & Support",
        page_description="Get help with cases, data access, or platform workflows."
    ), name="support"),
]
