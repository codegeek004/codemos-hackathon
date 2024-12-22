from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .utils import delete_emails

@login_required
def delete_emails_view(request):
    """
    View to delete emails from the authenticated user's Gmail account.
    """
    try:
        print('i am in try')
        print('user', request.user)

        # Retrieve the linked Google account
        social_accounts = SocialAccount.objects.filter(user=request.user, provider='google')
        if not social_accounts.exists():
            return HttpResponse("No Google account linked for the user.", status=400)

        for social_account in social_accounts: 
            social_tokens = social_account.socialtoken_set.all()
            print('social_token', social_tokens)
            if social_tokens.exists():
                for social_token in social_tokens:
                    print(f"Access Token: {social_token.token}")
                    print(f"Refresh Token: {social_token.token_secret}")
                    
                    # Create credentials using the token
                    creds = Credentials(
                        token=social_token.token,
                        refresh_token=social_token.token_secret,
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id='99034799467-m8dh7cdtpfquud1jvt21eup1t5vuk7fv.apps.googleusercontent.com',  # Replace with actual client ID
                        client_secret='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'  # Replace with actual client secret
                    )

                    # Refresh the token if expired
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())

                    # Build the Gmail service
                    service = build('gmail', 'v1', credentials=creds)

                    # Call the function to delete emails
                    result = delete_emails(service)

                    if not result:
                        return HttpResponse("No emails found to delete.", status=404)

                    return HttpResponse(result)  # Return result after deletion

        return HttpResponse("No valid Google token found for the user.", status=400) 

    except SocialAccount.DoesNotExist:
        return HttpResponse("Google account not linked.", status=400)
    except Exception as e:
        return HttpResponse(f"An error occurred: {e}", status=500)
