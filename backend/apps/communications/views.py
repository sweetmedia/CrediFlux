"""
API Views for Communications app - Tasks
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Task
from .serializers import (
    TaskListSerializer,
    TaskSerializer,
    TaskCreateSerializer,
    TaskMoveSerializer,
    TaskReorderSerializer,
)


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Tasks (Kanban board)

    Provides CRUD operations plus custom actions for:
    - Moving tasks between columns
    - Reordering tasks within columns
    - Getting tasks by status
    """
    queryset = Task.objects.select_related('assignee', 'created_by', 'customer').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'assignee', 'customer']
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'priority', 'position']
    ordering = ['position', '-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TaskListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TaskCreateSerializer
        elif self.action == 'move':
            return TaskMoveSerializer
        elif self.action == 'reorder':
            return TaskReorderSerializer
        return TaskSerializer

    def get_queryset(self):
        """
        Filter queryset based on query params.
        Tasks are automatically tenant-isolated by django-tenants.
        """
        queryset = super().get_queryset()

        # Filter by multiple statuses (for board view)
        statuses = self.request.query_params.get('statuses')
        if statuses:
            status_list = statuses.split(',')
            queryset = queryset.filter(status__in=status_list)

        # Filter by tags
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        # Filter overdue tasks
        overdue = self.request.query_params.get('overdue')
        if overdue == 'true':
            from datetime import date
            queryset = queryset.filter(
                due_date__lt=date.today()
            ).exclude(status='done')

        return queryset

    @swagger_auto_schema(
        operation_id='list_tasks',
        operation_description='List all tasks with optional filters',
        manual_parameters=[
            openapi.Parameter(
                'status', openapi.IN_QUERY,
                description='Filter by status (todo, in_progress, review, done)',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'priority', openapi.IN_QUERY,
                description='Filter by priority (low, medium, high)',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'statuses', openapi.IN_QUERY,
                description='Filter by multiple statuses (comma-separated)',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'tag', openapi.IN_QUERY,
                description='Filter by tag',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'overdue', openapi.IN_QUERY,
                description='Filter overdue tasks only (true/false)',
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'search', openapi.IN_QUERY,
                description='Search in title, description, and tags',
                type=openapi.TYPE_STRING
            ),
        ],
        responses={200: TaskListSerializer(many=True)},
        tags=['Tasks']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id='create_task',
        operation_description='Create a new task',
        request_body=TaskCreateSerializer,
        responses={201: TaskSerializer},
        tags=['Tasks']
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id='get_task',
        operation_description='Get task details',
        responses={200: TaskSerializer},
        tags=['Tasks']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id='update_task',
        operation_description='Update a task',
        request_body=TaskCreateSerializer,
        responses={200: TaskSerializer},
        tags=['Tasks']
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id='partial_update_task',
        operation_description='Partially update a task',
        request_body=TaskCreateSerializer,
        responses={200: TaskSerializer},
        tags=['Tasks']
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id='delete_task',
        operation_description='Delete a task',
        responses={204: 'No content'},
        tags=['Tasks']
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id='move_task',
        operation_description='Move a task to another column/status',
        request_body=TaskMoveSerializer,
        responses={
            200: openapi.Response(
                description='Task moved successfully',
                examples={
                    'application/json': {
                        'message': 'Tarea movida exitosamente',
                        'task': {'id': '...', 'status': 'in_progress', 'position': 0}
                    }
                }
            )
        },
        tags=['Tasks']
    )
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """
        Move a task to another status/column.
        Optionally update its position within the column.
        """
        task = self.get_object()
        serializer = TaskMoveSerializer(data=request.data)

        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            new_position = serializer.validated_data.get('position', 0)

            # If moving to different status, update position in new column
            if task.status != new_status:
                # Shift positions of tasks in target column
                Task.objects.filter(
                    status=new_status,
                    position__gte=new_position
                ).update(position=F('position') + 1)

            task.status = new_status
            task.position = new_position
            task.save()

            return Response({
                'message': 'Tarea movida exitosamente',
                'task': TaskSerializer(task).data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_id='reorder_tasks',
        operation_description='Reorder multiple tasks (update positions)',
        request_body=TaskReorderSerializer,
        responses={
            200: openapi.Response(
                description='Tasks reordered successfully',
                examples={
                    'application/json': {
                        'message': 'Tareas reordenadas exitosamente',
                        'updated_count': 5
                    }
                }
            )
        },
        tags=['Tasks']
    )
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """
        Reorder multiple tasks at once.
        Expects a list of {id, position} objects.
        """
        serializer = TaskReorderSerializer(data=request.data)

        if serializer.is_valid():
            tasks_data = serializer.validated_data['tasks']
            updated_count = 0

            for task_data in tasks_data:
                try:
                    task = Task.objects.get(pk=task_data['id'])
                    task.position = task_data['position']
                    task.save(update_fields=['position', 'updated_at'])
                    updated_count += 1
                except Task.DoesNotExist:
                    pass  # Skip non-existent tasks

            return Response({
                'message': 'Tareas reordenadas exitosamente',
                'updated_count': updated_count
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_id='get_tasks_by_status',
        operation_description='Get tasks grouped by status (for Kanban board)',
        responses={
            200: openapi.Response(
                description='Tasks grouped by status',
                examples={
                    'application/json': {
                        'todo': [{'id': '...', 'title': '...'}],
                        'in_progress': [],
                        'review': [],
                        'done': []
                    }
                }
            )
        },
        tags=['Tasks']
    )
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """
        Get all tasks grouped by status for Kanban board view.
        """
        queryset = self.filter_queryset(self.get_queryset())

        grouped = {
            'todo': [],
            'in_progress': [],
            'review': [],
            'done': []
        }

        for task in queryset:
            if task.status in grouped:
                grouped[task.status].append(TaskListSerializer(task).data)

        return Response(grouped)

    @swagger_auto_schema(
        operation_id='get_task_statistics',
        operation_description='Get task statistics',
        responses={
            200: openapi.Response(
                description='Task statistics',
                examples={
                    'application/json': {
                        'total': 25,
                        'by_status': {'todo': 10, 'in_progress': 5, 'review': 3, 'done': 7},
                        'by_priority': {'low': 5, 'medium': 15, 'high': 5},
                        'overdue': 2
                    }
                }
            )
        },
        tags=['Tasks']
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get task statistics for dashboard.
        """
        from datetime import date
        from django.db.models import Count

        queryset = self.get_queryset()

        # Count by status
        status_counts = dict(
            queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )

        # Count by priority
        priority_counts = dict(
            queryset.values('priority').annotate(count=Count('id')).values_list('priority', 'count')
        )

        # Count overdue
        overdue_count = queryset.filter(
            due_date__lt=date.today()
        ).exclude(status='done').count()

        return Response({
            'total': queryset.count(),
            'by_status': {
                'todo': status_counts.get('todo', 0),
                'in_progress': status_counts.get('in_progress', 0),
                'review': status_counts.get('review', 0),
                'done': status_counts.get('done', 0),
            },
            'by_priority': {
                'low': priority_counts.get('low', 0),
                'medium': priority_counts.get('medium', 0),
                'high': priority_counts.get('high', 0),
            },
            'overdue': overdue_count
        })
