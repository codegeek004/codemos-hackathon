from django.db import models
from django.utils.timezone import now

class MigrationStatus(models.Model):
	user = models.ForeignKey('gmailapp.CustomUser', on_delete=models.CASCADE) 
	task_id = models.CharField(max_length=200, unique=True)
	status = models.CharField(max_length=40, default="PENDING")
	result = models.TextField(null=True, blank=True)
	migrated_count = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

class DestinationToken(models.Model):
    user = models.ForeignKey('gmailapp.CustomUser', on_delete=models.CASCADE)
    token = models.TextField()
    refresh_token = models.TextField()
    token_uri = models.TextField()
    client_id = models.TextField()
    client_secret = models.TextField()
    scopes = models.TextField()
    expiry = models.DateTimeField(default=now(), null=True, blank=True)
