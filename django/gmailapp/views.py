from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .utils import retrieve_credentials_for_user
from django.contrib import messages
from allauth.socialaccount.models import SocialAccount, SocialToken
from .models import TaskStatus
import json
from allauth.socialaccount.models import SocialAccount, SocialToken
from .tasks import delete_emails_task
from django.shortcuts import get_object_or_404
from django.db import transaction


def index_view(request):
    return render(request, 'index.html')


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

            task = delete_emails_task.delay(request.user.id, category)

            # Create TaskStatus object to track task progress
            TaskStatus.objects.create(
                task_id=task.id,
                user=request.user,
                status="IN_PROGRESS"
            )

            messages.success(request, "Your email deletion request has been started. You will be notified upon completion.")
            
            # Redirect to check the task status using the task_id
            return redirect('check_task_status', task_id=task.id)

    except Exception as e:
        print(e)
        messages.error(request, "An error occurred while processing your request.")
        return render(request, 'email_delete_form.html')


def check_task_status_view(request, task_id):
    try:
        if not request.user.is_authenticated:
            messages.error(request, "You are not logged in. Please login to continue.")
            return redirect('index')

        task_status = TaskStatus.objects.get(task_id=task_id, user=request.user)

        if task_status.status == "SUCCESS":
            message = f"Your emails have been deleted successfully! {task_status.result}"
        elif task_status.status == "FAILURE":
            message = "An error occurred while deleting emails. Please try again later."
        else:  
            message = "Your email deletion is still in progress. Please check back later."

        context = {
            "message": message,
            "task_status": task_status
        }
        return render(request, "check_task_status.html", context)

    except TaskStatus.DoesNotExist:
        messages.error(request, "Task not found or you do not have permission to view it.")
        return redirect('index')
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect('index')




#####recover deleted emails############
def recover_emails_from_trash_view(request):
    if not request.user.is_authenticated:
        return HttpResponse("You are not logged in. Please login to continue.", status=403)

    try:
        creds = retrieve_credentials_for_user(request.user)
        service = build("gmail", "v1", credentials=creds)

        messages_list = []
        next_page_token = None

        while True:
            results = service.users().messages().list(
                userId="me", 
                labelIds=["TRASH"], 
                pageToken=next_page_token
            ).execute()
            
            messages_list.extend(results.get("messages", []))
            
            next_page_token = results.get("nextPageToken")
            if not next_page_token:
                break
        
        if not messages_list:
            return render(request, 'recover_emails.html', {"error": "No emails found in Trash."})

        restored_count = 0
        for message in messages_list:
            msg_id = message['id']
            service.users().messages().modify(
                userId="me", 
                id=msg_id,
                body={"removeLabelIds": ["TRASH"]}
            ).execute()

            restored_count += 1

        return render(request, 'recover_emails.html', {"success": f"Successfully restored {restored_count} emails from Trash."})

    
    except Exception as e:
        return render(request, 'recover_emails.html', {"error": f"An error occurred while recovering emails: {e}"})
