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
                    client_id=config('client_id',cast=str),
                    client_secret=config('client_secret',cast=str),
                    expiry=token.expires_at
                )
                # token.expires_at = ensure_aware(token.expires_at)
                expiry = token.expires_at  # or token_obj.expiry for destination
                print('creds k niche', creds.expiry)
                if expiry:
                    print('if creds k andar')
                    if is_naive(expiry):
                        print('if is_naive k andar')
                        expiry = make_aware(expiry, timezone.utc)
                        print('expiry hai', expiry)
                    else:
                        print('else k andar')
                        expiry = expiry.astimezone(timezone.utc)
                        print('idhar expiry', expiry)
                creds.expiry = expiry
                print('final creds', creds.expiry)
                logger.debug(f"Source token expiry: {token.expires_at}, type: {type(token.expires_at)}")

                # creds.expiry = token.expires_at
                print(creds.expiry, 'source token expite', type(creds.expiry))
                if creds.expiry and creds.expiry <= now() and creds.refresh_token:

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
