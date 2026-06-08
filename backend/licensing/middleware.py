from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .validator import resolve_license


class LicenseMiddleware(MiddlewareMixin):
    """
    Lightweight license middleware.

    State handling:
      dev      → No restrictions
      trial    → Full access (header: X-License-Mode: trial)
      limited  → Only /licensing/ and /api/system/ accessible, all else blocked
      licensed → Full access
    """

    EXEMPT_PATHS = [
        '/admin/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/licensing/',
    ]

    ALLOWED_LIMITED_PATHS = [
        '/licensing/',
        '/api/system/',
        '/api/backup/',
    ]

    def process_request(self, request):
        path = request.path_info

        if self._is_exempt_path(path):
            return None

        if request.method == 'OPTIONS':
            return None

        try:
            state = resolve_license(request)
            request.license_state = state
            request.license_mode = state['mode']
            request.license_info = state

            if state['mode'] in ("dev", "licensed", "trial"):
                return None

            if state['mode'] == "limited":
                if not self._is_allowed_in_limited(path):
                    return JsonResponse({
                        'error': 'Trial period expired',
                        'message': state.get('message',
                                            'Trial has expired. Please activate a license.'),
                        'code': 'TRIAL_EXPIRED',
                        'restricted': True,
                    }, status=403)
                return None

            return JsonResponse({
                'error': 'License required',
                'message': state.get('message', 'No valid license found.'),
                'code': 'LICENSE_REQUIRED',
            }, status=403)

        except Exception:
            request.license_mode = 'unknown'
            request.license_state = {'mode': 'unknown', 'is_valid': False,
                                      'message': 'License validation unavailable'}
            return None

    def _is_exempt_path(self, path):
        for p in self.EXEMPT_PATHS:
            if path == p or path.startswith(p):
                return True
        return False

    def _is_allowed_in_limited(self, path):
        for p in self.ALLOWED_LIMITED_PATHS:
            if path == p or path.startswith(p):
                return True
        return False
