from django.shortcuts import render
from django.http import HttpResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def delete_emails_view(request):
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

                messages = results.get("messages", [])
                if not messages:
                    break  # Exit loop if no messages are left

                # Delete each email in the batch
                for message in messages:
                    service.users().messages().delete(userId="me", id=message["id"]).execute()
                    deleted_count += 1

                # Get the next page token, if available
                page_token = results.get("nextPageToken")
                if not page_token:
                    break  # Exit loop if there are no more pages

            return HttpResponse(f"Deleted {deleted_count} emails in the {category} category.", status=200)

        except Exception as e:
            return HttpResponse(f"An error occurred: {e}", status=500)



from allauth.socialaccount.models import SocialAccount, SocialToken

def retrieve_credentials_for_user(user):
    try:
        # Get the social account for the user
        social_account = SocialAccount.objects.get(user=user, provider="google")
        
        # Get the associated social token
        social_token = SocialToken.objects.get(account=social_account)
        
        # Build the credentials
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=social_token.token,
            refresh_token=social_token.token_secret,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="your-client-id.apps.googleusercontent.com",
            client_secret="your-client-secret",
        )
        return creds
    except SocialAccount.DoesNotExist:
        raise Exception("Google account not linked to this user.")
    except SocialToken.DoesNotExist:
        raise Exception("No Google token found for this user.")
