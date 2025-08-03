from google.oauth2.credentials import Credentials
from allauth.socialaccount.models import SocialAccount, SocialToken
from decouple import config

def retrieve_credentials_for_user(user_id):
    try:
        social_account = SocialAccount.objects.get(user_id=user_id, provider="google")
        social_token = SocialToken.objects.get(account=social_account)

        # No string formatting — pass the datetime object directly
        creds = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config('client_id',cast=str),
            client_secret=config('client_secret',cast=str),
            expiry=social_token.expires_at
        )

        return creds
    except SocialAccount.DoesNotExist:
        raise Exception("Google account not linked to this user.")
    except SocialToken.DoesNotExist:
        raise Exception("No Google token found for this user.")
