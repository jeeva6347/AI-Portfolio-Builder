import sys
import traceback


class ExceptionLoggingMiddleware:
    """
    Middleware that catches unhandled exceptions and outputs full tracebacks to stderr
    to ensure production runtime errors are logged cleanly in server logs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        sys.stderr.write(
            f"[UNHANDLED EXCEPTION 500] Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"Exception: {exception.__class__.__name__}: {exception}\n"
            f"Traceback:\n{traceback.format_exc()}\n"
        )
        return None
