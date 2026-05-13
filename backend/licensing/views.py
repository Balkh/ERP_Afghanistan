"""
Phase 5B.16 — Secured License Views.

Removed @csrf_exempt. Added authentication requirements.
LicenseCreateView now requires admin authentication.
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from .services import LicenseService, LicenseValidationError


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class LicenseInfoView(View):
    def get(self, request):
        try:
            license_info = LicenseService.get_license_info()
            if 'error' in license_info:
                return JsonResponse(license_info, status=403)
            return JsonResponse({'success': True, 'data': license_info})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def post(self, request):
        return self.get(request)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class LicenseValidateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body) if request.body else {}
            license_key = data.get('license_key')
            license_obj = LicenseService.validate_license(license_key=license_key)
            return JsonResponse({
                'success': True, 'message': 'License is valid',
                'data': {
                    'license_key': license_obj.license_key,
                    'device_id': license_obj.device_id,
                    'is_valid': license_obj.is_valid(),
                    'expires_date': license_obj.expires_date.isoformat() if license_obj.expires_date else None,
                }
            })
        except LicenseValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=403)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class LicenseCreateView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if not _is_admin(request.user):
            return JsonResponse({'success': False, 'error': 'Admin privileges required'}, status=403)
        try:
            data = json.loads(request.body) if request.body else {}
            license_key = data.get('license_key')
            issued_to = data.get('issued_to')
            expires_date_str = data.get('expires_date')
            notes = data.get('notes')

            if not license_key:
                return JsonResponse({'success': False, 'error': 'license_key is required'}, status=400)

            expires_date = None
            if expires_date_str:
                try:
                    from datetime import datetime
                    expires_date = datetime.strptime(expires_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

            license_obj = LicenseService.create_license(
                license_key=license_key, issued_to=issued_to,
                expires_date=expires_date, notes=notes,
            )
            return JsonResponse({
                'success': True, 'message': 'License created successfully',
                'data': {
                    'license_key': license_obj.license_key,
                    'device_id': license_obj.device_id,
                    'issued_to': license_obj.issued_to,
                    'expires_date': license_obj.expires_date.isoformat() if license_obj.expires_date else None,
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


def license_info(request):
    return JsonResponse({'success': False, 'error': 'Use API endpoint'}, status=404)


def license_validate(request):
    return JsonResponse({'success': False, 'error': 'Use API endpoint'}, status=404)


def license_create(request):
    return JsonResponse({'success': False, 'error': 'Use API endpoint'}, status=404)
