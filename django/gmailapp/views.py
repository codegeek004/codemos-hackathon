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
#adding explicitly this error 'HttpError'

from googleapiclient.errors import HttpError 
#adding explicitly this error 'HttpError'


from googleapiclient.errors import HttpError 
#adding explicitly this error 'HttpError'


def index_view(request):
    return render(request, 'index.html')


def delete_emails_view(request):
    try:
        creds = retrieve_credentials_for_user(request.user.id)
        if check_token_validity(creds.token) == False:
            request.session.flush()
            logout(request)
            messages.warning(request, 'Your session was expired. login again to continue')
            return redirect('index')

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
        messages.error(request, f"An error occurred while processing your request. {e}")
        return render(request, 'email_delete_form.html')


def check_task_status_view(request, task_id):
    try:
        creds = retrieve_credentials_for_user(request.user.id)
        if check_token_validity(creds.token) == False:
            request.session.flush()
            logout(request)
            messages.warning(request, 'Your session was expired. login again to continue')
            return redirect('index')

        if not request.user.is_authenticated:
            messages.error(request, "You are not logged in. Please login to continue.")
            return redirect('index')

        task_status = TaskStatus.objects.get(task_id=task_id, user=request.user)

        if task_status.status == "SUCCESS":
            print(request.user.email)
            message = f"Your {task_status.deleted_count} emails have been deleted successfully! {task_status.result}"
            email = EmailMessage('Emails deleted', f'Your {task_status.deleted_count} emails has been deleted succesfully. Thanks for choosing CODEMOS.', to=[request.user.email])
            email.send()

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

        task = recover_emails_task.delay(request.user.id)

        RecoverStatus.objects.create(
            task_id=task.id,
            user=request.user,
            status='IN_PROGRESS'
            )
        messages.success(request, 'Your email recovery is in progress. You will be notified when all emails are recovered successfully.')

        return redirect('email_recovery_status', task_id=task.id)
    
    except Exception as e:
        print(e)
        messages.error(request, f"An error occurred while processing your request. {e}")
        return render(request, 'email_delete_form.html')

def email_recovery_status_view(request, task_id):
    try:
        if not request.user.is_authenticated:
            messages.warning('You are not logged in. Login to perform this action')
            return redirect('index')

        task_status = RecoverStatus.objects.get(task_id=task_id, user=request.user)
        print(task_status.status, 'lskglsgbllskb')
        if task_status.status == "SUCCESS":
            print(request.user.email)
            message = f"Your {task_status.recover_count} emails have been deleted successfully! {task_status.result}"
            email = EmailMessage('Emails deleted', f'Your {task_status.recover_count} emails has been deleted succesfully. Thanks for choosing CODEMOS.', to=[request.user.email])
            email.send()

        elif task_status.status == "FAILURE":
            message = "An error occurred while deleting emails. Please try again later."
        else:  
            message = "Your email deletion is still in progress. Please check back later."

        context = {
            "message": message,
            "task_status": task_status
        }
        return render(request, "recovery_task_status.html", context)

    except TaskStatus.DoesNotExist:
        messages.error(request, "Task not found or you do not have permission to view it.")
        return redirect('index')
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect('index')









