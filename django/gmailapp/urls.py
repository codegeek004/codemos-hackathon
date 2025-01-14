from django.urls import path
from . import views  
urlpatterns = [
    # path('show/', views.show, name='show'),  # Test endpoint to check OAuth completion
    path('delete_emails/', views.delete_emails_view, name='delete_emails'),  # Endpoint to delete emails
    path('recover_emails/', views.recover_emails_from_trash_view, name='recover_emails'),
    path('check_task_status/<str:task_id>/', views.check_task_status_view, name='check_task_status'),

    # path('polling/<str:task_id>/', views.polling_view, name='polling_view'), 
    # path('fetch_google_token/', views.fetch_google_token, name='fetch_google_token'),  # Endpoint to fetch Google tokens
    ##webhook url
    # path('delete_emails/webhook/task_completed/', views.task_completed_webhook, name='task_completed_webhook')
]
