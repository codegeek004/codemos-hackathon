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


def google_auth_redirect(request):
    return redirect('socialaccount_login', provider='google')



# Define constants
API_NAME = 'photoslibrary'
API_VERSION = 'v1'

# Utility function to retrieve Google credentials
def retrieve_credentials_for_user(user):
    try:
        # Get the social account for the user
        social_account = SocialAccount.objects.get(user=user, provider="google")
        
        # Get the associated social token
        social_token = SocialToken.objects.get(account=social_account)
        print('social token are ',social_token)
        SCOPES = ['https://www.googleapis.com/auth/photoslibrary']


        # Build the credentials
        creds = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="your-client-id.apps.googleusercontent.com",
            client_secret="your-client-secret",
        )

        # Check if credentials need to be refreshed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # Re-apply the required scope if necessary
        if not creds.has_scopes(SCOPES):
            creds = Credentials(
                token=creds.token,
                refresh_token=creds.refresh_token,
                token_uri=creds.token_uri,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                scopes=SCOPES  # Add the required scopes here
            )        
        return creds
    except SocialAccount.DoesNotExist:
        raise Exception("Google account not linked to this user.")
    except SocialToken.DoesNotExist:
        raise Exception("No Google token found for this user.")


from google.auth.transport.requests import Request

def get_photos_service(credentials):
    # Refresh the token if it's expired
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    # Build the service object using credentials directly
    service = build(API_NAME, API_VERSION, credentials=credentials, static_discovery=False)

    return service



def migrate_photos(request):

    # Get source credentials from social token (Google account)
    if not request.user.is_authenticated:
        messages.error(request, "You are not logged in. Please login to continue.")
        return redirect("index")
    creds = retrieve_credentials_for_user(request.user.id)
    if check_token_validity(creds.token) == False:
        request.session.flush()
        logout(request)
        messages.warning(request, 'Your session was expired. login again to continue')
        return redirect('index')
    try:
        source_credentials = retrieve_credentials_for_user(request.user)
    except Exception as e:
        messages.error(request, f"Error retrieving source credentials: {e}")
        return redirect('/accounts/google/login/?process=login')

    page_token = request.GET.get('page_token')
    photos, next_page_token = get_photos(source_credentials, page_token)

    # Get destination credentials from social token (Google account)
    try:
        destination_credentials = retrieve_credentials_for_user(request.user)
    except Exception as e:
        messages.error(request, f"Error retrieving destination credentials: {e}")
        return redirect('destination_google_auth')

    if request.method == 'POST' and 'action' in request.POST:
        action = request.POST['action']

        if action == 'migrate_all':
            if destination_credentials:
                destination_service = get_photos_service(destination_credentials)
                all_photos = []
                current_page_token = None

                while True:
                    photos, next_page_token = get_photos(source_credentials, current_page_token)
                    all_photos.extend(photos)

                    for photo in photos:
                        file_url = photo['baseUrl'] + "=d"
                        file_name = photo['filename']
                        photo_data = download_photo(file_url)
                        if photo_data:
                            upload_photo(destination_service, photo_data, file_name)

                    if not next_page_token:
                        break
                    current_page_token = next_page_token

                return render(request, 'migrate_photos.html', {
                    'photos': all_photos,
                    'success_all': True
                })  

        elif action == 'migrate_selected':
            selected_photo_ids = request.POST.getlist('selected_photos')
            if destination_credentials and selected_photo_ids:
                destination_service = get_photos_service(destination_credentials)
                selected_photos = [photo for photo in photos if photo['id'] in selected_photo_ids]
                for photo in selected_photos:
                    file_url = photo['baseUrl'] + "=d"
                    file_name = photo['filename']
                    photo_data = download_photo(file_url)
                    if photo_data:
                        upload_photo(destination_service, photo_data, file_name)
                return render(request, 'migrate_photos.html', {
                    'photos': photos,
                    'success_selected': True,
                    'next_page_token': next_page_token
                })

    return render(request, 'migrate_photos.html', {
        'photos': photos,
        'next_page_token': next_page_token
    })

def get_photos(credentials, page_token=None):
    service = get_photos_service(credentials)
    results = service.mediaItems().list(pageSize=20, pageToken=page_token).execute()
    items = results.get('mediaItems', [])
    next_page_token = results.get('nextPageToken')
    return items, next_page_token

def download_photo(url):
    if not User.is_authenticated:
        return redirect('oauth')
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading photo: {e}")
        return None

def upload_photo(service, photo_data, file_name):
    if not User.is_authenticated:
        return redirect('oauth')
    try:
        upload_url = "https://photoslibrary.googleapis.com/v1/uploads"
        headers = {
            "Authorization": f"Bearer {service._http.credentials.token}",
            "Content-Type": "application/octet-stream",
            "X-Goog-Upload-File-Name": file_name,
            "X-Goog-Upload-Protocol": "raw"
        }

        response = requests.post(upload_url, headers=headers, data=photo_data)
        if response.status_code != 200:
            print(f"Error uploading photos: {response.status_code}, {response.text}")
            return None
        response.raise_for_status()

        upload_token = response.text
        media_item = {
            'newMediaItems': [{
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }]
        }

        service.mediaItems().batchCreate(body=media_item).execute()

    except Exception as e:
        print(f"Error uploading photo: {e}")
