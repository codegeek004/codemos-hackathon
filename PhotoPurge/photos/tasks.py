import time
from celery import shared_task
from .utils import get_photos_service, download_photo, upload_photo, get_photos
from .models import MigrationStatus, PhotoMigrationProgress
from django.core.mail import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import logging
import requests

logger = logging.getLogger(__name__)

PHOTOS_API_BASE = "https://photoslibrary.googleapis.com/v1"


def refresh_credentials_if_needed(credentials_dict):
    """
    Refresh credentials if expired.
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

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update the dict with new token
            credentials_dict['token'] = creds.token

        return credentials_dict
    except Exception as e:
        logger.error(f"Failed to refresh credentials: {e}")
        raise


@shared_task(bind=True, default_retry_delay=60, max_retries=3)
def migrate_photo_batch(self, user_id, task_id, batch_photos, source_credentials, destination_credentials):
    """
    Internal task to migrate a batch of photos.
    This keeps each task short-lived to avoid token expiration.
    """
    try:
        # Refresh credentials at the start of each batch
        destination_credentials = refresh_credentials_if_needed(
            destination_credentials)
        destination_service = get_photos_service(destination_credentials)

        migrated_in_batch = 0

        for photo in batch_photos:
            try:
                file_url = photo['baseUrl'] + "=d"
                file_name = photo['filename']
                photo_id = photo['id']

                # Check if already migrated
                if PhotoMigrationProgress.objects.filter(
                    task_id=task_id,
                    photo_id=photo_id,
                    status='SUCCESS'
                ).exists():
                    logger.info(f"Skipping already migrated photo: {photo_id}")
                    continue

                # Download and upload
                photo_data = download_photo(file_url)
                if photo_data:
                    upload_photo(destination_service, photo_data, file_name)

                    # Track progress
                    PhotoMigrationProgress.objects.update_or_create(
                        task_id=task_id,
                        photo_id=photo_id,
                        defaults={
                            'status': 'SUCCESS',
                            'filename': file_name
                        }
                    )

                    # Update main task status
                    task_status = MigrationStatus.objects.get(task_id=task_id)
                    task_status.migrated_count += 1
                    task_status.save()

                    migrated_in_batch += 1
                    time.sleep(10)

            except Exception as e:
                logger.error(
                    f"Failed to migrate photo {photo.get('filename', 'unknown')}: {e}")

                # Track failure
                PhotoMigrationProgress.objects.update_or_create(
                    task_id=task_id,
                    photo_id=photo['id'],
                    defaults={
                        'status': 'FAILED',
                        'filename': photo.get('filename', 'unknown'),
                        'error_message': str(e)
                    }
                )
                continue

        return {'migrated': migrated_in_batch}

    except Exception as e:
        logger.error(f"Batch migration failed: {e}")
        raise self.retry(exc=e)


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

        # Initialize migration process
        current_page_token = None
        all_photos = []

        # PHASE 1: Discover all photos
        logger.info("Discovering all photos...")
        while True:
            try:
                # Refresh credentials before each API call
                source_credentials = refresh_credentials_if_needed(
                    source_credentials)
                photos, next_page_token = get_photos(
                    source_credentials, current_page_token)
            except Exception as e:
                logger.error(f"Failed to fetch photos: {e}")
                task_status.status = "FAILED"
                task_status.result = f"Error fetching photos: {e}"
                task_status.save()
                raise self.retry(exc=e)

            all_photos.extend(photos)
            logger.info(f"Discovered {len(all_photos)} photos so far...")

            if not next_page_token:
                break
            current_page_token = next_page_token

        # Update total count
        task_status.total_count = len(all_photos)
        task_status.save()

        logger.info(f"Total photos to migrate: {len(all_photos)}")

        # PHASE 2: Split into batches and process
        batch_size = 50
        total_batches = (len(all_photos) + batch_size - 1) // batch_size

        for batch_index in range(0, len(all_photos), batch_size):
            batch_photos = all_photos[batch_index:batch_index + batch_size]
            batch_num = (batch_index // batch_size) + 1

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch_photos)} photos)")

            # Process batch synchronously but with fresh credentials
            try:
                # Refresh credentials before each batch
                destination_credentials = refresh_credentials_if_needed(
                    destination_credentials)
                destination_service = get_photos_service(
                    destination_credentials)

                for photo in batch_photos:
                    file_url = photo['baseUrl'] + "=d"
                    file_name = photo['filename']
                    photo_id = photo['id']

                    try:
                        # Check if already migrated
                        if PhotoMigrationProgress.objects.filter(
                            task_id=self.request.id,
                            photo_id=photo_id,
                            status='SUCCESS'
                        ).exists():
                            continue

                        photo_data = download_photo(file_url)
                        if photo_data:
                            upload_photo(destination_service,
                                         photo_data, file_name)

                            # Track progress
                            PhotoMigrationProgress.objects.update_or_create(
                                task_id=self.request.id,
                                photo_id=photo_id,
                                defaults={
                                    'status': 'SUCCESS',
                                    'filename': file_name
                                }
                            )

                            task_status.migrated_count += 1
                            task_status.save()
                            time.sleep(10)
                    except Exception as e:
                        logger.error(
                            f"Failed to migrate photo {file_name}: {e}")

                        PhotoMigrationProgress.objects.update_or_create(
                            task_id=self.request.id,
                            photo_id=photo_id,
                            defaults={
                                'status': 'FAILED',
                                'filename': file_name,
                                'error_message': str(e)
                            }
                        )
                        continue

            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                # Continue with next batch instead of failing completely
                continue

        # Finalize task status
        migrated_count = task_status.migrated_count
        failed_count = PhotoMigrationProgress.objects.filter(
            task_id=self.request.id,
            status='FAILED'
        ).count()

        result_message = f"Migrated {migrated_count} photos out of {len(all_photos)}. Failed: {failed_count}"
        task_status.status = "SUCCESS"
        task_status.result = result_message
        task_status.save()

        # Send notification email
        try:
            message = f"{migrated_count} photos have been successfully migrated. {failed_count} photos failed. Thank you for using our service!"
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

        # Refresh credentials before use
        source_credentials = refresh_credentials_if_needed(source_credentials)
        destination_credentials = refresh_credentials_if_needed(
            destination_credentials)

        destination_service = get_photos_service(destination_credentials)
        photos, _ = get_photos(source_credentials)

        selected_photos = [
            photo for photo in photos if photo['id'] in selected_photo_ids
        ]

        migrated_count = 0

        for photo in selected_photos:
            try:
                file_url = photo['baseUrl'] + "=d"
                file_name = photo['filename']
                photo_data = download_photo(file_url)
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
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def delete_all_google_photos(self, access_token: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    next_page_token = None
    deleted_count = 0

    while True:
        # 1. List media items (paginated)
        params = {"pageSize": 100}
        if next_page_token:
            params["pageToken"] = next_page_token

        list_resp = requests.get(
            f"{PHOTOS_API_BASE}/mediaItems",
            headers=headers,
            params=params,
            timeout=15,
        )

        list_resp.raise_for_status()
        data = list_resp.json()

        media_items = data.get("mediaItems", [])
        if not media_items:
            break

        # 2. Delete each media item
        for item in media_items:
            media_item_id = item["id"]

            delete_resp = requests.delete(
                f"{PHOTOS_API_BASE}/mediaItems/{media_item_id}",
                headers=headers,
                timeout=10,
            )

            # 200 or 204 = success
            if delete_resp.status_code not in (200, 204, 404):
                raise Exception(
                    f"Failed to delete {media_item_id}: "
                    f"{delete_resp.status_code} {delete_resp.text}"
                )

            deleted_count += 1
            time.sleep(0.1)  # critical: rate limiting

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return {
        "status": "completed",
        "deleted_count": deleted_count,
    }
