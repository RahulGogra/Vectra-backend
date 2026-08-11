from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Workspace, WorkspaceMember
from .serializers import WorkspaceSerializer, WorkspaceMemberSerializer
from .permissions import IsWorkspaceOwner, IsWorkspaceAdminOrOwner

class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'destroy':
            # Only owners can delete the entire workspace
            permission_classes = [IsAuthenticated, IsWorkspaceOwner]
        elif self.action in ['update', 'partial_update']:
            # Admins and Owners can update workspace settings (name, etc.)
            permission_classes = [IsAuthenticated, IsWorkspaceAdminOrOwner]
        else:
            # Everyone logged in can list, retrieve, or create
            permission_classes = [IsAuthenticated]
            
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Filter workspaces to only those where the requesting user is a member
        return Workspace.objects.filter(members__user=self.request.user)

    def perform_create(self, serializer):
        # Save the new workspace
        workspace = serializer.save()
        
        # Automatically make the creator the owner
        WorkspaceMember.objects.create(
            workspace=workspace, 
            user=self.request.user, 
            role='owner'
        )

class WorkspaceMemberViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only show members for workspaces the current user belongs to
        return WorkspaceMember.objects.filter(workspace__members__user=self.request.user)