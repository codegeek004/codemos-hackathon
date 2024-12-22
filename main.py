import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64

# Define the Gmail API scope (ensure modify scope is included)
SCOPES = ['https://mail.google.com/']



def authenticate_gmail():
    """
    Authenticate and return the Gmail API service.
    """
    creds = None
    # Check if token.pickle already exists (for reauthentication)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If no valid credentials, authenticate with OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print(f"Requesting the following scopes: {SCOPES}")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)  # Use a fixed port
        # Save the credentials for next time
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def connect_to_gmail():
    """
    Connect to the Gmail API and return the service.
    """
    creds = authenticate_gmail()
    service = build('gmail', 'v1', credentials=creds)
    return service


def search_emails(service, query):
    """
    Search for emails using a query.
    """
    print(f"Searching emails with query: {query}")
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    print(f"Found {len(messages)} emails matching the query.")
    return messages


def save_attachments(service, message, folder):
    """
    Save attachments from the email to a specified folder.
    """
    msg = service.users().messages().get(userId='me', id=message['id']).execute()
    parts = msg['payload'].get('parts', [])
    
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    for part in parts:
        if part.get('filename'):  # Check if the part is an attachment
            att_id = part['body'].get('attachmentId')
            if att_id:
                att = service.users().messages().attachments().get(
                    userId='me', messageId=message['id'], id=att_id).execute()
                data = base64.urlsafe_b64decode(att['data'])
                file_path = os.path.join(folder, part['filename'])
                with open(file_path, 'wb') as f:
                    f.write(data)
                print(f"Attachment saved: {file_path}")


def delete_email(service, message_id):
    """
    Delete an email by its message ID.
    """
    print(f"Attempting to delete email with ID: {message_id}")
    try:
        service.users().messages().delete(userId='me', id=message_id).execute()
        print(f"Deleted email with ID: {message_id}")
    except Exception as e:
        print(f"Error deleting email {message_id}: {e}")


def delete_emails_batch(service, message_ids):
    """
    Delete multiple emails in a batch using their message IDs.
    """
    print(f"Attempting to batch delete {len(message_ids)} emails.")
    try:
        service.users().messages().batchDelete(
            userId='me',
            body={'ids': message_ids}
        ).execute()
        print(f"Batch deleted {len(message_ids)} emails successfully.")
    except Exception as e:
        print(f"Error during batch deletion: {e}")



def main():
    """
    Main function to delete Gmail emails by category or all emails.
    """
    print("Starting script...")
    service = connect_to_gmail()
    print("Connected to Gmail.")
    
    # Ask the user which category to target
    category = input("Which category would you like to delete? (social/promotions/forums/updates/all): ").strip().lower()

    # Map category to Gmail queries
    category_queries = {
        'social': 'category:social',
        'promotions': 'category:promotions',
        'forums': 'category:forums',
        'updates': 'category:updates',
        'all': ''  # Empty query for all emails
    }

    if category not in category_queries:
        print("Invalid category. Please choose from social, promotions, forums, updates, or all.")
        return

    query = category_queries[category]
    print(f"Searching for emails in category: {category}")

    # Step 1: Retrieve emails
    messages = []
    page_token = None
    while True:
        results = service.users().messages().list(userId='me', q=query, pageToken=page_token, maxResults=500).execute()
        messages.extend(results.get('messages', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break

    print(f"Total emails fetched in category '{category}': {len(messages)}")

    if not messages:
        print(f"No emails found in the '{category}' category.")
        return

    # Step 2: Confirm before deletion
    confirm = input(f"Are you sure you want to delete {len(messages)} emails in the '{category}' category? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Operation canceled.")
        return

    # Step 3: Delete emails in batches of 1000
    batch_size = 2000
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        message_ids = [msg['id'] for msg in batch]
        delete_emails_batch(service, message_ids)

    print(f"All emails in the '{category}' category processed successfully!")


if __name__ == '__main__':
    main()
