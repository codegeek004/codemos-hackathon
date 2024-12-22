from googleapiclient.errors import HttpError

def delete_emails(service):
    print('delete emails mai gay')
    """
    Function to delete emails from the user's Gmail account.
    """
    try:
        # Get list of emails (you can define your own query/filter here)
        results = service.users().messages().list(userId='me').execute()
        messages = results.get('messages', [])

        if not messages:
            return "No emails to delete."

        # Loop through the messages and delete them in batches of 1000
        message_ids = [message['id'] for message in messages]
        batch_size = 1000
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i + batch_size]
            service.users().messages().batchDelete(
                userId='me',
                body={'ids': batch}
            ).execute()

        return f"Successfully deleted {len(messages)} emails."

    except HttpError as error:
        return f"An error occurred while deleting emails: {error}"

    except Exception as e:
        return f"Unexpected error: {e}"
