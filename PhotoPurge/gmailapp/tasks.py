from celery import shared_task
from googleapiclient.discovery import build
from .utils import retrieve_credentials_for_user
import logging 
from .models import TaskStatus, RecoverStatus
import requests
from django.core.mail import EmailMessage 
from .auth import check_token_validity, refresh_google_token  
import time
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from allauth.socialaccount.models import SocialAccount
#with bind=True we can use self in the function
@shared_task(bind=True)
def delete_emails_task(self, user_id, email, category):
	try:
		# task_status variable creates a new object of TaskStatus class or if it already existing it fetches its data by task_id and user_id and created is boolean variable which returns True or False for created or not created
		task_status, created = TaskStatus.objects.get_or_create(
			task_id=self.request.id,
			user_id=user_id
		)
	except Exception as e:
		return f"mera exception hai {e}"

	try:
		
		task_status.status = "IN_PROGRESS"
		task_status.save()
		
		# fetch credentials as dictionary from utils module
		creds = retrieve_credentials_for_user(user_id)
		if creds.expiry and isinstance(creds.expiry, str):
			creds.expiry = datetime.strptime(creds.expiry.replace(' ', 'T'), '%Y-%m-%dT%H:%M:%S.%f')

		# builds service for gmail api
		service = build("gmail", "v1", credentials=creds)
		
		query = f"category:{category.split('_')[1].lower()}"
		deleted_count = 0
		page_token = None
		
		while True:
			try:
				if not check_token_validity(creds.token):
					creds.refresh(Request())
					task_status.result = "Refreshing token"
					task_status.save()

					creds = retrieve_credentials_for_user(user_id)

					social_account = SocialAccount.objects.get(user_id=user_id, provider='google')
					social_token = SocialToken.objects.get(account=social_account)
					social_token.token = creds.token
					social_token.expires_at = creds.expiry
					social_token.save()
					time.sleep(15)

					
			except Exception as e:
				return f"kjsgbksjbgksb {e}"
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


		task_status.status = "SUCCESS"
		task_status.result = result_message
		task_status.deleted_count = deleted_count
		task_status.save()
		message = f"Your {task_status.deleted_count} emails have been deleted successfully! {task_status.result}. Thanks for choosing CODEMOS"
		email = EmailMessage('Emails deleted', message, to=[email])
		email.send()


		return result_message, messages_list

	except Exception as e:
		task_status.status = "FAILURE"
		task_status.result = f"An error occurred: {e}"
		task_status.save()


		return task_status.result


@shared_task(bind=True)
def recover_emails_task(self, user_id, email):
	try:

		task_status, created = RecoverStatus.objects.get_or_create(
			task_id=self.request.id,
			user_id=user_id
		)

		task_status.status = "IN_PROGRESS"
		task_status.save()

		creds = retrieve_credentials_for_user(user_id)
		if creds.expiry and isinstance(creds.expiry, str):
			creds.expiry = datetime.strptime(creds.expiry.replace(' ', 'T'), '%Y-%m-%dT%H:%M:%S.%f')

		service = build("gmail", "v1", credentials=creds)

		recover_count = 0
		next_page_token = None
		messages_list = []  

		while True:
			try:
				if not check_token_validity(creds.token):
					creds.refresh(Request())
					task_status.result = "Refreshing token"
					task_status.save()

					creds = retrieve_credentials_for_user(user_id)

					social_account = SocialAccount.objects.get(user_id=user_id, provider='google')
					social_token = SocialToken.objects.get(account=social_account)
					social_token.token = creds.token
					social_token.expires_at = creds.expiry
					social_token.save()
					time.sleep(15)

					
			except Exception as e:
				return f"kjsgbksjbgksb {e}"

			results = service.users().messages().list(
				userId="me",
				labelIds=["TRASH"],
				pageToken=next_page_token
			).execute()

			next_page_token = results.get("nextPageToken")

			if not next_page_token:
				break

			messages_list.extend(results.get("messages", []))

		if not messages_list:
			task_status.status = "SUCCESS"
			task_status.result = "No emails found in Trash."    
			task_status.save()
			return task_status.result


		for message in messages_list:
			msg_id = message['id']

			service.users().messages().modify(
				userId="me", 
				id=msg_id,
				body={"removeLabelIds": ["TRASH"]}
			).execute()

			recover_count += 1  

		result_message = f"Recovered {recover_count} emails."

		task_status.status = "SUCCESS"
		task_status.result = result_message
		task_status.recover_count = recover_count  
		task_status.save()
		message = f"Your {task_status.recover_count} emails have been recovered successfully! {task_status.result}. Thanks for choosing CODEMOS"
		email = EmailMessage('Emails deleted', message, to=[email])
		email.send()

		return result_message, recover_count

	except Exception as e:
		task_status.status = "FAILURE"
		task_status.result = f"An error occurred: {e}"
		task_status.save()

		return task_status.result
