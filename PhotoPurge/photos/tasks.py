from celery import shared_task
from .utils import get_photos_service, upload_photo, get_photos
from .models import MigrationStatus
from django.core.mail import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import logging
import time
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def refresh_credentials_if_needed(credentials_dict):
    """
    Refresh credentials if expired or about to expire.
    credentials_dict should contain: token, refresh_token, token_uri, client_id, client_secret
    """
    try:
        creds = Credentials(
            token=credentials_dict.get('token'),
            refresh_token=credentials_dict.get('refresh_token'),
            token_uri=credentials_dict.get(
                'token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=credentials_dict.get('client_id'),
            client_secret=credentials_dict.get('client_secret')
        )

        # Force check expiry - if not set or expired, refresh
        # Google tokens expire in 1 hour, so we refresh proactively
        if creds.expired and creds.refresh_token:
            logger.info("Token expired, refreshing...")
            creds.refresh(Request())
            credentials_dict['token'] = creds.token
            credentials_dict['token_refreshed_at'] = datetime.utcnow()
            logger.info("Token refreshed successfully")
        elif not creds.expiry:
            # No expiry info, refresh to be safe
            logger.info("No expiry info, refreshing token...")
            creds.refresh(Request())
            credentials_dict['token'] = creds.token
            credentials_dict['token_refreshed_at'] = datetime.utcnow()
            logger.info("Token refreshed successfully")

        return credentials_dict
    except Exception as e:
        logger.error(f"Failed to refresh credentials: {e}")
        raise


def refresh_if_older_than(credentials_dict, minutes=50):
    """
    Refresh token if it's older than specified minutes (default 50 min to be safe before 60 min expiry)
    """
    last_refresh = credentials_dict.get('token_refreshed_at')

    if not last_refresh:
        # First time or no tracking, refresh now
        logger.info("No refresh timestamp found, refreshing token...")
        return refresh_credentials_if_needed(credentials_dict)

    age = datetime.utcnow() - last_refresh
    if age > timedelta(minutes=minutes):
        logger.info(
            f"Token is {age.total_seconds()/60:.1f} minutes old, refreshing...")
        return refresh_credentials_if_needed(credentials_dict)

    return credentials_dict


def download_photo_authenticated(file_url, access_token):
    """
    Download photo using authenticated request with access token
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(file_url, headers=headers, timeout=30)
        response.raise_for_status()

        return response.content
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(f"403 Forbidden - Token may be expired or invalid")
        logger.error(f"Error downloading photo: {e}")
        raise


@shared_task(bind=True, default_retry_delay=60, max_retries=3)
def migrate_all_photos_task(self, user_id, email_id, source_credentials, destination_credentials):
    try:
        # Initialize task status
        task_status, created = MigrationStatus.objects.get_or_create(
            task_id=self.request.id,
            user_id=user_id,
        )

        task_status.status = "IN_PROGRESS"
        task_status.save()

        # Refresh credentials before starting and mark the time
        logger.info("Initial credential refresh...")
        source_credentials = refresh_credentials_if_needed(source_credentials)
        source_credentials['token_refreshed_at'] = datetime.utcnow()

        destination_credentials = refresh_credentials_if_needed(
            destination_credentials)
        destination_credentials['token_refreshed_at'] = datetime.utcnow()

        # Initialize migration process
        destination_service = get_photos_service(destination_credentials)
        current_page_token = None
        all_photos = []
        migrated_count = 0
        batch_counter = 0

        # Paginate through source photos
        while True:
            try:
                # Refresh source credentials if older than 50 minutes
                source_credentials = refresh_if_older_than(
                    source_credentials, minutes=50)

                photos, next_page_token = get_photos(
                    source_credentials, current_page_token)
                batch_counter += 1
            except Exception as e:
                logger.error(f"Failed to fetch photos: {e}")
                task_status.status = "FAILED"
                task_status.result = f"Error fetching photos: {e}"
                task_status.save()
                raise self.retry(exc=e)

            all_photos.extend(photos)

            for photo in photos:
                # Use baseUrl with =d for download, but authenticate the request
                file_url = photo['baseUrl'] + "=d"
                file_name = photo['filename']

                try:
                    # Refresh credentials if they're getting old (every 50 minutes)
                    source_credentials = refresh_if_older_than(
                        source_credentials, minutes=50)
                    destination_credentials = refresh_if_older_than(
                        destination_credentials, minutes=50)

                    # Recreate destination service if we refreshed
                    if destination_credentials.get('token_just_refreshed'):
                        destination_service = get_photos_service(
                            destination_credentials)
                        destination_credentials.pop(
                            'token_just_refreshed', None)

                    # Download with CURRENT valid token
                    photo_data = download_photo_authenticated(
                        file_url, source_credentials['token'])

                    if photo_data:
                        upload_photo(destination_service,
                                     photo_data, file_name)
                        task_status.migrated_count += 1
                        task_status.save()
                        migrated_count += 1
                        time.sleep(10)

                except Exception as e:
                    logger.error(f"Failed to migrate photo {file_name}: {e}")
                    # Log and continue migrating other photos
                    continue

            if not next_page_token:
                break
            current_page_token = next_page_token

        # Finalize task status
        result_message = f"Migrated {migrated_count} photos out of {len(all_photos)}"
        task_status.status = "SUCCESS"
        task_status.result = result_message
        task_status.save()

        # Send notification email
        try:
            message = f"{migrated_count} photos have been successfully migrated. Thank you for using our service!"
            email = EmailMessage('Photo Migration Complete',
                                 message, to=[email_id])
            email.send()
        except Exception as e:
            logger.error(f"Failed to send email to {email_id}: {e}")

        return result_message

    except Exception as e:
        logger.error(f"Task failed: {e}")
        task_status.status = "FAILED"
        task_status.result = f"Error: {e}"
        task_status.save()
        raise self.retry(exc=e)


@shared_task(bind=True)
def migrate_selected_photos_task(self, user_id, source_email, source_credentials, destination_credentials, selected_photo_ids):
    try:
        task_status, created = MigrationStatus.objects.get_or_create(
            task_id=self.request.id,
            user_id=user_id,
        )

        task_status.status = "IN_PROGRESS"
        task_status.save()

        # Refresh credentials before starting
        logger.info("Initial credential refresh...")
        source_credentials = refresh_credentials_if_needed(source_credentials)
        source_credentials['token_refreshed_at'] = datetime.utcnow()

        destination_credentials = refresh_credentials_if_needed(
            destination_credentials)
        destination_credentials['token_refreshed_at'] = datetime.utcnow()

        destination_service = get_photos_service(destination_credentials)
        photos, _ = get_photos(source_credentials)

        selected_photos = [
            photo for photo in photos if photo['id'] in selected_photo_ids]

        migrated_count = 0
        for photo in selected_photos:
            try:
                # Refresh if needed before each photo
                source_credentials = refresh_if_older_than(
                    source_credentials, minutes=50)
                destination_credentials = refresh_if_older_than(
                    destination_credentials, minutes=50)

                file_url = photo['baseUrl'] + "=d"
                file_name = photo['filename']

                # Download with CURRENT valid token
                photo_data = download_photo_authenticated(
                    file_url, source_credentials['token'])

                if photo_data:
                    upload_photo(destination_service, photo_data, file_name)
                    migrated_count += 1
            except Exception as e:
                logger.error(f"Failed to migrate photo {file_name}: {e}")
                continue

        result_message = f"Migrated {migrated_count} photos"

        task_status.status = "SUCCESS"
        task_status.result = result_message
        task_status.migrated_count = migrated_count
        task_status.save()

        message = f"Migrated {migrated_count} from your account. Thanks for choosing CODEMOS"
        email = EmailMessage('Migrated photos', message, to=[source_email])
        email.send()

        return result_message

    except Exception as e:
        logger.error(f"Selected photos migration failed: {e}")
        task_status.status = "FAILED"
        task_status.result = f"Error: {e}"
        task_status.save()
        raise
