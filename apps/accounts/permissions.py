from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from .models import User


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()
    raise_exception = True

    def test_func(self):
        return self.request.user.role in self.allowed_roles


class FarmerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.FARMER,)
    permission_denied_message = "Verify your email address before opening the Farmer workspace."

    def test_func(self):
        return super().test_func() and self.request.user.is_verified


class AgriculturalistRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.AGRICULTURALIST,)

    def test_func(self):
        user = self.request.user
        return (
            super().test_func()
            and hasattr(user, "agriculturalist_profile")
            and user.agriculturalist_profile.is_approved
        )


class PlatformAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.ADMIN,)


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
