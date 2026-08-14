from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.views import RegisterView
from users.serializers import UserSerializer
from workspaces.views import WorkspaceViewSet, WorkspaceMemberViewSet
from projects.views import ProjectViewSet
from tasks.views import TaskViewSet

class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


router = DefaultRouter()
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')
router.register(r'workspace-members', WorkspaceMemberViewSet, basename='workspacemember')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/me/', MeView.as_view(), name='me'),
    path('api/', include(router.urls)),
    path('api/payments/', include('payments.urls')),
    path('api/notifications/', include('notifications.urls')),
]