from django.urls import include, path
from photos import views

urlpatterns = [
    # Home page (optional, can be added later)
    # path('', views.home, name='home'),  
    
    # Photo migration related URLs
    path('migrate/', views.migrate_photos, name='migrate_photos'),  # Migrate photos
    
    # Google authentication for source and destination accounts
     # Include allauth URLs (handles Google OAuth automatically)
    path('accounts/', include('allauth.urls')),  # Allauth authentication URLs
    
    # Logout view
    # path('logout/', views.logout_view, name='logout'),  # Logout
]
