from rest_framework import permissions
from .models import WorkspaceMember

class IsWorkspaceOwner(permissions.BasePermission):
    """
    Object-level permission to strictly allow only workspace owners to perform an action.
    """
    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS are GET, HEAD, OPTIONS (read-only). We let the queryset filtering handle these.
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Determine the workspace based on the object type
        # If it's a Workspace object, use it directly. If it's a Task, get its project's workspace. Otherwise, assume it has a workspace attribute (Project, WorkspaceMember).
        if hasattr(obj, 'slug'):
            workspace = obj
        elif hasattr(obj, 'project'):
            workspace = obj.project.workspace
        else:
            workspace = obj.workspace
        
        return WorkspaceMember.objects.filter(
            workspace=workspace, 
            user=request.user, 
            role='owner'
        ).exists()

class IsWorkspaceAdminOrOwner(permissions.BasePermission):
    """
    Object-level permission to allow both admins and owners to perform an action.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
            
        if hasattr(obj, 'slug'):
            workspace = obj
        elif hasattr(obj, 'project'):
            workspace = obj.project.workspace
        else:
            workspace = obj.workspace
        
        return WorkspaceMember.objects.filter(
            workspace=workspace, 
            user=request.user, 
            role__in=['owner', 'admin']
        ).exists()