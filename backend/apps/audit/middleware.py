import threading

# Thread-local storage for request context
_thread_locals = threading.local()


def get_current_request():
    """Get the current request from thread-local storage."""
    return getattr(_thread_locals, 'request', None)


def get_client_ip(request):
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request."""
    return request.META.get('HTTP_USER_AGENT', '')


class AuditMiddleware:
    """
    Middleware to capture request context for audit logging.
    Stores the request in thread-local storage so it can be accessed
    by signal handlers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the request in thread-local storage
        _thread_locals.request = request

        response = self.get_response(request)

        # Clean up thread-local storage
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request

        return response
