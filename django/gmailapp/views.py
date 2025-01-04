from django.shortcuts import render, redirect
from django.http import HttpResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .utils import retrieve_credentials_for_user
from django.contrib import messages
from allauth.socialaccount.models import SocialAccount, SocialToken



def index_view(request):
    return render(request, 'index.html')

from .tasks import delete_emails_task


def delete_emails_view(request):
    try:
        if not request.user.is_authenticated:
            messages.error(request, "You are not logged in. Please login to continue.")
            return redirect('index')

        if request.method == "GET":
            return render(request, "email_delete_form.html")

        if request.method == "POST":
            category = request.POST.get("category")
            valid_categories = [
                "CATEGORY_PROMOTIONS",
                "CATEGORY_SOCIAL",
                "CATEGORY_UPDATES",
                "CATEGORY_FORUMS",
            ]
            if category not in valid_categories:
                return HttpResponse("Invalid category selected.", status=400)


            try:
                creds = retrieve_credentials_for_user(request.user)
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
                        messages.warning(request, f"There are no emails in {category}")
                        break  # Exit loop if no messages are left

                    # #insert these emails into database
                    # email_data = [Gmail(user=request.user, message_id=message['id'], thread_id=message['threadId'])
                    #     for message in messages_list]
                    # try:
                    #     print('gmail insert wale try mai')
                    #     Gmail.objects.bulk_create(email_data)
                    # except Exception as e:
                    #     print(f'Gmail Insertion Error: {e}')

                    # Delete each email in the batch
                    for message in messages_list:
                        #deletes permanently
                        # service.users().messages().delete(userId="me", id=message["id"]).execute()
                        #adds to trash
                        service.users().messages().modify(
                            userId="me", 
                            id=message["id"],
                            body={
                                "removeLabelIds":"INBOX",
                                "addLabelIds":["TRASH"]
                            }).execute()    
                        deleted_count += 1

                    # Get the next page token, if available
                    page_token = results.get("nextPageToken")
                    if not page_token:
                        break  # Exit loop if there are no more pages

                messages.success(request, f"Deleted {deleted_count} conversations in the {category} category")
                return redirect('delete_emails')

            except Exception as e:
                messages.warning(request, f"Something went wrong")
                return redirect('delete_emails')


            delete_emails_task.delay(request.user.id, category)

            messages.success(request, "Your email deletion request has been started.")
            return redirect('delete_emails')




    except SocialAccount.DoesNotExist:
        raise Exception("Google account not linked to this user.")
    except SocialToken.DoesNotExist:
        raise Exception("No Google token found for this user.")

#####recover deleted emails############
def recover_emails_from_trash_view(request):
    if not request.user.is_authenticated:
        return HttpResponse("You are not logged in. Please login to continue.", status=403)

    try:
        creds = retrieve_credentials_for_user(request.user)
        service = build("gmail", "v1", credentials=creds)

        # Step 1: Fetch emails from Trash folder
        results = service.users().messages().list(userId="me", labelIds=["TRASH"]).execute()
        messages_list = results.get("messages", [])
        
        if not messages_list:
            return render(request, 'recover_emails.html', {"error": "No emails found in Trash."})

        # Step 2: Restore emails from Trash
        restored_count = 0
        for message in messages_list:
            # Move email from Trash to Inbox (remove TRASH label)
            msg_id = message['id']
            msg = service.users().messages().modify(
                userId="me", 
                id=msg_id,
                body={"removeLabelIds": ["TRASH"]}
            ).execute()
            restored_count += 1
        
        # After successful recovery, render success message
        return render(request, 'recover_emails.html', {"success": f"Successfully restored {restored_count} emails from Trash."})

    except Exception as e:
        # In case of any error, render the error message
        return render(request, 'recover_emails.html', {"error": f"An error occurred while recovering emails: {e}"})
