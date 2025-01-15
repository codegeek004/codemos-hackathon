from allauth.socialaccount.models import SocialToken, SocialAccount
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.contrib import messages
import requests
from gmailapp.auth import blacklist_token, check_token_validity
from gmailapp.utils import retrieve_credentials_for_user

def authenticate_source(request):
    if request.user.is_authenticated:
        token = SocialToken.objects.filter(account__user=request.user, account__provider='google')
        # token = SocialToken.objects.get(user=request.user)
        creds = retrieve_credentials_for_user(request.user)
        print(creds.token)
        print('source token', creds.token)
        if token and check_token_validity(creds.token):
            messages.success(request, 'Source account authentication successful')
        else:
            messages.error(request, "Source account auth failed")
    else:
        print('login first')
    return redirect('photos_index')

def authenticate_destination(request):
    if request.user.is_authenticated:
        token = SocialToken.objects.filter(account__user=request.user, account__provider='google').last() 
        print('dest_token', token.token)
        if token and check_token_validity(token.token):
            messages.success(request, 'Destination account authentication successful')
        else:
            messages.error(request, "Destination account auth failed")
    print('login first')
    return redirect('photos_index')

def store_token_in_session(request, token, account_type):
    key = f"{account_type}_token"
    request.session[key] = token.token

def get_token_from_session(request, account_type):
    key = f"{account_type}_token"
    return request.session.get(key, None)

def logout_view(request):
    try:
        source_token = get_token_from_session(request, 'source')
        if source_token:
            blacklist_token(source_token)

        destination_token = get_token_from_session(request, 'destination')
        if destination_token:
            blacklist_token(destination_token)

        request.session.flush()
        logout(request)
        messages.success(request, "successfully logged out from source and destination")

    except Exception as e:
        print(f"error{e}")
        messages.error(request, "An error occurred.")

    return redirect('photos_index')
