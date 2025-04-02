from rest_framework import serializers
from .models import MigrationRecord

class MigrationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationRecord
        fields = "__all__"

