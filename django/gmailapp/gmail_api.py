# gmail_api.py

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://mail.google.com/']
print('yash')
def connect_to_gmail():
    """
    Connect to Gmail API and return the service.
    """
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def search_emails(service, query):
    """
    Search for emails using a query.
    """
    results = service.users().messages().list(userId='me', q=query).execute()
    return results.get('messages', [])


def delete_emails_batch(service, message_ids):
    """
    Delete a batch of emails using Gmail API.

    :param service: The Gmail API service instance.
    :param message_ids: A list of email message IDs to delete.
    """
    try:
        service.users().messages().batchDelete(
            userId='me',
            body={'ids': message_ids}
        ).execute()
    except Exception as e:
        raise Exception(f"Error deleting emails: {str(e)}")
