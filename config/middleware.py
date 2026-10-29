class DevNoCacheMiddleware:
    """
    Prevents browsers from aggressively caching static assets and HTML during development,
    ensuring that full, updated styles load immediately without requiring hard refreshes (Ctrl+F5).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Disable caching for static files and pages in development
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
