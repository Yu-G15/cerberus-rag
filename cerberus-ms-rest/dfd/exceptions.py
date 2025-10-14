"""
Custom exception handling for the DFD API to return JSON responses instead of HTML.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import ValidationError
from neomodel import DoesNotExist
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns JSON responses for all errors.
    """
    # Handle our custom APIException first
    if isinstance(exc, APIException):
        custom_response_data = {
            'error': True,
            'message': exc.message,
            'status_code': exc.status_code,
            'data': exc.data
        }
        return Response(custom_response_data, status=exc.status_code)
    
    # Get the standard error response
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the error response format
        custom_response_data = {
            'error': True,
            'message': response.data.get('detail', 'An error occurred'),
            'status_code': response.status_code,
            'data': response.data
        }
        response.data = custom_response_data
    
    # Handle Django's Http404 exceptions
    elif isinstance(exc, Http404):
        custom_response_data = {
            'error': True,
            'message': str(exc),
            'status_code': status.HTTP_404_NOT_FOUND,
            'data': None
        }
        response = Response(custom_response_data, status=status.HTTP_404_NOT_FOUND)
    
    # Handle ValidationError exceptions
    elif isinstance(exc, ValidationError):
        custom_response_data = {
            'error': True,
            'message': 'Validation error',
            'status_code': status.HTTP_400_BAD_REQUEST,
            'data': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
        }
        response = Response(custom_response_data, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle NeoModel DoesNotExist exceptions
    elif isinstance(exc, DoesNotExist):
        custom_response_data = {
            'error': True,
            'message': 'Resource not found',
            'status_code': status.HTTP_404_NOT_FOUND,
            'data': None
        }
        response = Response(custom_response_data, status=status.HTTP_404_NOT_FOUND)
    
    # Handle any other unhandled exceptions
    else:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        custom_response_data = {
            'error': True,
            'message': 'Internal server error',
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'data': str(exc) if hasattr(exc, '__str__') else 'Unknown error'
        }
        response = Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response


class APIException(Exception):
    """
    Custom API exception class for consistent error responses.
    """
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, data=None):
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(self.message)


def raise_api_error(message, status_code=status.HTTP_400_BAD_REQUEST, data=None):
    """
    Helper function to raise API exceptions with consistent format.
    """
    raise APIException(message, status_code, data)
