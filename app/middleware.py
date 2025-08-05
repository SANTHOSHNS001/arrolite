from django.http import HttpResponseRedirect
from django.urls import reverse
import re

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = reverse("login")

    def __call__(self, request):
        # Skip middleware if AuthenticationMiddleware not loaded
        if not hasattr(request, "user"):
            return self.get_response(request)

        # Allow access if user is authenticated
        if request.user.is_authenticated:
            return self.get_response(request)

        # Allow access only to login page
        if request.path == self.login_url:
            return self.get_response(request)

        # Redirect all other unauthenticated users to login
        return HttpResponseRedirect(self.login_url)