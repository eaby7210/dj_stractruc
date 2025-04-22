from functools import wraps
from django.utils.timezone import now
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from .models import OAuthToken

def require_valid_oauth_token(*args, **kwargs):
    """
    Decorator factory to ensure the request has a valid OAuth token.
    
    If `redirect_url` is provided, it redirects with an error message.
    Otherwise, returns a JSON response.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            token_obj = OAuthToken.objects.first()

      
            if not token_obj or token_obj.is_expired():
                if kwargs['redirect_url']: 
                    messages.error(request, "Your session has expired. Please log in again.")
                    return redirect(kwargs['redirect_url'])
                else: 
                    return JsonResponse({"error": "Unauthorized: Invalid or expired OAuth token"}, status=401)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator