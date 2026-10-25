from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse


def admin_required(view_func):
    """Restrict a view to admin-role users only.

    - Unauthenticated users → redirect to login (page) or 401 JSON (API)
    - Authenticated non-admins → 403 page or 403 JSON
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_api = request.path.startswith("/api/")
        if not request.user.is_authenticated:
            if is_api:
                return JsonResponse(
                    {"error": {"code": "AUTH_REQUIRED", "message": "Please log in to continue."}},
                    status=401,
                )
            return redirect(f"/login/?next={request.path}")
        if not getattr(request.user, "is_admin", False):
            if is_api:
                return JsonResponse(
                    {"error": {"code": "FORBIDDEN", "message": "You don't have permission to do that."}},
                    status=403,
                )
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
