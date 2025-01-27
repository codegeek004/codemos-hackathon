from django.utils.timezone import now, make_aware
from datetime import datetime, timezone, timedelta
from .utils import retrieve_credentials_for_user
from django.core.mail import EmailMessage
class TokenRefreshMiddleware:
    """
    Middleware to ensure Google OAuth token is refreshed if it's about to expire.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Retrieve credentials for the current user
                creds = retrieve_credentials_for_user(request.user.id)

                # Convert creds.expiry from string to datetime if necessary
                if isinstance(creds.expiry, str):
                    creds.expiry = datetime.fromisoformat(creds.expiry)

                # Convert creds.expiry to timezone-aware if it's naive
                if creds.expiry.tzinfo is None:
                    creds.expiry = make_aware(creds.expiry, timezone.utc)

                # Refresh the token if it will expire within 30 minutes
                if creds.expiry - now() < timedelta(minutes=30):
                    creds.refresh(Request())
                    email = EmailMessage("token refreshed", f"token refreshed for {request.user.email}", to = ["codegeek004@gmail.com"])
                    email.send()

                    # Update the token in the database
                    social_account = SocialAccount.objects.get(user=request.user, provider='google')
                    social_token = SocialToken.objects.get(account=social_account)
                    social_token.token = creds.token
                    social_token.expires_at = creds.expiry  # Already timezone-aware
                    social_token.save()

            except Exception as e:
                # Log or handle token refresh errors
                print(f"Error refreshing token: {e}")

        response = self.get_response(request)
        return response
