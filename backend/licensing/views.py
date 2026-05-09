from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
from .services import LicenseService, LicenseValidationError


@method_decorator(csrf_exempt, name='dispatch')
class LicenseInfoView(View):
    """
    API endpoint to get license information for the current device.
    """
    
    def get(self, request):
        """Get license information."""
        try:
            license_info = LicenseService.get_license_info()
            if 'error' in license_info:
                return JsonResponse(license_info, status=403)
            return JsonResponse({'success': True, 'data': license_info})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def post(self, request):
        """Validate license (alternative to GET)."""
        return self.get(request)


@method_decorator(csrf_exempt, name='dispatch')
class LicenseValidateView(View):
    """
    API endpoint to explicitly validate license.
    """
    
    def post(self, request):
        """Validate license."""
        try:
            data = json.loads(request.body) if request.body else {}
            license_key = data.get('license_key')
            
            license_obj = LicenseService.validate_license(license_key=license_key)
            
            return JsonResponse({
                'success': True,
                'message': 'License is valid',
                'data': {
                    'license_key': license_obj.license_key,
                    'device_id': license_obj.device_id,
                    'is_valid': license_obj.is_valid(),
                    'expires_date': license_obj.expires_date.isoformat() if license_obj.expires_date else None,
                }
            })
        except LicenseValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=403)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class LicenseCreateView(View):
    """
    API endpoint to create a new license for the current device.
    """
    
    def post(self, request):
        """Create a new license."""
        try:
            data = json.loads(request.body) if request.body else {}
            license_key = data.get('license_key')
            issued_to = data.get('issued_to')
            expires_date_str = data.get('expires_date')
            notes = data.get('notes')
            
            # Validate required fields
            if not license_key:
                return JsonResponse({
                    'success': False,
                    'error': 'license_key is required'
                }, status=400)
            
            expires_date = None
            if expires_date_str:
                try:
                    from datetime import datetime
                    expires_date = datetime.strptime(expires_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid date format. Use YYYY-MM-DD'
                    }, status=400)
            
            license_obj = LicenseService.create_license(
                license_key=license_key,
                issued_to=issued_to,
                expires_date=expires_date,
                notes=notes
            )
            
            return JsonResponse({
                'success': True,
                'message': 'License created successfully',
                'data': {
                    'license_key': license_obj.license_key,
                    'device_id': license_obj.device_id,
                    'issued_to': license_obj.issued_to,
                    'expires_date': license_obj.expires_date.isoformat() if license_obj.expires_date else None,
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


# Simple function-based views for ease of URL configuration
def license_info(request):
    """Function-based view for license info."""
    view = LicenseInfoView.as_view()
    return view(request._request if hasattr(request, '_request') else request)


def license_validate(request):
    """Function-based view for license validation."""
    view = LicenseValidateView.as_view()
    return view(request._request if hasattr(request, '_request') else request)


def license_create(request):
    """Function-based view for license creation."""
    view = LicenseCreateView.as_view()
    return view(request._request if hasattr(request, '_request') else request)
