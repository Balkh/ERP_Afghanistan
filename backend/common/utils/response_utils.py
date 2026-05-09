"""
Utility functions for generating standardized API responses.
"""
from rest_framework.response import Response
from rest_framework import status
from typing import Optional, Dict, Any


class APIResponse:
    """
    Standardized API response builder.
    """
    
    @staticmethod
    def success(
        data: Optional[Any] = None,
        message: str = 'Success',
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        Build a successful API response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            
        Returns:
            DRF Response object
        """
        response_data = {
            'success': True,
            'message': message,
        }
        if data is not None:
            response_data['data'] = data
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        message: str = 'Error',
        errors: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> Response:
        """
        Build an error API response.
        
        Args:
            message: Error message
            errors: Detailed error information
            status_code: HTTP status code
            
        Returns:
            DRF Response object
        """
        response_data = {
            'success': False,
            'message': message,
        }
        if errors is not None:
            response_data['errors'] = errors
        return Response(response_data, status=status_code)
    
    @staticmethod
    def created(
        data: Optional[Any] = None,
        message: str = 'Resource created successfully'
    ) -> Response:
        """
        Build a created API response.
        
        Args:
            data: Response data
            message: Success message
            
        Returns:
            DRF Response object
        """
        return APIResponse.success(data=data, message=message, status_code=status.HTTP_201_CREATED)
    
    @staticmethod
    def no_content(message: str = 'No content') -> Response:
        """
        Build a no content API response.
        
        Args:
            message: Success message
            
        Returns:
            DRF Response object
        """
        return APIResponse.success(data=None, message=message, status_code=status.HTTP_204_NO_CONTENT)