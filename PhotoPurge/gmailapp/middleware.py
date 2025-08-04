from allauth.socialaccount.models import SocialAccount, SocialToken
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.utils.timezone import is_naive, make_aware
import logging
from decouple import config
from gmailapp.utils import ensure_aware
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
                    client_id=config('client_id',cast=str),
                    client_secret=config('client_secret',cast=str),
                    

                )
                creds.expiry = ensure_aware(token.expires_at)
                print(creds.expiry, 'source token expite', type(creds.expiry))
                if creds.expiry and creds.refresh_token:
                    creds.refresh(Request())
                    token.token = creds.token
                    token.expires_at = creds.expiry
                    token.save()
                    logger.info(f"Refreshed source token for {request.user.email}")

            except (SocialAccount.DoesNotExist, SocialToken.DoesNotExist):
                logger.debug(f"No source token found for {request.user}")
            except Exception as e:
                logger.warning(f"Error refreshing source token: {e}")

        return self.get_response(request)
