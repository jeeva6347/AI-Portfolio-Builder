from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

class SuperAdminRequiredMixin(AccessMixin):
    """Verify that the current user is a Super Admin."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_super_admin:
            raise PermissionDenied("You do not have permission to view this page. Super Admin access required.")
        return super().dispatch(request, *args, **kwargs)

class AdminRequiredMixin(AccessMixin):
    """Verify that the current user is an Admin or Super Admin."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_platform_admin:
            raise PermissionDenied("You do not have permission to view this page. Admin access required.")
        return super().dispatch(request, *args, **kwargs)
