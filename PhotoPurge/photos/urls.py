from photos import views, auth
from django.urls import include, path
from photos import views

urlpatterns = [
    # Home page (optional, can be added later)
    # path('', views.home, name='home'),  
    
    # Photo migration related URLs
    path('migrate/', views.migrate_photos, name='migrate_photos'),  # Migrate photos
    
    # Google authentication for source and destination accounts
     # Include allauth URLs (handles Google OAuth automatically)

    # path('accounts/', include('allauth.urls')),  # Allauth authentication URLs
    path('destination/oauth/', auth.dest_oauth, name='dest-oauth'),
    path('destination/auth/', auth.destination_google_auth, name='destination_google_auth'),  # Destination auth
    path('destination/auth/callback/', auth.destination_google_auth_callback, name='destination_google_auth_callback'),  # Destination callback
    # path('accounts/', include('allauth.urls')),  # Allauth authentication URLs
    
    # Logout view
    # path('logout/', views.logout_view, name='logout'),  # Logout
]
