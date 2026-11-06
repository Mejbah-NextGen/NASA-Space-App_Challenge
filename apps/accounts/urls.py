from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views


app_name = "accounts"
urlpatterns = [
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("logout/", views.SecureLogoutView.as_view(), name="logout"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    path("post-login/", views.post_login_redirect, name="post_login"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/image/", views.ProfileImageView.as_view(), name="profile_image"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("change-password/", views.AccountPasswordChangeView.as_view(), name="password_change"),
    path("forgot-password/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html",
        email_template_name="accounts/password_reset_email.txt",
        success_url=reverse_lazy("accounts:password_reset_done"),
    ), name="password_reset"),
    path("forgot-password/sent/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url=reverse_lazy("accounts:password_reset_complete"),
    ), name="password_reset_confirm"),
    path("reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
]
