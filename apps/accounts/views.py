from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import activate
from django.views import View
from django.views.generic import FormView, UpdateView

from .forms import AccountSettingsForm, EmailAuthenticationForm, ProfileForm, SignUpForm
from .models import AgriculturalistVerification, User
from .tokens import create_verification_token, read_verification_token


def _client_address(request):
    remote_address = request.META.get("REMOTE_ADDR", "unknown").strip() or "unknown"
    if not getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        return remote_address
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else remote_address) or remote_address


def _record_failed_login(rate_key):
    # add/incr avoids losing simultaneous failures to a get-then-set race.
    for _attempt in range(2):
        if cache.add(rate_key, 1, timeout=300):
            return
        try:
            cache.incr(rate_key)
            return
        except ValueError:
            # The entry expired between add() and incr(); retry atomically.
            continue


def _send_verification_email(request, user):
    token = create_verification_token(user)
    link = request.build_absolute_uri(reverse("accounts:verify_email", args=[token]))
    send_mail(
        "Verify your Farm Time Machine account",
        f"Verify your email address by visiting: {link}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        self.rate_key = f"login:{_client_address(request)}"
        if request.method == "POST" and cache.get(self.rate_key, 0) >= 10:
            return render(request, self.template_name, {"rate_limited": True}, status=429)
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        _record_failed_login(self.rate_key)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self.rate_key)
        return super().form_valid(form)


class SignUpView(FormView):
    template_name = "accounts/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        user = form.save()
        if user.role == User.Role.AGRICULTURALIST:
            AgriculturalistVerification.objects.create(agriculturalist=user.agriculturalist_profile)
        _send_verification_email(self.request, user)
        messages.success(self.request, "Account created. Check your email for the verification link.")
        return super().form_valid(form)


def verify_email(request, token):
    try:
        data = read_verification_token(token, settings.EMAIL_VERIFICATION_MAX_AGE)
    except SignatureExpired:
        messages.error(request, "That verification link has expired.")
    except BadSignature:
        messages.error(request, "That verification link is invalid.")
    else:
        user = get_object_or_404(User, pk=data["user_id"], email=data["email"])
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])
        messages.success(request, "Your email address is verified. You can now sign in.")
    return redirect("accounts:login")


def post_login_redirect(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role == User.Role.FARMER and not request.user.is_verified:
        messages.warning(request, "Verify your email address before opening the Farmer workspace.")
        return redirect("accounts:profile")
    destination = {
        User.Role.ADMIN: "administration:dashboard",
        User.Role.AGRICULTURALIST: "dashboard:agriculturalist_dashboard",
        User.Role.FARMER: "dashboard:farmer_dashboard",
    }
    return redirect(destination[request.user.role])


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def dispatch(self, request, *args, **kwargs):
        self.previous_email = request.user.email
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        email_changed = self.previous_email.casefold() != form.cleaned_data["email"].casefold()
        if email_changed:
            form.instance.is_verified = False
        response = super().form_valid(form)
        if email_changed:
            _send_verification_email(self.request, self.object)
            messages.warning(
                self.request,
                "Your email address changed. Verify the new address before returning to the Farmer workspace.",
            )
        else:
            messages.success(self.request, "Your profile has been updated.")
        return response


class SettingsView(LoginRequiredMixin, UpdateView):
    form_class = AccountSettingsForm
    template_name = "accounts/settings.html"
    success_url = reverse_lazy("accounts:settings")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        activate(self.object.preferred_language)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            self.object.preferred_language,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )
        messages.success(self.request, "Your account preferences have been saved.")
        return response


class AccountPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:settings")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed securely.")
        return super().form_valid(form)


class SecureLogoutView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "You have been signed out.")
        return redirect("core:home")
