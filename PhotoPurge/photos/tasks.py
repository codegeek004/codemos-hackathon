from celery import shared_task
from .utils import get_photos_service, download_photo, upload_photo, get_photos
from .models import MigrationStatus
from django.core.mail import EmailMessage
import logging
logger = logging.getLogger(__name__)
import time

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
        destination_service = get_photos_service(destination_credentials)
        current_page_token = None
        all_photos = []
        migrated_count = 0

        # Paginate through source photos
        while True:
            try:
                photos, next_page_token = get_photos(source_credentials, current_page_token)
            except Exception as e:
                logger.error(f"Failed to fetch photos: {e}")
                task_status.status = "FAILED"
                task_status.result = f"Error fetching photos: {e}"
                task_status.save()

                raise self.retry(exc=e)

            all_photos.extend(photos)

            for photo in photos:
                file_url = photo['baseUrl'] + "=d"
                file_name = photo['filename']

                try:
                    photo_data = download_photo(file_url)
                    if photo_data:
                        upload_photo(destination_service, photo_data, file_name)
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
            email = EmailMessage('Photo Migration Complete', message, to=[email_id])
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
    destination_service = get_photos_service(destination_credentials)
    photos, _ = get_photos(source_credentials)

    task_status, created = MigrationStatus.objects.get_or_create(
            task_id = self.request.id,
            user_id=user_id,
        )


    selected_photos = [photo for photo in photos if photo['id'] in selected_photo_ids]
    
    for photo in selected_photos:
        file_url = photo['baseUrl'] + "=d"
        file_name = photo['filename']
        photo_data = download_photo(file_url)
        if photo_data:
            upload_photo(destination_service, photo_data, file_name)
    
    result_message = f"Migrated {len(selected_photos)} photos"

    task_status.status = "SUCCESS"
    task_status.result = result_message
    task_status.migrated_count = len(selected_photos)
    task_status.save()
    message = f"migrated {len(selected_photos)} from your account. Thanks for choosing CODEMOS"
    email = EmailMessage('Migrated photos', message, to=[source_email])
    email.send()
    return result_message
