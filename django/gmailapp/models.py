from django.db import models
from django.contrib.auth.models import User

class GoogleToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_in = models.IntegerField()
    token_type = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.user.username}'s Google Token"
