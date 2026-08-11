from rest_framework import serializers
from .models import Workspace, WorkspaceMember
from users.serializers import UserSerializer

class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        # We exclude stripe_customer_id as the frontend doesn't need to see it
        fields = ['id', 'name', 'slug', 'created_at', 'updated_at']

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    # This nests the User JSON inside the Member JSON automatically
    user = UserSerializer(read_only=True) 

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'workspace', 'user', 'role', 'joined_at']