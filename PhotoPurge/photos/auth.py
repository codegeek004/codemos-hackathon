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
from django.utils.timezone import make_aware
from .models import *
from django.utils.timezone import now


#CLIENT_SECRETS_FILE = "credentials.json"
#for local testing
CLIENT_SECRETS_FILE = "credentials_local.json"


def get_google_auth_flow(redirect_uri):
    print('get google auth flow mai gaya')
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

#################destination auth##########################

def destination_google_auth(request):
    print('destination google auth mai gaya')

    #flow = get_google_auth_flow('https://codemos-services.co.in/photos/destination/auth/callback/')
    # for local testing
    flow = get_google_auth_flow('https://127.0.0.1:8000/photos/destination/auth/callback/')
    authorization_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    return redirect(authorization_url)


def destination_google_auth_callback(request):
    print('inside destination google auth callback')
    if 'code' not in request.GET:
        return redirect('dest-oauth')

    #flow = get_google_auth_flow('https://codemos-services.co.in/photos/destination/auth/callback/')
    # for local testing
    try:
        print('inside try of get flow')
        flow = get_google_auth_flow('https://127.0.0.1:8000/photos/destination/auth/callback/')
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        credentials = flow.credentials
        

        print('creds in destination auth callback', credentials)
        
        dest_creds = credentials_to_dict(credentials)
        print('flow try ends')
    except Exception as e:
        print(f"exception in flow get_google_auth_flow {e}")
    
    print('\n\ndest creds', dest_creds)
    try:
        print('inside try of request.session')
        request.session['destination_credentials'] = dest_creds
        request.session['is_destination_authenticated'] = True
        print(f'\n{request.session}\n')
        print('try ends of request.session')
    except Exception as e:
        print(f'exception in request.session, {e}')
    print('on top of destination token query')
    
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
                'expiry': credentials.expiry if credentials.expiry else None,
            }
        )
        print('destination email k upar')
        # **Fetch and validate destination email**
        destination_email = request.session.get('destination_email', None)
    except Exception as e:
        print(f'inside exception of token insert query, {e}')

    try:
        print('userinfo k upar destination email k niche')
        # **Fetch user info to confirm token validity**
        userinfo = fetch_user_info(credentials)
        print('userinfo k niche if condition k upar')
        if userinfo:
            print('if userinfo k andar')
            email = userinfo.get('email')
            print('email', email)
        else:
            print('userinfo is none')
        print('userinfo', userinfo)
        print('redirect migrate photos k upar')
    except Exception as e:
        print(f'exception raised in userinfo fetch {e}')
    return redirect('migrate_photos')


#####################logout#######################
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



####################fetch user creds####################
def fetch_user_info(credentials):
    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        #response.raise_for_status()
        if response.status_code==200 and response.headers.get('Content-Type') == 'application/json':
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user info: {e}")
        return None


def credentials_to_dict(credentials):
    print('credentials to dict mai gaya')
    print('creds to dict function mai gaya')
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

