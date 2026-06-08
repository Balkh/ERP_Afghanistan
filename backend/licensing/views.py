import json
import os
import tempfile
from datetime import datetime
from django.http import JsonResponse
from django.views import View

from .services import LicenseService, LicenseValidationError
from .validator import LicenseValidator


class LicenseInfoView(View):
    """GET /licensing/info/ — Current license state (exempt from middleware)."""
    def get(self, request):
        try:
            val = LicenseValidator()
            val.validate()
            return JsonResponse({'success': True, 'data': val.get_info()})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'data': {'mode': 'error', 'is_valid': False, 'message': str(e)},
            }, status=500)

    def post(self, request):
        return self.get(request)


class LicenseValidateView(View):
    """POST /licensing/validate/ — Validate a specific license key."""
    def post(self, request):
        try:
            data = json.loads(request.body) if request.body else {}
            result = LicenseService.validate_license(license_key=data.get('license_key'))

            if result is None:
                return JsonResponse({'success': True, 'message': 'Dev mode or trialing'})
            if hasattr(result, 'license_key'):
                return JsonResponse({
                    'success': True, 'message': 'License is valid',
                    'data': {
                        'license_key': result.license_key,
                        'is_valid': result.is_valid(),
                        'expires_date': result.expires_date.isoformat() if result.expires_date else None,
                    }
                })
            if hasattr(result, 'days_remaining'):
                return JsonResponse({
                    'success': True, 'message': 'Trial is active',
                    'data': {'mode': 'trial', 'days_remaining': result.days_remaining()},
                })
            return JsonResponse({'success': True, 'message': 'Valid'})
        except LicenseValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=403)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class LicenseCreateView(View):
    """POST /licensing/create/ — Admin: create a new device license."""
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Admin privileges required'}, status=403)
        try:
            data = json.loads(request.body) if request.body else {}
            expires_date = None
            if data.get('expires_date'):
                try:
                    expires_date = datetime.strptime(data['expires_date'], '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

            lic = LicenseService.create_license(
                license_key=data.get('license_key'),
                issued_to=data.get('issued_to'),
                expires_date=expires_date,
                notes=data.get('notes'),
            )
            return JsonResponse({
                'success': True, 'message': 'License created',
                'data': {
                    'license_key': lic.license_key,
                    'device_id': lic.device_id,
                    'issued_to': lic.issued_to,
                    'expires_date': lic.expires_date.isoformat() if lic.expires_date else None,
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class LicenseActivationRequestView(View):
    """GET /licensing/activation-request/ — Generate activation_request.json."""
    def get(self, request):
        try:
            val = LicenseValidator()
            out_path = val.generate_activation_request()
            with open(out_path) as f:
                content = json.load(f)
            return JsonResponse({
                'success': True, 'message': 'Activation request generated',
                'data': {'file_path': out_path, 'content': content},
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def post(self, request):
        return self.get(request)


class LicenseImportView(View):
    """POST /licensing/import-license/ — Import a signed .lic file."""
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Admin privileges required'}, status=403)
        try:
            uploaded = request.FILES.get('license_file')
            if uploaded:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.lic') as tmp:
                    for chunk in uploaded.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                try:
                    message = LicenseService.import_license_file(tmp_path)
                finally:
                    os.unlink(tmp_path)
                return JsonResponse({'success': True, 'message': message})

            data = json.loads(request.body) if request.body else {}
            file_path = data.get('file_path')
            if not file_path:
                return JsonResponse({'success': False, 'error': 'Provide license_file or file_path'}, status=400)
            message = LicenseService.import_license_file(file_path)
            return JsonResponse({'success': True, 'message': message})

        except LicenseValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class LicenseStatusView(View):
    """GET /licensing/status/ — Detailed license state (same as info)."""
    def get(self, request):
        try:
            val = LicenseValidator()
            val.validate()
            info = val.get_info()
            info['timestamp'] = datetime.utcnow().isoformat() + 'Z'
            return JsonResponse({'success': True, 'data': info})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'data': {'mode': 'error', 'is_valid': False, 'message': str(e)},
            }, status=500)
