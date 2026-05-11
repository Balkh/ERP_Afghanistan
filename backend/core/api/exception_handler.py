from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied, NotFound, AuthenticationFailed, NotAuthenticated, MethodNotAllowed, Throttled
from core.api.responses import APIResponse
from core.api.errors import ErrorCode


def standardized_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        data = response.data

        if isinstance(exc, ValidationError):
            error_code = ErrorCode.VAL_001
            if isinstance(data, dict):
                messages = []
                for field, errors in data.items():
                    if isinstance(errors, list):
                        messages.append(f"{field}: {', '.join(str(e) for e in errors)}")
                    else:
                        messages.append(f"{field}: {errors}")
                message = "; ".join(messages)
            else:
                message = str(data)
        elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            error_code = ErrorCode.AUTH_003
            message = str(getattr(exc, 'detail', 'Authentication failed'))
        elif isinstance(exc, PermissionDenied):
            error_code = ErrorCode.PER_001
            message = str(getattr(exc, 'detail', 'Permission denied'))
        elif isinstance(exc, NotFound):
            error_code = ErrorCode.FIN_003
            message = str(getattr(exc, 'detail', 'Resource not found'))
        elif isinstance(exc, MethodNotAllowed):
            error_code = ErrorCode.VAL_002
            message = str(getattr(exc, 'detail', 'Method not allowed'))
        elif isinstance(exc, Throttled):
            error_code = ErrorCode.SYS_004
            message = str(getattr(exc, 'detail', 'Rate limit exceeded'))
        else:
            error_code = ErrorCode.SYS_001
            if isinstance(data, dict):
                message = data.get('detail', str(data))
            else:
                message = str(data)

        standardized = APIResponse.error(
            code=error_code,
            message=message,
        )
        response.data = standardized

    return response
