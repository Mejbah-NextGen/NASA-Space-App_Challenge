from django.urls import path

from . import views


app_name = "core"
urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.StaticPageView.as_view(template_name="public/about.html"), name="about"),
    path("how-it-works/", views.StaticPageView.as_view(template_name="public/how_it_works.html"), name="how_it_works"),
    path("help/", views.HelpView.as_view(), name="help"),
    path("contact/", views.HelpView.as_view(template_name="public/contact.html"), name="contact"),
    path("privacy/", views.StaticPageView.as_view(template_name="public/privacy.html"), name="privacy"),
    path("terms/", views.StaticPageView.as_view(template_name="public/terms.html"), name="terms"),
]
