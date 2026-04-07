import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksAPI, TaskListParams } from '@/lib/api/tasks';
import { Task, TaskCreate, TaskUpdate, TaskMove, TasksByStatus } from '@/types';

export function useTasks(params?: TaskListParams) {
  const queryClient = useQueryClient();

  // Query: Get paginated tasks
  const {
    data: tasksResponse,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['tasks', params],
    queryFn: () => tasksAPI.getTasks(params),
    staleTime: 30 * 1000, // 30 seconds
  });

  // Query: Get tasks grouped by status (for Kanban)
  const {
    data: tasksByStatus,
    isLoading: isLoadingByStatus,
    refetch: refetchByStatus,
  } = useQuery({
    queryKey: ['tasks', 'by_status'],
    queryFn: () => tasksAPI.getTasksByStatus(),
    staleTime: 30 * 1000,
  });

  // Query: Get task statistics
  const { data: statistics, refetch: refetchStatistics } = useQuery({
    queryKey: ['tasks', 'statistics'],
    queryFn: () => tasksAPI.getStatistics(),
    staleTime: 60 * 1000, // 1 minute
  });

  // Mutation: Create task
  const createTaskMutation = useMutation({
    mutationFn: (data: TaskCreate) => tasksAPI.createTask(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Mutation: Update task
  const updateTaskMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaskUpdate }) =>
      tasksAPI.updateTask(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Mutation: Delete task
  const deleteTaskMutation = useMutation({
    mutationFn: (id: string) => tasksAPI.deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Mutation: Move task (optimistic update for smooth UX)
  const moveTaskMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaskMove }) =>
      tasksAPI.moveTask(id, data),
    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['tasks', 'by_status'] });

      // Snapshot previous value
      const previousTasksByStatus = queryClient.getQueryData<TasksByStatus>([
        'tasks',
        'by_status',
      ]);

      // Optimistically update
      if (previousTasksByStatus) {
        const newTasksByStatus = { ...previousTasksByStatus };
        let movedTask: Task | undefined;

        // Find and remove task from current column
        for (const status of Object.keys(newTasksByStatus) as Array<keyof TasksByStatus>) {
          const index = newTasksByStatus[status].findIndex((t) => t.id === id);
          if (index !== -1) {
            [movedTask] = newTasksByStatus[status].splice(index, 1);
            break;
          }
        }

        // Add task to new column
        if (movedTask) {
          movedTask.status = data.status;
          movedTask.position = data.position ?? 0;
          newTasksByStatus[data.status].splice(data.position ?? 0, 0, movedTask);
        }

        queryClient.setQueryData(['tasks', 'by_status'], newTasksByStatus);
      }

      return { previousTasksByStatus };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousTasksByStatus) {
        queryClient.setQueryData(['tasks', 'by_status'], context.previousTasksByStatus);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Mutation: Reorder tasks
  const reorderTasksMutation = useMutation({
    mutationFn: (tasks: { id: string; position: number }[]) =>
      tasksAPI.reorderTasks(tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  return {
    // Data
    tasks: tasksResponse?.results ?? [],
    totalCount: tasksResponse?.count ?? 0,
    tasksByStatus,
    statistics,

    // Loading states
    isLoading,
    isLoadingByStatus,
    error,

    // Refetch functions
    refetch,
    refetchByStatus,
    refetchStatistics,

    // Create
    createTask: createTaskMutation.mutateAsync,
    isCreating: createTaskMutation.isPending,
    createError: createTaskMutation.error,

    // Update
    updateTask: updateTaskMutation.mutateAsync,
    isUpdating: updateTaskMutation.isPending,
    updateError: updateTaskMutation.error,

    // Delete
    deleteTask: deleteTaskMutation.mutateAsync,
    isDeleting: deleteTaskMutation.isPending,
    deleteError: deleteTaskMutation.error,

    // Move
    moveTask: moveTaskMutation.mutateAsync,
    isMoving: moveTaskMutation.isPending,
    moveError: moveTaskMutation.error,

    // Reorder
    reorderTasks: reorderTasksMutation.mutateAsync,
    isReordering: reorderTasksMutation.isPending,
  };
}
