from django.utils.deprecation import MiddlewareMixin
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.utils.timezone import make_aware, is_naive, now
from .models import DestinationToken
import logging
# from gmailapp.utils import ensure_aware
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
                expiry=token_obj.expiry
            )
            expiry = token_obj.expiry  # or token_obj.expiry for destination
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
            #
            # logger.debug(f"Destination token expiry: {token_obj.expiry}, type: {type(token_obj.expiry)}")

            # print('dest token exp', creds.expiry)
            # logger.info(f"Token expiry after ensure_aware: {creds.expiry}, tzinfo: {creds.expiry.tzinfo}")

            if creds.expiry and creds.expiry <= now() and creds.refresh_token:
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
