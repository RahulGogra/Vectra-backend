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
        # If it's a Workspace object, use it directly. If it's a Project/Task, get its workspace.
        workspace = obj if hasattr(obj, 'slug') else obj.workspace
        
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
            
        workspace = obj if hasattr(obj, 'slug') else obj.workspace
        
        return WorkspaceMember.objects.filter(
            workspace=workspace, 
            user=request.user, 
            role__in=['owner', 'admin']
        ).exists()