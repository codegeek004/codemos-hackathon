from datetime import datetime, timedelta
from django.utils import timezone
from allauth.socialaccount.models import SocialToken
from .auth import refresh_google_token  # Ensure this is implemented in auth.py

class TokenRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        print('TokenRefreshMiddleware initialized')

    def __call__(self, request):
        # Only proceed if the user is authenticated
        if request.user.is_authenticated:
            # Fetch the first SocialToken associated with the Google account
            social_token = SocialToken.objects.filter(account__user=request.user, account__provider='google').first()
            
            # Check if the token exists and is expired
            if social_token and social_token.expires_at:
                if social_token.expires_at <= timezone.now():
                    # Refresh the token
                    refresh_google_token(request.user)
        
        # Proceed with the rest of the middleware chain
        response = self.get_response(request)
        return response
