"""
Custom exception handlers for DRF
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats PermissionDenied exceptions
    to include detailed error information for the frontend.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Handle PermissionDenied exceptions specially
    if isinstance(exc, PermissionDenied) and response is not None:
        # If the exception detail is a dict (our custom format)
        if isinstance(exc.detail, dict):
            # Keep the detailed format
            response.data = exc.detail
        else:
            # Convert simple message to detailed format
            response.data = {
                'detail': str(exc.detail),
                'error': str(exc.detail),
            }

    return response
