from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import MigrationRecord
from .serializers import MigrationRecordSerializer

@api_view(['POST'])
def log_migration(request):
    data = request.data
    migration = MigrationRecord.objects.create(
        user=request.user,
        google_email=data["google_email"],
        total_photos=data["total_photos"],
        status="pending"
    )
    return Response({"message": "Migration logged", "id": migration.id})

@api_view(['GET'])
def get_migrations(request):
    migrations = MigrationRecord.objects.filter(user=request.user)
    serializer = MigrationRecordSerializer(migrations, many=True)
    return Response(serializer.data)

