from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from .services import LicenseService, LicenseValidationError
import json


class LicenseMiddleware(MiddlewareMixin):
    """
    Middleware to validate device license for Pharmacy ERP.
    
    This middleware checks if the current device has a valid license
    before allowing access to the application (except for exempt paths).
    """
    
    # Paths that don't require license validation
    EXEMPT_PATHS = [
        '/admin/',  # Django admin
        '/static/',  # Static files
        '/media/',   # Media files
        '/favicon.ico',
        '/licensing/',  # Licensing endpoints (to avoid circular dependency)
        '/api/',       # API endpoints (for testing)
    ]
    
    # Paths that specifically relate to licensing (always allow)
    LICENSING_PATHS = [
        '/licensing/',
    ]
    
    def process_request(self, request):
        """
        Process the request and check for valid license.
        
        Returns:
            None: Continue processing the request
            JsonResponse: Return error response if license validation fails
        """
        # Get the path
        path = request.path_info
        
        # Check if path is exempt from license validation
        if self._is_exempt_path(path):
            return None
        
        # Skip license validation for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return None
        
        try:
            # Validate the license for the current device
            license_obj = LicenseService.validate_license()
            
            # Attach license info to request for use in views
            request.license = license_obj
            request.license_info = {
                'license_key': license_obj.license_key,
                'device_id': license_obj.device_id,
                'is_valid': license_obj.is_valid(),
                'expires_date': license_obj.expires_date.isoformat() if license_obj.expires_date else None,
            }
            
        except LicenseValidationError as e:
            # Return JSON error response for API requests
            if self._is_api_request(request):
                return JsonResponse({
                    'error': 'License validation failed',
                    'message': str(e),
                    'code': 'LICENSE_INVALID'
                }, status=403)
            
            # For HTML requests, we could redirect to a license page
            # For now, return a simple error
            return JsonResponse({
                'error': 'License validation failed',
                'message': str(e),
                'code': 'LICENSE_INVALID'
            }, status=403)
        
        except Exception as e:
            # Handle unexpected errors
            return JsonResponse({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred during license validation',
                'code': 'LICENSE_ERROR'
            }, status=500)
        
        return None
    
    def _is_exempt_path(self, path):
        """
        Check if the path is exempt from license validation.
        
        Args:
            path: The request path
            
        Returns:
            bool: True if path is exempt, False otherwise
        """
        # Check exact matches and prefixes
        for exempt_path in self.EXEMPT_PATHS:
            if path == exempt_path or path.startswith(exempt_path):
                return True
        return False
    
    def _is_api_request(self, request):
        """
        Check if the request is an API request (expects JSON response).
        
        Args:
            request: The HTTP request
            
        Returns:
            bool: True if request expects JSON, False otherwise
        """
        # Check Accept header
        accept_header = request.META.get('HTTP_ACCEPT', '')
        if 'application/json' in accept_header:
            return True
        
        # Check Content-Type for POST/PUT/PATCH
        content_type = request.META.get('HTTP_CONTENT_TYPE', '')
        if 'application/json' in content_type:
            return True
        
        # Check if path looks like an API endpoint
        if request.path.startswith('/api/'):
            return True
            
        return False