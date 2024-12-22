from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials
from allauth.socialaccount.models import SocialAccount, SocialToken
from .utils import delete_emails

@login_required
def show(request):
    return HttpResponse('oauth2 is completed')

@login_required
def delete_emails_view(request):
    """
    View to delete emails from the authenticated user's Gmail account.
    """
    try:
        print('i am in try')
        print('user', request.user)

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
                    # Use the token to delete emails (your logic here)

        # If no tokens are found for any linked Google account
        return HttpResponse("No valid Google token found for the user.", status=400) 

        
        # Extract credentials
        creds = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri='https://oauth2.googleapis.com/token',
            client_id='99034799467-m8dh7cdtpfquud1jvt21eup1t5vuk7fv.apps.googleusercontent.com',  # Replace with actual client ID
            client_secret='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'  # Replace with actual client secret
        )

        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # Connect to Gmail API
        service = build('gmail', 'v1', credentials=creds)

        # Call delete_emails and get the result (success message or error)
        result = delete_emails(service)  # Ensure this returns a message, not a string
        
        if not result:
            return HttpResponse("No emails found to delete.", status=404)
        
        # Return the result from delete_emails as an HttpResponse
        return HttpResponse(result)  # Ensure the response is wrapped in HttpResponse

    except SocialAccount.DoesNotExist:
        return HttpResponse("Google account not linked.", status=400)
    except Exception as e:
        return HttpResponse(f"An error occurred: {e}", status=500)




from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

@login_required
def fetch_google_token(request):
    """
    Fetch and display the Google OAuth token for the authenticated user.
    """
    try:
        # Fetch the social account for the user
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        
        # Fetch the token associated with the social account
        social_token = SocialToken.objects.get(account=social_account)
        
        # Print and return the tokens
        access_token = social_token.token  # Google access token
        refresh_token = social_token.token_secret  # Refresh token (if available)
        
        response = (
            f"Access Token: {access_token}<br>"
            f"Refresh Token: {refresh_token if refresh_token else 'No refresh token available.'}"
        )
        return HttpResponse(response)
    
    except SocialAccount.DoesNotExist:
        return HttpResponse("No Google account linked.", status=400)
    except SocialToken.DoesNotExist:
        return HttpResponse("No token found for the linked Google account.", status=400)
