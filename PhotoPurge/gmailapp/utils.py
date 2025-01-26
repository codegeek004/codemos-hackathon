from google.oauth2.credentials import Credentials
from allauth.socialaccount.models import SocialAccount, SocialToken
from datetime import datetime
def retrieve_credentials_for_user(user_id):
    try:
        # Get the social account for the user
        social_account = SocialAccount.objects.get(user_id=user_id, provider="google")
        
        # Get the associated social token
        social_token = SocialToken.objects.get(account=social_account)
        time = social_token.expires_at
        actual_time = time.strftime('%Y-%m-%d %H:%M:%S.%f')
        # Build the credentials
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="99034799467-hl9dbl4t4l64gftesd8bokb1no6kbgu3.apps.googleusercontent.com",
            client_secret="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",
            expiry=actual_time
        )

        return creds
    except SocialAccount.DoesNotExist:
        raise Exception("Google account not linked to this user.")
    except SocialToken.DoesNotExist:
        raise Exception("No Google token found for this user.")
