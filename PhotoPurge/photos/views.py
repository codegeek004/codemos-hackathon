from django.contrib import messages
from django.shortcuts import render, redirect
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount, SocialToken
from google.oauth2.credentials import Credentials
from gmailapp.auth import check_token_validity
from django.contrib.auth import logout
import httplib2
import requests
import io
import json
from django.contrib.auth.models import User
from .tasks import migrate_all_photos_task, migrate_selected_photos_task
from .utils import get_photos_service, download_photo, upload_photo, get_photos
from decouple import config


def google_auth_redirect(request):
    return redirect('socialaccount_login', provider='google')


API_NAME = 'photoslibrary'
API_VERSION = 'v1'


def retrieve_credentials_for_user(user):
    try:

        social_account = SocialAccount.objects.get(
            user=user, provider="google")

        social_token = SocialToken.objects.get(account=social_account)
        SCOPES = ['https://www.googleapis.com/auth/photoslibrary',
                  'https://www.googleapis.com/auth/drive',]

        creds = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config('client_id', cast=str),
            client_secret=config('client_secret', cast=str),
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds.has_scopes(SCOPES):
            creds = Credentials(
                token=creds.token,
                refresh_token=creds.refresh_token,
                token_uri=creds.token_uri,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                scopes=SCOPES
            )
        return creds
    except SocialAccount.DoesNotExist:
        raise Exception("Google account not linked to this user.")
    except SocialToken.DoesNotExist:
        raise Exception("No Google token found for this user.")


def migrate_photos(request):
    request.session['next'] = 'migrate_photos'
    if not request.user.is_authenticated:
        messages.error(
            request, "You are not logged in. Please login to continue.")
        return redirect("index")

    creds = retrieve_credentials_for_user(request.user.id)
    if not check_token_validity(creds.token):
        request.session.flush()
        logout(request)
        messages.warning(
            request, 'Your session has expired. Please log in again to continue.')
        return redirect('index')

    try:
        source_credentials = retrieve_credentials_for_user(request.user)
    except Exception as e:
        messages.error(request, f"Error retrieving source credentials: {e}")
        return redirect('/accounts/google/login/?process=login')
    creds = retrieve_credentials_for_user(request.user.id)
    src_creds = {
        'token': creds.token, 'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri, 'client_id': creds.client_id,
        'client_secret': creds.client_secret, 'scopes': creds.scopes
    }

    page_token = request.GET.get('page_token')
    photos, next_page_token = get_photos(src_creds, page_token)

    destination_credentials = request.session.get('destination_credentials')

    if request.method == 'POST' and 'action' in request.POST:
        if not destination_credentials:
            messages.error(request, 'Destination address not selected')
            return redirect('migrate_photos')

        action = request.POST['action']

        if action == 'migrate_all':
            creds = retrieve_credentials_for_user(request.user)
            src_creds = {'token': creds.token, 'refresh_token': creds.refresh_token,
                         'client_id': creds.client_id, 'token_uri': creds.token_uri, 'client_secret': creds.client_secret}
            if destination_credentials:
                task = migrate_all_photos_task.delay(
                    request.user.id, request.user.email, src_creds, destination_credentials)

                messages.success(
                    request, f"Migrating all photos. Task ID: {task.id}")
                return redirect('migrate_photos')

        elif action == 'migrate_selected':
            selected_photo_ids = request.POST.getlist('selected_photos')
            if destination_credentials and selected_photo_ids:

                creds = retrieve_credentials_for_user(request.user.id)
                src_creds = {
                    'token': creds.token, 'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri, 'client_id': creds.client_id,
                    'client_secret': creds.client_secret, 'scopes': creds.scopes
                }

                task = migrate_selected_photos_task.delay(
                    src_creds, destination_credentials, selected_photo_ids)

                messages.success(
                    request, f"Migrating selected photos. Task ID: {task.id}")
                return redirect('migrate_photos')

    return render(request, 'migrate_photos.html', {
        'photos': photos,
        'next_page_token': next_page_token
    })
