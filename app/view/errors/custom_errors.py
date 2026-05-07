import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import requires_csrf_token

logger = logging.getLogger(__name__)

def custom_400(request, exception=None):
    """Handle 400 Bad Request"""
    logger.warning(f"400 Bad Request: {request.path}")
    return render(request, 'errors/400.html', status=400)

def custom_403(request, exception=None):
    """Handle 403 Forbidden"""
    logger.warning(f"403 Forbidden: {request.path} - User: {request.user}")
    return render(request, 'errors/403.html', status=403)

def custom_404(request, exception=None):
    """Handle 404 Not Found"""
    logger.warning(f"404 Not Found: {request.path}")
    return render(request, 'errors/404.html', status=404)

def custom_500(request):
    """Handle 500 Server Error"""
    # logger.error(f"500 Server Error: {request.path}", exc_info=True)
    return render(request, 'errors/500.html', status=500)

@requires_csrf_token
def custom_403_csrf(request, reason=""):
    """Handle 403 CSRF Error"""
    logger.warning(f"403 CSRF Error: {request.path} - Reason: {reason}")
    return render(request, 'errors/403.html', {'reason': reason}, status=403)