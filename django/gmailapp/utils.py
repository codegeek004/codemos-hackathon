from googleapiclient.errors import HttpError

def delete_emails(service):
    """
    Function to delete emails from the user's Gmail account.
    """
    try:
        print('delete emails method invoked.')

        # Fetch the list of emails. You can modify the query parameter to target specific emails.
        results = service.users().messages().list(userId='me').execute()
        messages = results.get('messages', [])

        if not messages:
            return "No emails to delete."

        # Extract email IDs
        message_ids = [message['id'] for message in messages]
        batch_size = 1000

        # Delete emails in batches of 1000
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i + batch_size]
            service.users().messages().batchDelete(
                userId='me',
                body={'ids': batch}
            ).execute()

        return f"Successfully deleted {len(messages)} emails."

    except HttpError as error:
        print(f"An error occurred: {error}")
        return f"An error occurred while deleting emails: {error}"

    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"
