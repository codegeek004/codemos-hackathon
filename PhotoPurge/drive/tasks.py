from google.auth.transport.requests import Request
from celery import shared_task
from drive.utils import (
    get_drive_service,
    get_drive_files,
    download_all_formats,
    upload_all_formats,
    create_drive_folder,
    trash_drive_file,
    FOLDER_MIME
)
from .models import MigrationStatus, FailedMigration
from django.core.mail import EmailMessage
import logging
import time
from datetime import datetime
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta


def refresh_if_older_than(credentials_dict, minutes=50):
    """
    Refresh token if it's older than specified minutes (default 50 min to be safe before 60 min expiry)
    """
    last_refresh = credentials_dict.get('token_refreshed_at')

    if not last_refresh:
        # First time or no tracking, refresh now
        print('TOken refreshed')
        return refresh_credentials_if_needed(credentials_dict)

    age = datetime.utcnow() - last_refresh
    if age > timedelta(minutes=minutes):
        print(
            "Token is {age.total_seconds()/60:.1f} minutes old, refreshing...")
        return refresh_credentials_if_needed(credentials_dict)

    return credentials_dict


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
            creds.refresh(Request())
            credentials_dict['token'] = creds.token
            credentials_dict['token_refreshed_at'] = datetime.utcnow()
        elif not creds.expiry:
            # No expiry info, refresh to be safe
            creds.refresh(Request())
            credentials_dict['token'] = creds.token
            credentials_dict['token_refreshed_at'] = datetime.utcnow()

        return credentials_dict
    except Exception as e:
        print('Inside exception', e)
        raise


@shared_task(bind=True, default_retry_delay=60, max_retries=3)
def migrate_drive_task(self, user_id, email_id, source_credentials, destination_credentials):
    try:
        task_status, created = MigrationStatus.objects.get_or_create(
            task_id=self.request.id,
            user_id=user_id,
        )
        task_status.status = "IN_PROGRESS"
        task_status.save()

        # Initial credential refresh
        source_credentials = refresh_credentials_if_needed(source_credentials)
        source_credentials['token_refreshed_at'] = datetime.utcnow()

        destination_credentials = refresh_credentials_if_needed(
            destination_credentials)
        destination_credentials['token_refreshed_at'] = datetime.utcnow()

        dest_service = get_drive_service(destination_credentials)
        current_page_token = None
        migrated_count = 0
        total_seen = 0
        folder_map = {}  # {source_folder_id: dest_folder_id}

        while True:
            source_credentials = refresh_if_older_than(
                source_credentials, minutes=50)

            files, next_page_token = get_drive_files(
                source_credentials, current_page_token)
            total_seen += len(files)

            for item in files:
                file_id = item['id']
                file_name = item['name']
                mime_type = item['mimeType']
                source_parent_ids = item.get('parents', [])
                source_parent_id = source_parent_ids[0] if source_parent_ids else None

                source_credentials = refresh_if_older_than(
                    source_credentials, minutes=50)
                destination_credentials = refresh_if_older_than(
                    destination_credentials, minutes=50)

                if destination_credentials.get('token_just_refreshed'):
                    dest_service = get_drive_service(destination_credentials)
                    destination_credentials.pop('token_just_refreshed', None)

                try:
                    dest_parent_id = folder_map.get(
                        source_parent_id) if source_parent_id else None

                    if mime_type == FOLDER_MIME:
                        new_folder_id = create_drive_folder(
                            dest_service, file_name, dest_parent_id)
                        folder_map[file_id] = new_folder_id
                        continue

                    src_service = get_drive_service(source_credentials)

                    downloads = download_all_formats(
                        src_service, file_id, file_name, mime_type)
                    if not downloads:
                        FailedMigration.objects.create(
                            task_id=self.request.id,
                            user_id=user_id,
                            file_id=file_id,
                            file_name=file_name,
                            reason="No downloadable formats available for this file type."
                        )
                        continue

                    uploaded = upload_all_formats(
                        dest_service, downloads, dest_parent_id)

                    if uploaded > 0:
                        trash_drive_file(src_service, file_id)
                        migrated_count += uploaded
                        task_status.migrated_count = migrated_count
                        task_status.total_count = total_seen
                        task_status.save()
                    else:
                        FailedMigration.objects.create(
                            task_id=self.request.id,
                            user_id=user_id,
                            file_id=file_id,
                            file_name=file_name,
                            reason="All format uploads failed. Source file kept."
                        )

                    time.sleep(5)

                except Exception as e:
                    FailedMigration.objects.create(
                        task_id=self.request.id,
                        user_id=user_id,
                        file_id=file_id,
                        file_name=file_name,
                        reason=str(e)
                    )
                    continue

            if not next_page_token:
                break
            current_page_token = next_page_token

        failed_count = FailedMigration.objects.filter(
            task_id=self.request.id).count()
        result_message = f"Migrated {migrated_count} files out of {total_seen} items. {failed_count} failed."
        task_status.status = "SUCCESS"
        task_status.result = result_message
        task_status.save()

        try:
            message = f"{migrated_count} files have been successfully migrated and removed from your source account. {failed_count} files could not be migrated. Thank you for using our service!"
            email = EmailMessage('Drive Migration Complete',
                                 message, to=[email_id])
            email.send()
        except Exception as e:
            print(f'Exception is {e}')
            return result_message

    except Exception as e:
        task_status.status = "FAILED"
        task_status.result = f"Error: {e}"
        task_status.save()
        raise self.retry(exc=e)
