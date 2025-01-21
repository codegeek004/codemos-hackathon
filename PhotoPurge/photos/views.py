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



def google_auth_redirect(request):
    return redirect('socialaccount_login', provider='google')


API_NAME = 'photoslibrary'
API_VERSION = 'v1'


def retrieve_credentials_for_user(user):
    try:

        social_account = SocialAccount.objects.get(user=user, provider="google")
        
        social_token = SocialToken.objects.get(account=social_account)
        print('social token are ',social_token)
        SCOPES = ['https://www.googleapis.com/auth/photoslibrary']

        creds = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="your-client-id.apps.googleusercontent.com",
            client_secret="your-client-secret",
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
    print('inside migrate photos')
    if not request.user.is_authenticated:
        messages.error(request, "You are not logged in. Please login to continue.")
        return redirect("index")

    creds = retrieve_credentials_for_user(request.user.id)
    print('creds', creds)
    if not check_token_validity(creds.token):
        request.session.flush()
        logout(request)
        messages.warning(request, 'Your session has expired. Please log in again to continue.')
        return redirect('index')

    try:
        source_credentials = retrieve_credentials_for_user(request.user)
        print('src crds', source_credentials)
    except Exception as e:
        messages.error(request, f"Error retrieving source credentials: {e}")
        return redirect('/accounts/google/login/?process=login')
    creds = retrieve_credentials_for_user(request.user.id)
    src_creds = {
                        'token':creds.token, 'refresh_token':creds.refresh_token,
                        'token_uri':creds.token_uri, 'client_id':creds.client_id,
                        'client_secret':creds.client_secret, 'scopes':creds.scopes
                                        }
    
    page_token = request.GET.get('page_token')
    photos, next_page_token = get_photos(src_creds, page_token)

    destination_credentials = request.session.get('destination_credentials')
    print('dest creds', destination_credentials)

    

    if request.method == 'POST' and 'action' in request.POST:
        if not destination_credentials:
            messages.error(request, 'Destination address not selected')
            return redirect('migrate_photos')

        action = request.POST['action']
        print('inside post method', action)

        if action == 'migrate_all':
            print('inside migrate all')
            creds = retrieve_credentials_for_user(request.user)
            src_creds = {'token':creds.token, 'refresh_token':creds.refresh_token}
            if destination_credentials:
                task = migrate_all_photos_task.delay(request.user.id, request.user.email, src_creds, destination_credentials)
                messages.success(request, f"Migrating all photos. Task ID: {task.id}")
                return redirect('migrate_photos')

        elif action == 'migrate_selected':
            print('inside migrate selected')
            selected_photo_ids = request.POST.getlist('selected_photos')
            print(f'\nselectedphotoid\n {selected_photo_ids}\n')
            if destination_credentials and selected_photo_ids:
                print('inside if')
                print('source_credentials', source_credentials)
                print('destination_credentials', destination_credentials)

                creds = retrieve_credentials_for_user(request.user.id)
                src_creds = {
                        'token':creds.token, 'refresh_token':creds.refresh_token,
                        'token_uri':creds.token_uri, 'client_id':creds.client_id,
                        'client_secret':creds.client_secret, 'scopes':creds.scopes
                                        }
                

                print('src creds', src_creds)



                task = migrate_selected_photos_task.delay(request.user.id, request.user.email, src_creds, destination_credentials, selected_photo_ids)
                print('on botom of task')
                print(f"task{task}")
                messages.success(request, f"Migrating selected photos. Task ID: {task.id}")
                return redirect('migrate_photos')

    return render(request, 'migrate_photos.html', {
        'photos': photos,
        'next_page_token': next_page_token
    })

