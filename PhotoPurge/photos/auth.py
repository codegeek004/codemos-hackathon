import logging
from django.contrib.auth import login
from django.contrib.auth.models import User
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
import httplib2
from google_auth_oauthlib.flow import Flow
from django.contrib.auth import logout
from django.shortcuts import render, redirect
import requests
import json
from datetime import datetime, timezone, timedelta
from django.utils.timezone import make_aware, is_naive, now
from datetime import timezone
from .models import *
from django.contrib.auth import get_user_model

user = get_user_model()

# CLIENT_SECRETS_FILE = "credentials.json"
# for local testing
CLIENT_SECRETS_FILE = "credentials_local.json"


def get_google_auth_flow(redirect_uri):

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=[
            'https://www.googleapis.com/auth/photoslibrary.readonly',
            'https://www.googleapis.com/auth/photoslibrary.appendonly',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
            'openid'
        ],
        redirect_uri=redirect_uri
    )
    return flow

################# destination auth##########################


def destination_google_auth(request):

    # flow = get_google_auth_flow('https://codemos-services.co.in/photos/destination/auth/callback/')
    # for local testing
    flow = get_google_auth_flow(
        'https://127.0.0.1:8000/photos/destination/auth/callback/')
    authorization_url, state = flow.authorization_url(
        access_type='offline', prompt='consent')
    return redirect(authorization_url)


def destination_google_auth_callback(request):

    if 'code' not in request.GET:
        return redirect('dest-oauth')

    # flow = get_google_auth_flow('https://codemos-services.co.in/photos/destination/auth/callback/')
    # for local testing
    try:
        flow = get_google_auth_flow(
            'https://127.0.0.1:8000/photos/destination/auth/callback/')
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        credentials = flow.credentials
        expires_at = credentials.expiry
        if expires_at and is_naive(expires_at):
            expires_at = make_aware(expires_at, timezone.utc)

        dest_creds = credentials_to_dict(credentials)
    except Exception as e:
        print(f"exception in flow get_google_auth_flow {e}")

    try:
        request.session['destination_credentials'] = dest_creds
        request.session['is_destination_authenticated'] = True
    except Exception as e:
        print(f'exception in request.session, {e}')

    try:
        DestinationToken.objects.update_or_create(
            user=request.user,
            defaults={
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': ' '.join(credentials.scopes),
                'expires_at': expires_at
            }
        )
        # **Fetch and validate destination email**
        destination_email = request.session.get('destination_email', None)
    except Exception as e:
        print(f'inside exception of token insert query, {e}')

    try:
        userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"
        headers = {
            "Authorization": f"Bearer {credentials.token}"
        }
        response = requests.get(userinfo_url, headers=headers)

        if response.status_code == 200:
            userinfo = response.json()
        else:
            userinfo = None
    except Exception as e:
        print(f'exception raised in userinfo fetch {e}')

    try:
        user = request.user
        user.email = userinfo.get('email', user.email)
        user.first_name = userinfo.get('given_name', user.first_name)
        user.last_name = userinfo.get('family_name', user.last_name)
        user.save()
    except Exception as e:
        print(f'Error inserting userinfo into db exception {e}')
    return redirect('migrate_photos')


##################### logout#######################
def logout_view(request):
    source_credentials = request.session.get('source_credentials')
    destination_credentials = request.session.get('destination_credentials')

    if source_credentials:
        requests.post(
            'https://oauth2.googleapis.com/revoke',
            params={'token': source_credentials['token']},
            headers={'content-type': 'application/x-www-form-urlencoded'}
        )

    if destination_credentials:
        requests.post(
            'https://oauth2.googleapis.com/revoke',
            params={'token': destination_credentials['token']},
            headers={'content-type': 'application/x-www-form-urlencoded'}
        )

    request.session.flush()
    logout(request)
    return redirect('home')


#################### fetch user creds####################
def fetch_user_info(credentials):
    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        # response.raise_for_status()
        if response.status_code == 200 and response.headers.get('Content-Type') == 'application/json':
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user info: {e}")
        return None


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
