import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64

# Define the Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate_gmail():
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
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)  # Use a fixed port
        # Save the credentials for next time
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def connect_to_gmail():
    creds = authenticate_gmail()
    service = build('gmail', 'v1', credentials=creds)
    return service

def search_emails(service, query):
    # Search for emails using a query
    results = service.users().messages().list(userId='me', q=query).execute()
    return results.get('messages', [])

def save_attachments(service, message, folder):
    # Get the message details
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

# def delete_email(service, message_id):
#     service.users().messages().delete(userId='me', id=message_id).execute()
#     print(f"Deleted email with ID: {message_id}")
def delete_email(service, message_id):
    print(f"Attempting to delete email with ID: {message_id}")
    try:
        service.users().messages().delete(userId='me', id=message_id).execute()
        print(f"Deleted email with ID: {message_id}")
    except Exception as e:
        print(f"Error deleting email {message_id}: {e}")

def main():
    print("Starting script...")
    service = connect_to_gmail()
    print("Connected to Gmail.")
    
    # Ask the user which category to target
    category = input("Which category would you like to delete? (social/promotions/forums/all): ").strip().lower()

    # Map category to Gmail queries
    category_queries = {
        'social': 'category:social',
        'promotions': 'category:promotions',
        'forums': 'category:forums',
        'all': 'category:social OR category:promotions OR category:forums'
    }

    if category not in category_queries:
        print("Invalid category. Please choose from social, promotions, forums, or all.")
        return

    query = category_queries[category]
    print(f"Searching for emails in category: {category}")

    # Step 2: Search for emails in the selected category
    messages = search_emails(service, query)
    
    if not messages:
        print(f"No emails found in the {category} category.")
        return

    print(f"Found {len(messages)} emails in the {category} category.")
    
    # Step 3: Ask if the user wants to save attachments
    save_attachments_option = input("Do you want to save attachments? (yes/no): ").strip().lower() == 'yes'
    attachment_folder = 'attachments'

    for message in messages:
        msg_id = message['id']
        print(f"Processing message ID: {msg_id}")
        
        if save_attachments_option:
            save_attachments(service, message, attachment_folder)
        
        # Step 4: Delete the email
        delete_email(service, msg_id)

    print("All selected emails processed successfully!")


if __name__ == '__main__':
    main()
