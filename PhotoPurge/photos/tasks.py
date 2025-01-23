from celery import shared_task
from .utils import get_photos_service, download_photo, upload_photo, get_photos
from .models import MigrationStatus
from django.core.mail import EmailMessage


@shared_task(bind=True)
def migrate_all_photos_task(self, user_id, email_id, source_credentials, destination_credentials):
    
    task_status, created = MigrationStatus.objects.get_or_create(
            task_id = self.request.id,
            user_id=user_id,
        )

    task_status.status = "IN_PROGRESS"
    task_status.save()


<<<<<<< HEAD
    destination_service = get_photos_service(destination_credentials)
    current_page_token = None
    all_photos = []
=======
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
>>>>>>> 3e5d234f (added sleep timer for this to avoid rate limiting)

    while True:
        photos, next_page_token = get_photos(source_credentials, current_page_token)
        all_photos.extend(photos)

        for photo in photos:
            file_url = photo['baseUrl'] + "=d"
            file_name = photo['filename']
            photo_data = download_photo(file_url)
            if photo_data:
                upload_photo(destination_service, photo_data, file_name)

<<<<<<< HEAD
        if not next_page_token:
            break
=======
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
>>>>>>> 3e5d234f (added sleep timer for this to avoid rate limiting)

    result_message = f"Migrated {len(all_photos)} photos"

    task_status.status = "SUCCESS"
    task_status.result = result_message
    task_status.migrated_count = len(all_photos)
    task_status.save()

    message = f"{len(all_photos)} migrated from your account. Thanks for choosing CODEMOS"
    email = EmailMessage('Migrated photos', message, to=[email_id])
    email.send()
    return result_message  # Return the count of migrated photos


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
