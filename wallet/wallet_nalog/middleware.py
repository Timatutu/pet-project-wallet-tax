from django.utils.deprecation import MiddlewareMixin


class DisableCSRFForAPI(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        elif request.path == '/tonconnect-manifest.json' or request.path.endswith('/tonconnect-manifest.json'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None

