from django.urls import path

from . import views


app_name = "ai_assistant"
urlpatterns = [
    path("", views.AssistantPanelView.as_view(), name="panel"),
    path("chat/", views.ChatView.as_view(), name="chat"),
    path("new/", views.NewConversationView.as_view(), name="new_conversation"),
]
