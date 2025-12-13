import { apiClient } from './client';
import {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskMove,
  TasksByStatus,
  TaskStatistics,
  PaginatedResponse,
} from '@/types';

export interface TaskListParams {
  page?: number;
  status?: string;
  priority?: string;
  assignee?: string;
  search?: string;
  tag?: string;
  overdue?: boolean;
  ordering?: string;
}

export const tasksAPI = {
  /**
   * Get paginated list of tasks
   */
  async getTasks(params?: TaskListParams): Promise<PaginatedResponse<Task>> {
    const searchParams = new URLSearchParams();

    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.status) searchParams.append('status', params.status);
    if (params?.priority) searchParams.append('priority', params.priority);
    if (params?.assignee) searchParams.append('assignee', params.assignee);
    if (params?.search) searchParams.append('search', params.search);
    if (params?.tag) searchParams.append('tag', params.tag);
    if (params?.overdue) searchParams.append('overdue', 'true');
    if (params?.ordering) searchParams.append('ordering', params.ordering);

    const queryString = searchParams.toString();
    const url = queryString
      ? `/api/communications/tasks/?${queryString}`
      : '/api/communications/tasks/';

    return apiClient.get<PaginatedResponse<Task>>(url);
  },

  /**
   * Get a single task by ID
   */
  async getTask(id: string): Promise<Task> {
    return apiClient.get<Task>(`/api/communications/tasks/${id}/`);
  },

  /**
   * Create a new task
   */
  async createTask(data: TaskCreate): Promise<Task> {
    return apiClient.post<Task>('/api/communications/tasks/', data);
  },

  /**
   * Update an existing task
   */
  async updateTask(id: string, data: TaskUpdate): Promise<Task> {
    return apiClient.patch<Task>(`/api/communications/tasks/${id}/`, data);
  },

  /**
   * Delete a task
   */
  async deleteTask(id: string): Promise<void> {
    return apiClient.delete(`/api/communications/tasks/${id}/`);
  },

  /**
   * Move a task to another status/column
   */
  async moveTask(id: string, data: TaskMove): Promise<{ message: string; task: Task }> {
    return apiClient.post<{ message: string; task: Task }>(
      `/api/communications/tasks/${id}/move/`,
      data
    );
  },

  /**
   * Reorder multiple tasks
   */
  async reorderTasks(
    tasks: { id: string; position: number }[]
  ): Promise<{ message: string; updated_count: number }> {
    return apiClient.post<{ message: string; updated_count: number }>(
      '/api/communications/tasks/reorder/',
      { tasks }
    );
  },

  /**
   * Get tasks grouped by status (for Kanban board)
   */
  async getTasksByStatus(): Promise<TasksByStatus> {
    return apiClient.get<TasksByStatus>('/api/communications/tasks/by_status/');
  },

  /**
   * Get task statistics
   */
  async getStatistics(): Promise<TaskStatistics> {
    return apiClient.get<TaskStatistics>('/api/communications/tasks/statistics/');
  },
};
