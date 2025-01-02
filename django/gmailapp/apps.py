from django.apps import AppConfig


class GmailappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gmailapp'
def ready(self):
        # import gmailapp.signals
        print('gmail app is ready')