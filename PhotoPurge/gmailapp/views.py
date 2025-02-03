from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .utils import retrieve_credentials_for_user
from django.contrib import messages
from .models import TaskStatus, RecoverStatus
import json
from allauth.socialaccount.models import SocialAccount, SocialToken

from .tasks import delete_emails_task, recover_emails_task
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from .auth import check_token_validity
from django.contrib.auth import logout
from googleapiclient.errors import HttpError 
from .auth import check_token_validity


def index_view(request):

    return render(request, 'index.html')

def privacy_policy_view(request):
    return render(request, 'privacy_policy.html')

# works when when delete emails button is triggered 
def delete_emails_view(request):
    try:
        if not request.user.is_authenticated:
            messages.error(request, "You are not logged in. Please login to continue.")
            return redirect('index')
        # fetch the credentials for the user. The credentials are in the dictionary format
        creds = retrieve_credentials_for_user(request.user.id)
        if check_token_validity(creds.token) == False:
            request.session.flush()
            logout(request)
            messages.warning(request, 'Your session was expired. login again to continue')
            return redirect('index')

        if request.method == "GET":
            return render(request, "email_delete_form.html")

        # User inputs the category from the form
        if request.method == "POST":
            category = request.POST.get("category")
            valid_categories = [
                "CATEGORY_PROMOTIONS",
                "CATEGORY_SOCIAL",
                "CATEGORY_UPDATES",
                "CATEGORY_FORUMS",
            ]
            # print('request.data'. request.POST)
            if category is None:
                messages.error(request, 'Category is required')
                return redirect('delete_emails')
            if category not in valid_categories:
                return HttpResponse("Invalid category selected.", status=400)
            
            # task defined in tasks module
            try:
                task = delete_emails_task.delay(request.user.id, request.user.email, category)
            except Exception as e:
                messages.error(request, f"Error {e}")
            # Create TaskStatus object to track task progress
            TaskStatus.objects.create(
                task_id=task.id,
                user=request.user,
                status="IN_PROGRESS"
            )
            
            messages.success(request, "Your email deletion request has been started.It might take several hours")
            messages.success(request, " You will get an email  notification upon completion.")
            
            # The message will be displayed on this html page
            return render(request, 'email_delete_form.html')
    
    except Exception as e:
        print(e)
        messages.error(request, f"An error occurred while processing your request. {e}")
        return render(request, 'email_delete_form.html')


#####recover deleted emails############

# works when recover emails button is triggered
def recover_emails_from_trash_view(request):
    if not request.user.is_authenticated:
        messages.error(request, "You are not logged in. Please login to continue.")
        return redirect('index')

    try:
        # this task is also defined in tasks module
        task = recover_emails_task.delay(request.user.id, request.user.email)
        
        # create object to create a new instance of RecoverStatus
        RecoverStatus.objects.create(
            task_id=task.id,
            user=request.user,
            status='IN_PROGRESS'
            )
        messages.success(request, 'Your email recovery is in progress. You will be notified when all emails are recovered successfully.')
        # The message will be displayed on this html page
        return render(request, 'email_delete_form.html')
    
    except Exception as e:
        print(e)
        messages.error(request, f"An error occurred while processing your request. {e}")
        return render(request, 'email_delete_form.html')









