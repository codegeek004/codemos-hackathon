from django.urls import path
from . import views  # Import your views from the current app

urlpatterns = [
    # path('show/', views.show, name='show'),  # Test endpoint to check OAuth completion
    path('delete_emails/', views.delete_emails_view, name='delete_emails'),  # Endpoint to delete emails
    path('recover_emails/', views.recover_emails_from_trash_view, name='recover_emails'),

    # path('fetch_google_token/', views.fetch_google_token, name='fetch_google_token'),  # Endpoint to fetch Google tokens
]
