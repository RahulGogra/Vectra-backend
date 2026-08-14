from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from workspaces.models import WorkspaceMember
from .models import Project
from .serializers import ProjectSerializer
from workspaces.permissions import IsWorkspaceAdminOrOwner
from django_filters.rest_framework import DjangoFilterBackend

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['workspace']
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            # Object-level check: Can they edit/delete this specific project?
            permission_classes = [IsAuthenticated, IsWorkspaceAdminOrOwner]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return Project.objects.filter(workspace__members__user=self.request.user)

    def perform_create(self, serializer):
        # Extract the workspace they are trying to attach the project to
        workspace = serializer.validated_data['workspace']
        
        # Verify their role in that specific workspace
        is_authorized = WorkspaceMember.objects.filter(
            workspace=workspace, 
            user=self.request.user, 
            role__in=['owner', 'admin']
        ).exists()
        
        if not is_authorized:
            raise PermissionDenied("You must be an admin or owner to create projects in this workspace.")
            
        serializer.save(created_by=self.request.user)