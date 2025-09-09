from django.utils.deprecation import MiddlewareMixin
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.utils.timezone import make_aware, is_naive, now
from .models import DestinationToken
import logging
# from gmailapp.utils import ensure_aware
from datetime import timezone

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
            )
            expires_at = token_obj.expires_at  
            if expires_at:
                if is_naive(expires_at):
                    expires_at = make_aware(expires_at, timezone.utc)
                else:
                    expires_at = expires_at.astimezone(timezone.utc)
            creds.expiry = expires_at
           
            if creds.expiry and creds.expiry <= now() and creds.refresh_token:
                creds.refresh(Request())

                token_obj.token = creds.token
                token_obj.expires_at = creds.expiry
                token_obj.save()
                print(f'Destination token Refreshed successfully at {now()}')

        except DestinationToken.DoesNotExist:
            raise ValueError("Destination token does not exist")
        except Exception as e:
            raise Exception(f"Exception in RefreshDestinationTokenMiddleware(photos app) : {e}")
