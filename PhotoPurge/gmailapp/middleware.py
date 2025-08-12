from allauth.socialaccount.models import SocialAccount, SocialToken
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.utils.timezone import is_naive, make_aware, now
import logging
from decouple import config
# from gmailapp.utils import ensure_aware
from datetime import timezone


logger = logging.getLogger(__name__)

class SourceTokenRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                account = SocialAccount.objects.get(user=request.user, provider='google')
                token = SocialToken.objects.get(account=account)

                creds = Credentials(
                    token=token.token,
                    refresh_token=token.token_secret,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=config('client_id', cast=str),
                    client_secret=config('client_secret', cast=str),
                )

                expires_at = token.expires_at 

                if expires_at:
                    if is_naive(expires_at):
                        expires_at = make_aware(expires_at, timezone.utc)
                    else:
                        expires_at = expires_at.astimezone(timezone.utc)

                creds.expiry = expires_at

                if creds.expiry and creds.expiry <= now() and creds.refresh_token:

                    creds.refresh(Request())
                    token.token = creds.token
                    token.expires_at = creds.expiry
                    token.save()

            except (SocialAccount.DoesNotExist, SocialToken.DoesNotExist):
                raise ValueError("Source token does not exist")
            except Exception as e:
                raise Exception(f"Exception in SourceTokenRefreshMiddleware(gmailapp): {e}")

        return self.get_response(request)
