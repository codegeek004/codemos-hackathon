from celery import shared_task
from googleapiclient.discovery import build
from .utils import retrieve_credentials_for_user
import logging 
from .models import TaskStatus
import requests

#with bind=True we can use self in the function
@shared_task(bind=True)
def delete_emails_task(self, user_id, category):
    try:
        # Get or create the TaskStatus object
        task_status, created = TaskStatus.objects.get_or_create(
            task_id=self.request.id,
            user_id=user_id
        )

        # Set the initial status to IN_PROGRESS
        task_status.status = "IN_PROGRESS"
        task_status.save()

        creds = retrieve_credentials_for_user(user_id)
        service = build("gmail", "v1", credentials=creds)

        query = f"category:{category.split('_')[1].lower()}"
        deleted_count = 0
        page_token = None

        while True:
            results = service.users().messages().list(
                userId="me", q=query, pageToken=page_token
            ).execute()
            messages_list = results.get("messages", [])

            if not messages_list:
                task_status.status = "SUCCESS"
                task_status.result = f"No emails found in {category}"
                task_status.save()
                return task_status.result

            for message in messages_list:
                service.users().messages().modify(
                    userId="me",
                    id=message["id"],
                    body={
                        "removeLabelIds": ["INBOX"],
                        "addLabelIds": ["TRASH"]
                    }).execute()
                deleted_count += 1

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        result_message = f"Deleted {deleted_count} emails in category {category}"

        # Update the TaskStatus to SUCCESS once the task completes
        task_status.status = "SUCCESS"
        task_status.result = result_message
        task_status.save()

        return result_message, messages_list

    except Exception as e:
        # Handle errors and update status to FAILURE if something goes wrong
        task_status.status = "FAILURE"
        task_status.result = f"An error occurred: {e}"
        task_status.save()

        return task_status.result



