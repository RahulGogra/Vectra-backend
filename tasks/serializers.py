from rest_framework import serializers
from .models import Task
from users.serializers import UserSerializer

class TaskSerializer(serializers.ModelSerializer):
    # Include basic assignee info for the frontend UI
    assignee_details = UserSerializer(source='assignee', read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['created_by']