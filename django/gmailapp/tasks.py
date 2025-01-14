from celery import shared_task
from googleapiclient.discovery import build
from .utils import retrieve_credentials_for_user
import logging 
from .models import TaskStatus

#with bind=True we can use self in the function
@shared_task(bind=True)
def delete_emails_task(self, user_id, category):
    try:
        try:
        
            task_status, created = TaskStatus.objects.get_or_create(
                    task_id = self.request.id,
                    user_id = user_id
                )
            task_status.status = "IN_PROGRESS"
            task_status.save()
        except Exception as e:
            return e


        if not isinstance(category, str):
            raise ValueError("The 'category' parameter must be a string in the format 'CATEGORY_NAME'.")

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

            # Delete emails in the batch
            for message in messages_list:
                service.users().messages().modify(
                    userId="me", 
                    id=message["id"],
                    body={
                        "removeLabelIds": ["INBOX"],
                        "addLabelIds": ["TRASH"]
                    }).execute()
                deleted_count += 1

            # Get next page token, if any
            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return f"Deleted {deleted_count} emails in category {category}"
    except Exception as e:
        task_status.status = "FAILURE"
        task_status.result = "An error occurred"
        task_status.save()
        return f"An error occurred: {e}"
