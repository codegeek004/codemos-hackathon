from django.db import models


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


class FailedMigration(models.Model):
    task_id = models.CharField(max_length=255, db_index=True)
    user_id = models.CharField(max_length=255, default='test')
    file_id = models.CharField(max_length=255)
    file_name = models.CharField(max_length=500)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.reason}"
