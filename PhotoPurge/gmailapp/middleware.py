from datetime import timedelta
from django.utils.timezone import now
from .auth import refresh_google_token, check_token_validity
from .utils import retrieve_credentials_for_user
from allauth.socialaccount.models import SocialToken
from google.auth.transport.requests import Request

class TokenRefreshMiddleware:
    """
    Middleware to refresh Google OAuth tokens before they expire.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        print('TokenRefreshMiddleware initiated')

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                print('call method called')
                # Fetch the user's token
                social_token = SocialToken.objects.get(account__user=request.user, account__provider='google')

                # Refresh the token if it's about to expire within the next 5 minutes
                if social_token.expires_at and (social_token.expires_at - now()) < timedelta(minutes=5):
                    creds = retrieve_credentials_for_user(request.user.id)
                    creds.refresh(Request())
                    print('token refreshed')

            except SocialToken.DoesNotExist:
                pass  # No token for the user, skip

        return self.get_response(request)

