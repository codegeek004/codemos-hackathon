from django.db import models
from django.contrib.auth.models import User
class MigrationStatus(models.Model):
	user = models.ForeignKey('gmailapp.CustomUser', on_delete=models.CASCADE) 
	task_id = models.CharField(max_length=200, unique=True)
	status = models.CharField(max_length=40, default="PENDING")
	result = models.TextField(null=True, blank=True)
	migrated_count = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

