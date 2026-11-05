from django.urls import path

from . import views


app_name = "farmer_consultations"
urlpatterns = [
    path("", views.FarmerConsultationListView.as_view(), name="list"),
    path("experts/", views.ExpertDirectoryView.as_view(), name="expert_list"),
    path("new/", views.ConsultationCreateView.as_view(), name="create"),
    path("<int:pk>/", views.FarmerConsultationDetailView.as_view(), name="detail"),
    path("<int:pk>/media/question-image/", views.ConsultationQuestionImageView.as_view(), name="question_image"),
    path(
        "<int:pk>/media/messages/<int:message_pk>/attachment/",
        views.ConsultationMessageAttachmentView.as_view(),
        name="message_attachment",
    ),
    path("<int:pk>/message/", views.FarmerSendMessageView.as_view(), name="message"),
    path("<int:pk>/close/", views.FarmerCloseConsultationView.as_view(), name="close"),
    path("<int:pk>/consent/revoke/", views.RevokeConsentView.as_view(), name="revoke_consent"),
    path("<int:pk>/consent/grant/", views.GrantConsentView.as_view(), name="grant_consent"),
]
