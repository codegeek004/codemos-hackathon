from celery import shared_task
from .utils import get_photos_service, download_photo, upload_photo, get_photos

@shared_task
def migrate_all_photos_task(source_credentials, destination_credentials):
    destination_service = get_photos_service(destination_credentials)
    current_page_token = None
    all_photos = []

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

    return len(all_photos)  # Return the count of migrated photos


@shared_task
def migrate_selected_photos_task(source_credentials, destination_credentials, selected_photo_ids):
    destination_service = get_photos_service(destination_credentials)
    photos, _ = get_photos(source_credentials)

    selected_photos = [photo for photo in photos if photo['id'] in selected_photo_ids]
    for photo in selected_photos:
        file_url = photo['baseUrl'] + "=d"
        file_name = photo['filename']
        photo_data = download_photo(file_url)
        if photo_data:
            upload_photo(destination_service, photo_data, file_name)

    return f"Migrated {len(selected_photos)} photos"  # Return the count of migrated photos
