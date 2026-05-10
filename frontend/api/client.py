import json
import requests
import time
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication
from typing import Dict, Any, Optional, Callable
from utils.logger import get_logger, record_api_time, record_error

log = get_logger('api')

DEBUG_MODE = True
DEFAULT_TIMEOUT = 30  # seconds


class APIError(Exception):
    """Custom API error with status code."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class APIClient(QObject):
    """API client for communicating with the backend server."""
    
    # Signals
    request_started = Signal(str)  # endpoint
    request_finished = Signal(str, bool)  # endpoint, success
    request_error = Signal(str, str)  # endpoint, error_message
    response_received = Signal(str, object)  # endpoint, data
    session_expired = Signal()  # emitted when token refresh fails
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__()
        self.base_url = base_url
        self.session = requests.Session()
        self._auth_token = None
        self._refresh_token = None
        self._refreshing = False
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json; version=v1"
        })
        # Track loading state
        self._loading_count = 0
    
    def _make_request(self, method: str, endpoint: str, 
                      data: Optional[Dict] = None, 
                      params: Optional[Dict] = None,
                      headers: Optional[Dict] = None) -> Any:
        """Make an HTTP request and return the response data."""
        _req_start = time.time()
        # Update loading state
        self._loading_count += 1
        if self._loading_count == 1:
            # Show loading overlay on first request
            from ui.main_window import MainWindow
            # Find the main window to show loading overlay
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if isinstance(widget, MainWindow):
                    widget.loading_overlay.show_overlay()
                    break
        
        url = f"{self.base_url}{endpoint}"
        
        log.info(f"{method} {endpoint}", extra={'extra_fields': {'tags': ['api', 'request']}})
        
        # Emit started signal
        self.request_started.emit(endpoint)
        
        try:
            # Prepare request
            request_headers = self.session.headers.copy()
            if self._auth_token:
                request_headers["Authorization"] = f"Bearer {self._auth_token}"
            if headers:
                request_headers.update(headers)
            
            # Make request with timeout
            response = self.session.request(
                method=method,
                url=url,
                json=data if data else None,
                params=params,
                headers=request_headers,
                timeout=DEFAULT_TIMEOUT
            )
            
            log.debug(f"{method} {endpoint} -> {response.status_code}",
                       extra={'extra_fields': {'tags': ['api'], 'status': response.status_code}})
            
            # Handle different status codes
            if response.status_code == 401:
                log.warning(f"{method} {endpoint} -> 401 Unauthorized",
                             extra={'extra_fields': {'tags': ['api', 'auth', 'error']}})
                if self._refresh_token and not self._refreshing:
                    self._refreshing = True
                    if self._attempt_token_refresh():
                        self._refreshing = False
                        return self._make_request(method, endpoint, data, params, headers)
                    self._refreshing = False
                    log.warning("Token refresh failed, session expired",
                                 extra={'extra_fields': {'tags': ['auth', 'session']}})
                    self.session_expired.emit()
                record_error(exc_type='APIError:401', endpoint=endpoint, category='auth')
                raise APIError("Unauthorized - please login", 401, response)
            elif response.status_code == 403:
                log.warning(f"{method} {endpoint} -> 403 Forbidden",
                             extra={'extra_fields': {'tags': ['api', 'auth', 'error']}})
                record_error(exc_type='APIError:403', endpoint=endpoint, category='auth')
                raise APIError("Forbidden - access denied", 403, response)
            elif response.status_code == 404:
                log.warning(f"{method} {endpoint} -> 404 Not Found",
                             extra={'extra_fields': {'tags': ['api', 'error']}})
                record_error(exc_type='APIError:404', endpoint=endpoint, category='api')
                raise APIError("Not found", 404, response)
            elif response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                except:
                    error_msg = response.text
                log.warning(f"{method} {endpoint} -> {response.status_code}: {error_msg}",
                             extra={'extra_fields': {'tags': ['api', 'error'], 'status': response.status_code}})
                record_error(exc_type=f'APIError:{response.status_code}', endpoint=endpoint, category='api')
                raise APIError(f"API Error: {error_msg}", response.status_code, response)
            
            # Parse JSON response
            try:
                response_data = response.json() if response.content else {}
            except json.JSONDecodeError:
                response_data = {"raw": response.text}
            
            log.debug(f"{method} {endpoint} response received",
                       extra={'extra_fields': {'tags': ['api'], 'response_type': type(response_data).__name__}})
            
            # Handle standardized response format
            if isinstance(response_data, dict):
                # Check for error in response
                if not response_data.get("success", True):
                    error_info = response_data.get("error", {})
                    record_error(exc_type='APISuccessFalse', endpoint=endpoint, category='api')
                    raise APIError(error_info.get("message", "API request failed"), response.status_code, response_data)
            
            # Emit success signals
            self.request_finished.emit(endpoint, True)
            self.response_received.emit(endpoint, response_data)
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            log.warning(f"{method} {endpoint} request failed: {error_msg}",
                         extra={'extra_fields': {'tags': ['api', 'error']}})
            record_error(exc_type='RequestException', endpoint=endpoint, category='api')
            self.request_finished.emit(endpoint, False)
            self.request_error.emit(endpoint, error_msg)
            raise APIError(error_msg)
        finally:
            _duration_ms = (time.time() - _req_start) * 1000
            record_api_time(endpoint, _duration_ms)
            # Update loading state
            self._loading_count -= 1
            if self._loading_count <= 0:
                self._loading_count = 0
                # Hide loading overlay safely
                self._hide_loading_overlay()

    def _hide_loading_overlay(self):
        """Safely hide the loading overlay."""
        try:
            from ui.main_window import MainWindow
            app = QApplication.instance()
            if not app:
                return
            for widget in app.topLevelWidgets():
                if isinstance(widget, MainWindow) and hasattr(widget, 'loading_overlay'):
                    widget.loading_overlay.hide_overlay()
                    break
        except Exception:
            pass
    
    def get(self, endpoint: str, params: Optional[Dict] = None, 
            headers: Optional[Dict] = None, retries: int = 3) -> Any:
        """Make a GET request with automatic retries for network issues."""
        last_error = None
        for attempt in range(retries):
            try:
                return self._make_request("GET", endpoint, params=params, headers=headers)
            except APIError as e:
                # If it's a 4xx error, don't retry (it's a client error)
                if e.status_code and 400 <= e.status_code < 500:
                    self._show_error_toast("GET", endpoint, str(e))
                    return {"success": False, "data": [], "error": str(e)}
                last_error = e
                time.sleep(1 * (attempt + 1)) # Exponential backoff
            except Exception as e:
                last_error = e
                time.sleep(1 * (attempt + 1))
        
        log.error(f"GET {endpoint} failed after {retries} attempts: {last_error}",
                   extra={'extra_fields': {'tags': ['api', 'error'], 'retries': retries}})
        self._show_error_toast("GET", endpoint, f"Connection failed after {retries} retries.")
        return {"success": False, "data": [], "error": str(last_error)}
    
    def post(self, endpoint: str, data: Optional[Dict] = None,
            headers: Optional[Dict] = None) -> Any:
        """Make a POST request."""
        try:
            return self._make_request("POST", endpoint, data=data, headers=headers)
        except APIError as e:
            log.warning(f"POST {endpoint} failed: {e}",
                         extra={'extra_fields': {'tags': ['api', 'error'], 'status': e.status_code}})
            # Show error toast
            from ui.main_window import MainWindow
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if isinstance(widget, MainWindow):
                    widget.toast_manager.show_error(f"POST {endpoint} failed: {str(e)}")
                    break
            return {"success": False, "error": {"message": str(e)}}
        except Exception as e:
            log.error(f"POST {endpoint} unexpected error: {e}",
                       extra={'extra_fields': {'tags': ['api', 'error']}})
            # Show error toast
            from ui.main_window import MainWindow
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if isinstance(widget, MainWindow):
                    widget.toast_manager.show_error(f"POST {endpoint} failed: {str(e)}")
                    break
            return {"success": False, "error": {"message": str(e)}}
    
    def put(self, endpoint: str, data: Optional[Dict] = None,
            headers: Optional[Dict] = None) -> Any:
        """Make a PUT request."""
        try:
            return self._make_request("PUT", endpoint, data=data, headers=headers)
        except APIError as e:
            log.warning(f"PUT {endpoint} failed: {e}",
                         extra={'extra_fields': {'tags': ['api', 'error'], 'status': e.status_code}})
            # Show error toast
            from ui.main_window import MainWindow
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if isinstance(widget, MainWindow):
                    widget.toast_manager.show_error(f"PUT {endpoint} failed: {str(e)}")
                    break
            return {"success": False, "error": {"message": str(e)}}
        except Exception as e:
            log.error(f"PUT {endpoint} unexpected error: {e}",
                       extra={'extra_fields': {'tags': ['api', 'error']}})
            # Show error toast
            from ui.main_window import MainWindow
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if isinstance(widget, MainWindow):
                    widget.toast_manager.show_error(f"PUT {endpoint} failed: {str(e)}")
                    break
            return {"success": False, "error": {"message": str(e)}}
    
    def delete(self, endpoint: str, headers: Optional[Dict] = None) -> Any:
        """Make a DELETE request."""
        try:
            return self._make_request("DELETE", endpoint, headers=headers)
        except APIError as e:
            log.warning(f"DELETE {endpoint} failed: {e}",
                         extra={'extra_fields': {'tags': ['api', 'error'], 'status': e.status_code}})
            return {"success": False, "error": {"message": str(e)}}
        except Exception as e:
            log.error(f"DELETE {endpoint} unexpected error: {e}",
                       extra={'extra_fields': {'tags': ['api', 'error']}})
            return {"success": False, "error": {"message": str(e)}}

    def _show_error_toast(self, method: str, endpoint: str, error: str):
        """Centralized error toast display."""
        try:
            from ui.main_window import MainWindow
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if isinstance(widget, MainWindow):
                    widget.toast_manager.show_error(f"{method} {endpoint}: {error}")
                    break
        except Exception:
            pass  # Silently fail if toast unavailable

    def parse_api_error(self, response_data: Dict) -> str:
        """Parse API error response into user-friendly message."""
        if not isinstance(response_data, dict):
            return "Unknown error occurred"
        
        # Check for standardized error format
        error_info = response_data.get("error", {})
        if isinstance(error_info, dict):
            return error_info.get("message", "Unknown error")
        
        # Check for success=False
        if not response_data.get("success", True):
            return response_data.get("error", "Unknown error")
        
        return "Unknown error occurred"

    def health_check(self) -> bool:
        """
        Perform a health check request to the backend.
        Returns True if the backend is reachable and responding, False otherwise.
        This method does not show toasts or trigger loading overlay.
        """
        try:
            # Make a raw request without using _make_request to avoid loading overlay and toasts
            url = f"{self.base_url}/health/"
            log.debug("Health check", extra={'extra_fields': {'tags': ['api', 'health']}})
            
            # Prepare request
            request_headers = self.session.headers.copy()
            if self._auth_token:
                request_headers["Authorization"] = f"Bearer {self._auth_token}"
            
            # Make request with a short timeout
            response = self.session.get(url, headers=request_headers, timeout=5)
            
            log.debug(f"Health check status: {response.status_code}",
                       extra={'extra_fields': {'tags': ['api', 'health'], 'status': response.status_code}})
            
            # Consider 2xx and 4xx as reachable (the server is responding)
            # 5xx or connection errors are not reachable
            if response.status_code < 500:
                return True
            else:
                return False
        except requests.exceptions.RequestException:
            # Connection error, timeout, etc.
            return False
        except Exception:
            # Any other error
            return False
    
    def set_auth_token(self, token: str):
        """Set authorization token for requests."""
        self._auth_token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def set_auth_data(self, data: dict):
        """Set both access and refresh tokens from login/refresh response."""
        access = data.get('access_token') or data.get('token') or data.get('access')
        refresh = data.get('refresh_token')
        if access:
            self.set_auth_token(access)
        if refresh:
            self._refresh_token = refresh

    def clear_auth_token(self):
        """Clear authorization token and refresh token."""
        self._auth_token = None
        self._refresh_token = None
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]

    def _attempt_token_refresh(self) -> bool:
        """Try to refresh the access token using the stored refresh token.
        Returns True if refresh succeeded, False otherwise.
        """
        if not self._refresh_token:
            log.warning("Token refresh attempted but no refresh token available",
                         extra={'extra_fields': {'tags': ['auth', 'token']}})
            return False
        try:
            url = f"{self.base_url}/api/auth/token/refresh/"
            response = self.session.post(url, json={
                'refresh_token': self._refresh_token
            }, timeout=DEFAULT_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                response_data = data if isinstance(data, dict) else {}
                inner = response_data.get('data') if isinstance(response_data, dict) else response_data
                if isinstance(inner, dict):
                    self.set_auth_data(inner)
                else:
                    self.set_auth_data(response_data)
                log.info("Token refresh succeeded",
                         extra={'extra_fields': {'tags': ['auth', 'token']}})
                return True
            log.warning(f"Token refresh failed with status {response.status_code}",
                         extra={'extra_fields': {'tags': ['auth', 'token', 'error'], 'status': response.status_code}})
            return False
        except Exception as e:
            log.warning(f"Token refresh error: {e}",
                         extra={'extra_fields': {'tags': ['auth', 'token', 'error']}})
            return False

    def is_authenticated(self) -> bool:
        """Check if client has authentication token."""
        return bool(self._auth_token)
    
    # Dashboard API methods
    
    def get_control_center(self):
        """Get complete control center dashboard data."""
        return self.get("/api/control-center/")

    def get_control_center_stats(self):
        """Get quick KPI stats."""
        return self.get("/api/control-center/stats/")

    def get_control_center_financial(self):
        """Get financial summary."""
        return self.get("/api/control-center/financial/")

    def get_control_center_inventory(self):
        """Get inventory summary."""
        return self.get("/api/control-center/inventory/")

    def get_control_center_hr(self):
        """Get HR summary."""
        return self.get("/api/control-center/hr/")

    def get_control_center_operations(self):
        """Get operations summary."""
        return self.get("/api/control-center/operations/")

    def get_executive_dashboard(self, start_date=None, end_date=None):
        """Get executive summary dashboard from control center."""
        return self.get_control_center()
    
    def get_sales_dashboard(self, start_date=None, end_date=None):
        """Get sales dashboard — redirected to control center."""
        return self.get_control_center()
    
    def get_inventory_dashboard(self, as_of_date=None):
        """Get inventory dashboard."""
        return self.get_control_center_inventory()
    
    def get_financial_dashboard(self, start_date=None, end_date=None):
        """Get financial dashboard."""
        return self.get_control_center_financial()
    
    def get_hr_dashboard(self, as_of_date=None):
        """Get HR dashboard."""
        return self.get_control_center_hr()
    
    # Barcode/Mobile API methods
    
    def lookup_barcode(self, barcode):
        """Look up product by barcode."""
        return self.get("/api/inventory/products/by_barcode/", params={'barcode': barcode})
    
    def lookup_sku(self, sku):
        """Look up product by SKU."""
        return self.get("/api/inventory/products/by_sku/", params={'sku': sku})
    
    def search_products(self, query):
        """Search products by name, barcode, or sku."""
        return self.get("/api/inventory/products/", params={'search': query})
    
    def get_product_detail(self, product_id):
        """Get product detail with batches."""
        return self.get(f"/api/inventory/products/{product_id}/")
    
    def get_product_by_barcode_or_sku(self, code):
        """Quick lookup - try barcode first, then SKU."""
        result = self.lookup_barcode(code)
        if result.get('success'):
            return result
        return self.lookup_sku(code)
    
    # User Management API methods
    
    def get_users(self, search=None, page=1):
        """Get list of users."""
        params = {'page': page}
        if search:
            params['search'] = search
        return self.get("/api/auth/users/", params=params)
    
    def get_user(self, user_id):
        """Get user detail."""
        return self.get(f"/api/auth/users/{user_id}/")
    
    def create_user(self, data):
        """Create new user."""
        return self.post("/api/auth/users/", data)
    
    def update_user(self, user_id, data):
        """Update user."""
        return self.put(f"/api/auth/users/{user_id}/", data)
    
    def delete_user(self, user_id):
        """Delete user."""
        return self.delete(f"/api/auth/users/{user_id}/")
    
    def get_roles(self):
        """Get list of roles."""
        return self.get("/api/auth/roles/")
    
    def get_permissions(self, modules=None):
        """Get list of permissions."""
        params = {}
        if modules:
            params['modules'] = modules
        return self.get("/api/auth/permissions/", params=params)
    
    # Export API methods
    
    def export_report(self, report_type, report_data, format='excel'):
        """
        Export report to specified format.
        
        Args:
            report_type: Type of report (trial_balance, profit_loss, etc.)
            report_data: Report data dictionary
            format: Export format (csv, excel, pdf, json)
        
        Returns:
            bytes: File content (use to download)
        """
        data = {
            'report_type': report_type,
            'report_data': report_data,
            'format': format
        }
        
        try:
            return self.post("/api/accounting/export/", data, raw_response=True)
        except Exception as e:
            log.error(f"Export error: {e}",
                       extra={'extra_fields': {'tags': ['api', 'export', 'error']}})
            return None
    
    def download_report(self, report_type, report_data, format='excel', filename=None):
        """
        Download report - wrapper around export that handles file saving.
        
        Args:
            report_type: Type of report
            report_data: Report data
            format: Export format (csv, excel, pdf)
            filename: Optional filename
        
        Returns:
            tuple: (success: bool, filename: str, error: str)
        """
        response = self.export_report(report_type, report_data, format)
        
        if response is None:
            return (False, '', "Export failed - no response")
        
        # Check if response is HttpResponse
        if hasattr(response, 'content'):
            if response.status_code >= 400:
                return (False, '', f"Export failed with status {response.status_code}")
            
            # Generate filename
            from datetime import date
            if not filename:
                ext = 'xlsx' if format == 'excel' else format
                filename = f"{report_type}_{date.today()}.{ext}"
            
            # Save file
            try:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return (True, filename, '')
            except Exception as e:
                return (False, '', f"Failed to save file: {e}")
        
        return (False, '', "Invalid response")
    
    # Advanced Reports API methods
    
    def get_report_options(self):
        """Get available report types."""
        return self.get("/api/accounting/report-options/")
    
    def generate_advanced_report(self, report_type, start_date=None, end_date=None, 
                                  account_code='1100', config=None):
        """
        Generate advanced report.
        
        Args:
            report_type: Type of report
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            account_code: For cash book reports
            config: Custom report configuration
        """
        data = {
            'report_type': report_type
        }
        
        if start_date:
            data['start_date'] = start_date
        if end_date:
            data['end_date'] = end_date
        if account_code:
            data['account_code'] = account_code
        if config:
            data['config'] = config
        
        return self.post("/api/accounting/reports/", data)
    
    # === Workflow Methods ===
    
    def get_workflow_status(self, entity_type: str, entity_id: int) -> Dict[str, Any]:
        """Get workflow status for an entity."""
        return self.get(f"/api/workflows/status/{entity_type}/{entity_id}/")
    
    def workflow_action(self, workflow_id: int, action: str, comment: str = '') -> Dict[str, Any]:
        """Perform workflow action (submit, approve, reject, post, cancel, reopen)."""
        return self.post(f"/api/workflows/action/{workflow_id}/", {
            'action': action,
            'comment': comment
        })
    
    def get_workflow_instances(self, **filters) -> Dict[str, Any]:
        """Get workflow instances with optional filters."""
        return self.get("/api/workflows/instances/", params=filters)
    
    def create_workflow_instance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow instance."""
        return self.post("/api/workflows/instances/", data)
    
    def get_approval_chains(self, **filters) -> Dict[str, Any]:
        """Get approval chains."""
        return self.get("/api/workflows/chains/", params=filters)
    
    def get_my_pending_approvals(self) -> Dict[str, Any]:
        """Get pending approval requests for current user."""
        return self.get("/api/workflows/my-pending/")
    
    def process_approval_request(self, request_id: int, action: str, comment: str = '') -> Dict[str, Any]:
        """Approve or reject an approval request."""
        return self.post(f"/api/workflows/request/{request_id}/action/", {
            'action': action,
            'comment': comment
        })