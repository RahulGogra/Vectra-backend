from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Workspace, WorkspaceMember
from .serializers import WorkspaceSerializer, WorkspaceMemberSerializer
from .permissions import IsWorkspaceOwner, IsWorkspaceAdminOrOwner
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend

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
        user = self.request.user
        # Check if user is on free plan and already owns a workspace
        if user.plan == 'free':
            owned_workspaces = WorkspaceMember.objects.filter(user=user, role='owner').count()
            if owned_workspaces >= 1:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Free users can only create one workspace. Please upgrade to Pro to create more.")

        # Save the new workspace
        workspace = serializer.save()
        
        # Automatically make the creator the owner
        WorkspaceMember.objects.create(
            workspace=workspace, 
            user=user, 
            role='owner'
        )

    @action(detail=True, methods=['post'], url_path='invite')
    def invite_member(self, request, pk=None):
        """Send an invitation to an existing user by email"""
        workspace = self.get_object()
        email = request.data.get('email')
        
        # Verify the requester is an Admin or Owner
        if not WorkspaceMember.objects.filter(workspace=workspace, user=request.user, role__in=['owner', 'admin']).exists():
            return Response({"error": "Not authorized to invite members."}, status=status.HTTP_403_FORBIDDEN)

        User = get_user_model()
        try:
            target_user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found. They must sign up first."}, status=status.HTTP_404_NOT_FOUND)

        # Check if they are already in the workspace
        if WorkspaceMember.objects.filter(workspace=workspace, user=target_user).exists():
            return Response({"error": "User is already in this workspace or has a pending invite."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the pending member (hardcoded to 'member' role as requested)
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=target_user,
            role='member',
            status='pending'
        )
        
        # Dispatch Real-Time Notification
        from notifications.models import Notification
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        notification = Notification.objects.create(
            user=target_user,
            title="Workspace Invitation",
            message=f"{request.user.first_name or request.user.email} invited you to join '{workspace.name}'.",
            type="invite"
        )
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{target_user.id}",
            {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.type,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat()
                }
            }
        )

        return Response({"message": "Invitation sent successfully."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='accept-invite')
    def accept_invite(self, request, pk=None):
        """User accepts a pending invitation"""
        workspace = self.get_object()
        try:
            member_record = WorkspaceMember.objects.get(workspace=workspace, user=request.user, status='pending')
            member_record.status = 'active'
            member_record.save()
            return Response({"message": "Invitation accepted."})
        except WorkspaceMember.DoesNotExist:
            return Response({"error": "No pending invitation found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='decline-invite')
    def decline_invite(self, request, pk=None):
        """User declines an invitation"""
        workspace = self.get_object()
        try:
            member_record = WorkspaceMember.objects.get(workspace=workspace, user=request.user, status='pending')
            member_record.delete()
            return Response({"message": "Invitation declined."})
        except WorkspaceMember.DoesNotExist:
            return Response({"error": "No pending invitation found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='invites')
    def my_invites(self, request):
        """Get all pending workspace invitations for the current user"""
        pending_memberships = WorkspaceMember.objects.filter(user=request.user, status='pending')
        
        # Return a simple list of invites with the workspace name
        invites = [
            {
                "workspace_id": m.workspace.id,
                "workspace_name": m.workspace.name,
                "role": m.role,
                "joined_at": m.joined_at
            }
            for m in pending_memberships
        ]
        return Response(invites)

class WorkspaceMemberViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceMemberSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['workspace']

    def get_queryset(self):
        # Only show members for workspaces the current user belongs to
        return WorkspaceMember.objects.filter(workspace__members__user=self.request.user)