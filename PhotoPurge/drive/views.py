from drive.utils import get_drive_files
from drive.tasks import migrate_drive_task
from drive.models import MigrationStatus, FailedMigration
from photos.views import retrieve_credentials_for_user
from gmailapp.auth import check_token_validity
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import logout


def migrate_drive(request):
    request.session['next'] = 'migrate_drive'
    if not request.user.is_authenticated:
        messages.error(
            request, "You are not logged in. Please login to continue.")
        return redirect("index")

    # token validity check — same as migrate_photos
    creds = retrieve_credentials_for_user(request.user.id)
    if not check_token_validity(creds.token):
        request.session.flush()
        logout(request)
        messages.warning(
            request, "Your session has expired. Please log in again to continue.")
        return redirect("index")

    # source credentials
    try:
        creds = retrieve_credentials_for_user(request.user)
    except Exception as e:
        messages.error(request, f"Error retrieving source credentials: {e}")
        return redirect("/accounts/google/login/?process=login")

    src_creds = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

    # fetch one page of drive files for preview
    page_token = request.GET.get("page_token")
    try:
        drive_files, next_page_token = get_drive_files(src_creds, page_token)
    except Exception as e:
        messages.error(request, f"Could not list Drive files: {e}")
        drive_files, next_page_token = [], None

    destination_credentials = request.session.get("destination_credentials")

    # fetch latest migration task status for this user
    task_status = MigrationStatus.objects.filter(
        user_id=request.user.id
    ).order_by("-created_at").first()

    # POST handler
    if request.method == "POST" and "action" in request.POST:
        if not destination_credentials:
            messages.error(request, "Destination account not selected.")
            return redirect("migrate_drive")

        if request.POST["action"] == "migrate_all_drive":
            task = migrate_drive_task.delay(
                request.user.id,
                request.user.email,
                src_creds,
                destination_credentials,
            )
            messages.success(
                request, f"Drive migration started. Task ID: {task.id}")
            return redirect("migrate_drive")

    return render(request, "drive_migration.html", {
        "drive_files": drive_files,
        "next_page_token": next_page_token,
        "task_status": task_status,
        "destination_authenticated": bool(destination_credentials),
    })
