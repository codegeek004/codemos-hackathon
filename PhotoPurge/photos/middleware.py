from django.utils.deprecation import MiddlewareMixin
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.utils.timezone import make_aware, is_naive
from .models import DestinationToken
import logging
from gmailapp.utils import ensure_aware
from datetime import timezone

logger = logging.getLogger(__name__)


class RefreshDestinationTokenMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return  # no user, no token

        try:
            token_obj = DestinationToken.objects.get(user=request.user)

            # Rebuild credentials
            creds = Credentials(
                token=token_obj.token,
                refresh_token=token_obj.refresh_token,
                token_uri=token_obj.token_uri,
                client_id=token_obj.client_id,
                client_secret=token_obj.client_secret,
                # expiry=token_obj.expiry
            )

            # logger.debug(f"[PRE] token.expires_at: {token_obj.expiry}, tzinfo: {getattr(token_obj.expiry, 'tzinfo', None)}")


            # creds.expiry = ensure_aware(token_obj.expiry)
            creds.expiry = ensure_aware(token_obj.expiry).astimezone(timezone.utc)
            print('dest token exp', creds.expiry)
            logger.info(f"Token expiry after ensure_aware: {creds.expiry}, tzinfo: {creds.expiry.tzinfo}")

            if creds.expired and creds.refresh_token:
                logger.info(f"Refreshing token for user {request.user.email}")
                creds.refresh(Request())

                # Save refreshed token
                token_obj.token = creds.token
                token_obj.expiry = creds.expiry
                token_obj.save()
                logger.info("Token refreshed successfully.")
        except DestinationToken.DoesNotExist:
            logger.warning(f"No destination token found for user {request.user}")
        except Exception as e:
            logger.error(f"Error in token refresh middleware: {e}")
