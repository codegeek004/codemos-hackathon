from datetime import datetime, timedelta
from django.utils import timezone
from allauth.socialaccount.models import SocialToken

class TokenRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            social_token = SocialToken.objects.filter(account__user=request.user, account__provider='google').first()
            if social_token and social_token.expires_at:
                # Refresh the token
                if social_token.expires_at <= timezone.now():
                    refresh_google_access_token(request.user)
        response = self.get_response(request)
        return response
