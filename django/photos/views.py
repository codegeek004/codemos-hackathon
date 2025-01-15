import io
from django.shortcuts import render, redirect
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import requests
import json
from .auth import *
# from .utils import *
from django.contrib.auth.decorators import login_required
from django.contrib import messages
# Define constants
API_NAME = 'photoslibrary'
API_VERSION = 'v1'

def home(request):
    return render(request, 'home.html')

def get_photos_service(credentials_dict):

    credentials = Credentials(
        token=credentials_dict['token'],
        refresh_token=credentials_dict.get('refresh_token'),
        token_uri=credentials_dict['token_uri'],
        client_id=credentials_dict['client_id'],
        client_secret=credentials_dict['client_secret'],
        scopes=credentials_dict['scopes']
    )

    print('credentials', credentials)

    http = httplib2.Http()
    print(http, 'http')
    authorized_http = AuthorizedHttp(credentials, http=http)
    print('authorized_http', authorized_http)
    return build(API_NAME, API_VERSION, http=authorized_http, static_discovery=False)

# @login_required
def migrate_photos(request):
    print('inside migrate photos')
    print(f"\n\nsession email {request.session.get('destination_credentials')}\n\n")
    print(f"session data {request.session.items()}\n\n")

    # Check if source credentials are present
    if 'source_credentials' not in request.session:
        return redirect('google_auth')  # Redirect to source authentication if missing

    source_credentials = request.session['source_credentials']
    print('src creds', source_credentials)
    page_token = request.GET.get('page_token')
    photos, next_page_token = get_photos(source_credentials, page_token)

    # Check if destination credentials are valid
    destination_credentials = request.session.get('destination_credentials')
    if not destination_credentials:
        print("Destination credentials missing. Redirecting to destination auth.")
        return redirect('destination_google_auth')  # Redirect to destination authentication page

    # If destination credentials exist but are invalid
    #checks if the desitanation_credentials are of string type
    if isinstance(destination_credentials, str):
        try:
            destination_credentials = json.loads(destination_credentials)
            print('inside isinstance below the destination_credentials')
        except json.JSONDecodeError as e:
            print('eeeeeeeeeeee', e)
            print("Invalid destination credentials format. Redirecting to destination auth.")
            return redirect('destination_google_auth')

    # Proceed with the migration logic if credentials are valid
    if request.method == 'POST' and 'action' in request.POST:
        print('post method mai gaya')
        action = request.POST['action']
        print('action', action)

        if action == 'migrate_all':
            print('in migrate all ')
            if destination_credentials:
                print('dest creds mil gaye')
                destination_service = get_photos_service(destination_credentials)
                all_photos = []
                current_page_token = None

                while True:
                    print(f"Fetching photos with page_token: {current_page_token}")
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


def get_photos(credentials_dict, page_token=None):
    service = get_photos_service(credentials_dict)
    results = service.mediaItems().list(pageSize=20, pageToken=page_token).execute()
    items = results.get('mediaItems', [])
    next_page_token = results.get('nextPageToken')
    return items, next_page_token

def download_photo(url):
    print('inside download photo')
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
    print('inside upload photo')
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
        print('token', upload_token)

        media_item = {
            'newMediaItems': [{
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }]
        }
        print('media item', media_item)

        service.mediaItems().batchCreate(body=media_item).execute()

    except Exception as e:
        print(f"Error uploading photo: {e}")

