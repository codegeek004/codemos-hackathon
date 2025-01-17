import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import json
from django.contrib.auth.models import User


def get_photos_service(credentials_dict):
    try:
        #if credentials is already an instance of the object it will use existing 
        #object or else it will create another
        if isinstance(credentials_dict, Credentials):
            credentials = credentials_dict  
        elif isinstance(credentials_dict, dict): 
            credentials = Credentials(
                token=credentials_dict.get('token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri'),
                client_id=credentials_dict.get('client_id'),
                client_secret=credentials_dict.get('client_secret'),
                scopes=credentials_dict.get('scopes')
            )
        else:
            raise ValueError("credentials_dict must be either a Credentials object or a dictionary")

        if not credentials or not credentials.valid:
            return None

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        return service
    except Exception as e:
        return None  


def get_photos(credentials, page_token=None):
    try:
        service = get_photos_service(credentials)
        results = service.mediaItems().list(pageSize=20, pageToken=page_token).execute()
        items = results.get('mediaItems', [])
        next_page_token = results.get('nextPageToken')
        return items, next_page_token
    except Exception as e:
        return None


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
        return e
