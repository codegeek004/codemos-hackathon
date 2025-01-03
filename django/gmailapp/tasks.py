from celery import shared_task
from googleapiclient.discovery import build
from .views import retrieve_credentials_for_user

# your_app/tasks.py
from celery import shared_task
from googleapiclient.discovery import build
from .views import retrieve_credentials_for_user

@shared_task
def delete_emails_task(user_id, category):
    try:
        creds = retrieve_credentials_for_user(user_id)
        service = build("gmail", "v1", credentials=creds)

        query = f"category:{category.split('_')[1].lower()}"
        deleted_count = 0
        page_token = None

        while True:
            # Fetch emails in batches
            results = service.users().messages().list(
                userId="me", q=query, pageToken=page_token
            ).execute()
            messages_list = results.get("messages", [])

            if not messages_list:
                break  # Exit loop if no messages are left

            # Delete each email in the batch
            for message in messages_list:
                service.users().messages().modify(
                    userId="me", 
                    id=message["id"],
                    body={
                        "removeLabelIds": "INBOX",
                        "addLabelIds": ["TRASH"]
                    }).execute()    
                deleted_count += 1

            # Get the next page token, if available
            page_token = results.get("nextPageToken")
            if not page_token:
                break  # Exit loop if there are no more pages

        return deleted_count  # Return the count of deleted emails
    except Exception as e:
        return str(e)  # Return the error message if something goes wrong
def delete_emails_task(user_id, category):
	try:
		creds = retrieve_credentials_for_user(user_id)
		service = build("gmail","v1",credentials=creds)

		query = f"category:{category.split('_')[1].lower()}"
		deleted_count = 0
		page_token=None

		while True:
			results = service.users().messages().list(
                userId="me", q=query, pageToken=page_token
            ).execute()
            messages_list = results.get("messages", [])

            if not messages_list:
                break  # Exit loop if no messages are left

            # Delete each email in the batch
            for message in messages_list:
                service.users().messages().modify(
                    userId="me", 
                    id=message["id"],
                    body={
                        "removeLabelIds": "INBOX",
                        "addLabelIds": ["TRASH"]
                    }).execute()    
                deleted_count += 1

            # Get the next page token, if available
            page_token = results.get("nextPageToken")
            if not page_token:
                break  # Exit loop if there are no more pages

        return deleted_count  # Return the count of deleted emails
    except Exception as e:
        return str(e)  # Return the error message if something goes wrong


