import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from workspaces.permissions import IsWorkspaceAdminOrOwner
from workspaces.models import Workspace, WorkspaceMember
from django.db.models import Q
from django.db import transaction
from .models import Task
from .serializers import TaskSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            permission_classes = [IsAuthenticated, IsWorkspaceAdminOrOwner]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        base_qs = Task.objects.filter(project__workspace__members__user=user)

        # Workspaces where user is admin or owner
        admin_workspaces = Workspace.objects.filter(members__user=user, members__role__in=['owner', 'admin'])

        # Filter: User must be Admin/Owner of the workspace, OR the task assignee, OR the task creator
        return base_qs.filter(
            Q(project__workspace__in=admin_workspaces) | 
            Q(assignee=user) | 
            Q(created_by=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # Add this custom endpoint
    @action(detail=False, methods=['post'], url_path='update-board')
    def update_board(self, request):
        """
        Accepts an array of task objects with their new status and order.
        Example payload:
        [
            {"id": "uuid-1", "status": "in_progress", "order": 0},
            {"id": "uuid-2", "status": "in_progress", "order": 1}
        ]
        """
        tasks_data = request.data
        
        if not isinstance(tasks_data, list):
            return Response({"error": "Expected a list of tasks."}, status=status.HTTP_400_BAD_REQUEST)

        # Extract IDs to fetch them all at once (better performance)
        task_ids = [item.get('id') for item in tasks_data if item.get('id')]
        
        # Fetch only tasks the user is allowed to modify
        existing_tasks = Task.objects.filter(
            id__in=task_ids, 
            project__workspace__members__user=request.user
        ).in_bulk()

        tasks_to_update = []

        for item in tasks_data:
            task = existing_tasks.get(uuid.UUID(item['id'])) # Ensure UUID matching
            if task:
                task.status = item.get('status', task.status)
                task.order = item.get('order', task.order)
                tasks_to_update.append(task)

        # Perform an atomic bulk update
        with transaction.atomic():
            Task.objects.bulk_update(tasks_to_update, ['status', 'order'])

        return Response({"message": "Board updated successfully."}, status=status.HTTP_200_OK)

    # Add filtering capabilities
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Allow frontend to query like: /api/tasks/?project=<id>&status=todo
    filterset_fields = ['project', 'status', 'priority', 'assignee']
    
    # Allow frontend to search like: /api/tasks/?search=bug
    search_fields = ['title', 'description']
    
    # Allow frontend to order like: /api/tasks/?ordering=-created_at
    ordering_fields = ['created_at', 'due_date', 'order']