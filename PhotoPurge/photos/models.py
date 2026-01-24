from django.db import models
from django.utils.timezone import now


class MigrationStatus(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    user_id = models.CharField(max_length=255, default='test')
    status = models.CharField(max_length=50, default="PENDING")
    result = models.TextField(null=True, blank=True)
    migrated_count = models.IntegerField(default=0)
    total_count = models.IntegerField(default=0)  # Added to track total photos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_id} - {self.status}"


class PhotoMigrationProgress(models.Model):
    """
    Track individual photo migration status.
    Add this model to enable resume capability.
    """
    task_id = models.CharField(max_length=255, db_index=True)
    photo_id = models.CharField(max_length=255)
    filename = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING'
    )
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['task_id', 'photo_id']
        indexes = [
            models.Index(fields=['task_id', 'status']),
        ]

    def __str__(self):
        return f"{self.filename} - {self.status}"


class DestinationToken(models.Model):
    user = models.ForeignKey('gmailapp.CustomUser', on_delete=models.CASCADE)
    token = models.TextField()
    refresh_token = models.TextField()
    token_uri = models.TextField()
    client_id = models.TextField()
    client_secret = models.TextField()
    scopes = models.TextField()
    expires_at = models.DateTimeField(default=now(), null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
