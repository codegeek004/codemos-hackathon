from django.urls import path

from . import views  # Import your views from the current app
from photos import views as photos_views 

from . import views, auth  

urlpatterns = [
    path('delete_emails/', views.delete_emails_view, name='delete_emails'),  # Endpoint to delete emails
    path('recover_emails/', views.recover_emails_from_trash_view, name='recover_emails'),
    path('migrate/', photos_views.migrate_photos, name='migrate_photos'),  # Migrate photos
    path('logout/', auth.logout_view, name='logout_url')
]
