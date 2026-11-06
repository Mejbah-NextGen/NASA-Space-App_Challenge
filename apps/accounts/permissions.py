from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import User
from .verification import user_has_verified_email


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()
    raise_exception = True

    def test_func(self):
        return self.request.user.role in self.allowed_roles

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())
        raise PermissionDenied(self.get_permission_denied_message())


class FarmerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.FARMER,)

    def test_func(self):
        return super().test_func() and user_has_verified_email(self.request.user)

    def get_permission_denied_message(self):
        if self.request.user.role == User.Role.FARMER and not user_has_verified_email(self.request.user):
            return "Verify your email address before opening the Farmer workspace."
        return "A Farmer account is required for this workspace."


class AgriculturalistRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.AGRICULTURALIST,)

    def test_func(self):
        user = self.request.user
        return (
            super().test_func()
            and user_has_verified_email(user)
            and hasattr(user, "agriculturalist_profile")
            and user.agriculturalist_profile.is_approved
        )


class PlatformAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.ADMIN,)

    def test_func(self):
        return super().test_func() and user_has_verified_email(self.request.user)


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login

                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
