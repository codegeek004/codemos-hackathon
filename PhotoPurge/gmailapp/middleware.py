from django.utils.timezone import now, make_aware
from datetime import datetime, timezone, timedelta
from allauth.socialaccount.models import SocialToken, SocialAccount
from google.auth.transport.requests import Request
from .utils import retrieve_credentials_for_user  # your custom function

class TokenRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                creds = retrieve_credentials_for_user(request.user.id)

                # Convert string/naive to aware datetime
                if isinstance(creds.expiry, str):
                    creds.expiry = datetime.fromisoformat(creds.expiry)
                if creds.expiry.tzinfo is None:
                    creds.expiry = make_aware(creds.expiry, timezone.utc)

                if creds.expiry - now() < timedelta(minutes=30):
                    creds.refresh(Request())

                    # Save refreshed token to SocialToken
                    social_account = SocialAccount.objects.get(user=request.user, provider='google')
                    social_token = SocialToken.objects.get(account=social_account)
                    social_token.token = creds.token
                    social_token.expires_at = creds.expiry
                    social_token.save()

            except Exception as e:
                print("Token refresh failed:", e)

        return self.get_response(request)

