'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useTasks } from '@/hooks/useTasks';
import { useTeam } from '@/hooks/useTeam';
import { customersAPI } from '@/lib/api/customers';
import { Task, TaskCreate, TaskStatus, TaskPriority, Customer } from '@/types';
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  CheckSquare,
  Plus,
  GripVertical,
  Calendar,
  User,
  Tag,
  Trash2,
  Edit,
  Loader2,
  Search,
  Filter,
  AlertCircle,
  Phone,
  Mail,
  UserCircle,
} from 'lucide-react';

const columns: { id: TaskStatus; title: string; color: string }[] = [
  { id: 'todo', title: 'Por Hacer', color: 'bg-gray-500' },
  { id: 'in_progress', title: 'En Progreso', color: 'bg-blue-500' },
  { id: 'review', title: 'En Revisión', color: 'bg-yellow-500' },
  { id: 'done', title: 'Completado', color: 'bg-green-500' },
];

const priorityColors: Record<TaskPriority, string> = {
  low: 'bg-gray-500',
  medium: 'bg-yellow-500',
  high: 'bg-red-500',
};

const priorityLabels: Record<TaskPriority, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
};

// Sortable Task Card Component
function SortableTaskCard({
  task,
  onEdit,
  onDelete,
}: {
  task: Task;
  onEdit: (task: Task) => void;
  onDelete: (id: string) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className={`border-slate-200 hover:shadow-md transition-shadow ${
        isDragging ? 'shadow-lg' : ''
      }`}
    >
      <CardHeader className="p-4 pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <div
                {...attributes}
                {...listeners}
                className="cursor-grab active:cursor-grabbing"
              >
                <GripVertical className="h-4 w-4 text-gray-400" />
              </div>
              <Badge className={`${priorityColors[task.priority]} text-white text-xs`}>
                {priorityLabels[task.priority]}
              </Badge>
              {task.is_overdue && (
                <Badge variant="destructive" className="text-xs">
                  Vencida
                </Badge>
              )}
            </div>
            <CardTitle className="text-sm font-semibold">{task.title}</CardTitle>
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => onEdit(task)}
            >
              <Edit className="h-3 w-3 text-gray-500" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => onDelete(task.id)}
            >
              <Trash2 className="h-3 w-3 text-gray-500" />
            </Button>
          </div>
        </div>
        {task.description && (
          <CardDescription className="text-xs mt-2 line-clamp-2">
            {task.description}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="p-4 pt-2">
        <div className="space-y-2">
          {task.assignee_name && (
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <User className="h-3 w-3" />
              <span>{task.assignee_name}</span>
            </div>
          )}
          {task.customer_info && (
            <div className="bg-blue-50 rounded p-2 space-y-1">
              <div className="flex items-center gap-2 text-xs text-blue-700 font-medium">
                <UserCircle className="h-3 w-3" />
                <span>{task.customer_info.full_name}</span>
              </div>
              {task.customer_info.phone && (
                <div className="flex items-center gap-2 text-xs text-blue-600">
                  <Phone className="h-3 w-3" />
                  <a href={`tel:${task.customer_info.phone}`} className="hover:underline">
                    {task.customer_info.phone}
                  </a>
                </div>
              )}
              {task.customer_info.email && (
                <div className="flex items-center gap-2 text-xs text-blue-600">
                  <Mail className="h-3 w-3" />
                  <a href={`mailto:${task.customer_info.email}`} className="hover:underline truncate">
                    {task.customer_info.email}
                  </a>
                </div>
              )}
            </div>
          )}
          {task.due_date && (
            <div
              className={`flex items-center gap-2 text-xs ${
                task.is_overdue ? 'text-red-600 font-medium' : 'text-gray-600'
              }`}
            >
              <Calendar className="h-3 w-3" />
              <span>{new Date(task.due_date).toLocaleDateString('es-ES')}</span>
            </div>
          )}
          {task.tags.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              <Tag className="h-3 w-3 text-gray-400" />
              {task.tags.slice(0, 3).map((tag, index) => (
                <Badge key={index} variant="outline" className="text-xs px-2 py-0">
                  {tag}
                </Badge>
              ))}
              {task.tags.length > 3 && (
                <Badge variant="outline" className="text-xs px-2 py-0">
                  +{task.tags.length - 3}
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Task Card for Drag Overlay
function TaskCardOverlay({ task }: { task: Task }) {
  return (
    <Card className="border-slate-200 shadow-xl rotate-3 w-[280px]">
      <CardHeader className="p-4 pb-2">
        <div className="flex items-center gap-2 mb-2">
          <GripVertical className="h-4 w-4 text-gray-400" />
          <Badge className={`${priorityColors[task.priority]} text-white text-xs`}>
            {priorityLabels[task.priority]}
          </Badge>
        </div>
        <CardTitle className="text-sm font-semibold">{task.title}</CardTitle>
      </CardHeader>
    </Card>
  );
}

// Column Component
function Column({
  column,
  tasks,
  onEditTask,
  onDeleteTask,
}: {
  column: { id: TaskStatus; title: string; color: string };
  tasks: Task[];
  onEditTask: (task: Task) => void;
  onDeleteTask: (id: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  return (
    <div className="flex flex-col min-w-[300px] w-[300px]">
      <div className={`${column.color} text-white px-4 py-3 rounded-t-lg`}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{column.title}</h3>
          <Badge variant="secondary" className="bg-white/20 text-white">
            {tasks.length}
          </Badge>
        </div>
      </div>
      <div
        ref={setNodeRef}
        className={`bg-gray-50 border border-t-0 border-gray-200 rounded-b-lg p-3 min-h-[500px] space-y-3 overflow-y-auto transition-colors ${
          isOver ? 'bg-blue-50 border-blue-300' : ''
        }`}
        style={{ maxHeight: 'calc(100vh - 280px)' }}
      >
        <SortableContext
          items={tasks.map((t) => t.id)}
          strategy={verticalListSortingStrategy}
        >
          {tasks.map((task) => (
            <SortableTaskCard
              key={task.id}
              task={task}
              onEdit={onEditTask}
              onDelete={onDeleteTask}
            />
          ))}
        </SortableContext>
        {tasks.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            Arrastra tareas aquí
          </div>
        )}
      </div>
    </div>
  );
}

export default function TasksPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const {
    tasksByStatus,
    statistics,
    isLoadingByStatus,
    createTask,
    isCreating,
    updateTask,
    isUpdating,
    deleteTask,
    moveTask,
    refetchByStatus,
  } = useTasks();
  const { teamMembers } = useTeam();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [error, setError] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  const [formData, setFormData] = useState<TaskCreate>({
    title: '',
    description: '',
    priority: 'medium',
    assignee: undefined,
    customer: undefined,
    due_date: undefined,
    tags: [],
  });
  const [tagsInput, setTagsInput] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoadingCustomers, setIsLoadingCustomers] = useState(false);
  const [customerSearch, setCustomerSearch] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Fetch customers when dialog opens
  useEffect(() => {
    const fetchCustomers = async () => {
      if (!isDialogOpen) return;

      setIsLoadingCustomers(true);
      try {
        const response = await customersAPI.getCustomers({ page_size: 100 });
        setCustomers(response.results || []);
      } catch (err) {
        console.error('Error fetching customers:', err);
      } finally {
        setIsLoadingCustomers(false);
      }
    };

    fetchCustomers();
  }, [isDialogOpen]);

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      priority: 'medium',
      assignee: undefined,
      customer: undefined,
      due_date: undefined,
      tags: [],
    });
    setTagsInput('');
    setCustomerSearch('');
    setEditingTask(null);
  };

  const handleOpenDialog = (task?: Task) => {
    if (task) {
      setEditingTask(task);
      setFormData({
        title: task.title,
        description: task.description,
        priority: task.priority,
        assignee: task.assignee || undefined,
        customer: task.customer || undefined,
        due_date: task.due_date || undefined,
        tags: task.tags,
      });
      setTagsInput(task.tags.join(', '));
      setCustomerSearch(task.customer_name || '');
    } else {
      resetForm();
    }
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    resetForm();
  };

  const handleSubmit = async () => {
    if (!formData.title.trim()) {
      setError('El título es requerido');
      return;
    }

    try {
      setError('');
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      const data = {
        ...formData,
        tags,
        assignee: formData.assignee || undefined,
        customer: formData.customer || undefined,
        due_date: formData.due_date || undefined,
      };

      if (editingTask) {
        await updateTask({ id: editingTask.id, data });
      } else {
        await createTask(data);
      }

      handleCloseDialog();
      refetchByStatus();
    } catch (err: any) {
      setError(err.message || 'Error al guardar la tarea');
    }
  };

  const handleDeleteTask = async (id: string) => {
    if (!confirm('¿Estás seguro de eliminar esta tarea?')) return;

    try {
      await deleteTask(id);
      refetchByStatus();
    } catch (err: any) {
      setError(err.message || 'Error al eliminar la tarea');
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const task = findTaskById(active.id as string);
    setActiveTask(task || null);
  };

  const handleDragOver = (event: DragOverEvent) => {
    // Handle drag over for visual feedback (optional)
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Find the task and determine target column
    const task = findTaskById(activeId);
    if (!task) return;

    // Determine target status
    let targetStatus: TaskStatus | null = null;

    // Check if dropped on a column
    if (columns.some((col) => col.id === overId)) {
      targetStatus = overId as TaskStatus;
    } else {
      // Dropped on another task, find its column
      const overTask = findTaskById(overId);
      if (overTask) {
        targetStatus = overTask.status;
      }
    }

    if (!targetStatus || task.status === targetStatus) return;

    // Move task to new column
    try {
      await moveTask({
        id: activeId,
        data: { status: targetStatus, position: 0 },
      });
    } catch (err: any) {
      setError(err.message || 'Error al mover la tarea');
      refetchByStatus();
    }
  };

  const findTaskById = (id: string): Task | undefined => {
    if (!tasksByStatus) return undefined;
    for (const status of Object.keys(tasksByStatus) as TaskStatus[]) {
      const task = tasksByStatus[status].find((t) => t.id === id);
      if (task) return task;
    }
    return undefined;
  };

  // Filter tasks
  const filterTasks = (tasks: Task[]): Task[] => {
    return tasks.filter((task) => {
      const matchesSearch =
        !searchTerm ||
        task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.tags.some((tag) => tag.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchesPriority =
        priorityFilter === 'all' || task.priority === priorityFilter;

      return matchesSearch && matchesPriority;
    });
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-full">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="h-6 w-6 text-blue-600" />
              Tareas
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Gestiona tus tareas con un tablero Kanban
              {statistics && (
                <span className="ml-2 text-slate-500">
                  ({statistics.total} total, {statistics.overdue} vencidas)
                </span>
              )}
            </p>
          </div>
          <Button
            className="bg-blue-600 hover:bg-blue-700"
            onClick={() => handleOpenDialog()}
          >
            <Plus className="h-4 w-4 mr-2" />
            Nueva Tarea
          </Button>
        </div>

        {/* Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar tareas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-[180px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Prioridad" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las prioridades</SelectItem>
              <SelectItem value="high">Alta</SelectItem>
              <SelectItem value="medium">Media</SelectItem>
              <SelectItem value="low">Baja</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Kanban Board */}
        {isLoadingByStatus ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-2 text-slate-600">Cargando tareas...</span>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
          >
            <div className="flex gap-4 overflow-x-auto pb-4">
              {columns.map((column) => (
                <Column
                  key={column.id}
                  column={column}
                  tasks={filterTasks(tasksByStatus?.[column.id] || [])}
                  onEditTask={handleOpenDialog}
                  onDeleteTask={handleDeleteTask}
                />
              ))}
            </div>
            <DragOverlay>
              {activeTask && <TaskCardOverlay task={activeTask} />}
            </DragOverlay>
          </DndContext>
        )}

        {/* Task Dialog */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>
                {editingTask ? 'Editar Tarea' : 'Nueva Tarea'}
              </DialogTitle>
              <DialogDescription>
                {editingTask
                  ? 'Modifica los detalles de la tarea'
                  : 'Crea una nueva tarea para el tablero'}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="title">Título *</Label>
                <Input
                  id="title"
                  placeholder="Título de la tarea"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Descripción</Label>
                <Textarea
                  id="description"
                  placeholder="Descripción de la tarea"
                  rows={3}
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="priority">Prioridad</Label>
                  <Select
                    value={formData.priority}
                    onValueChange={(value: TaskPriority) =>
                      setFormData({ ...formData, priority: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Baja</SelectItem>
                      <SelectItem value="medium">Media</SelectItem>
                      <SelectItem value="high">Alta</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dueDate">Fecha Límite</Label>
                  <Input
                    id="dueDate"
                    type="date"
                    value={formData.due_date || ''}
                    onChange={(e) =>
                      setFormData({ ...formData, due_date: e.target.value || undefined })
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="assignee">Asignado a</Label>
                <Select
                  value={formData.assignee || 'none'}
                  onValueChange={(value) =>
                    setFormData({
                      ...formData,
                      assignee: value === 'none' ? undefined : value,
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar usuario" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin asignar</SelectItem>
                    {Array.isArray(teamMembers)
                      ? teamMembers.map((member) => (
                          <SelectItem key={member.id} value={member.id.toString()}>
                            {member.full_name || member.email}
                          </SelectItem>
                        ))
                      : (teamMembers as any)?.results?.map((member: any) => (
                          <SelectItem key={member.id} value={member.id.toString()}>
                            {member.full_name || member.email}
                          </SelectItem>
                        ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="customer">Cliente/Contacto</Label>
                <Select
                  value={formData.customer || 'none'}
                  onValueChange={(value) =>
                    setFormData({
                      ...formData,
                      customer: value === 'none' ? undefined : value,
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingCustomers ? 'Cargando...' : 'Seleccionar cliente'} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin cliente asociado</SelectItem>
                    {customers.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        <div className="flex flex-col">
                          <span>{customer.full_name}</span>
                          <span className="text-xs text-gray-500">{customer.phone} • {customer.email}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {formData.customer && (
                  <div className="bg-blue-50 rounded-md p-3 mt-2 text-sm">
                    {(() => {
                      const selectedCustomer = customers.find(c => c.id === formData.customer);
                      if (!selectedCustomer) return null;
                      return (
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 font-medium text-blue-700">
                            <UserCircle className="h-4 w-4" />
                            {selectedCustomer.full_name}
                          </div>
                          {selectedCustomer.phone && (
                            <div className="flex items-center gap-2 text-blue-600">
                              <Phone className="h-3 w-3" />
                              <a href={`tel:${selectedCustomer.phone}`} className="hover:underline">
                                {selectedCustomer.phone}
                              </a>
                            </div>
                          )}
                          {selectedCustomer.email && (
                            <div className="flex items-center gap-2 text-blue-600">
                              <Mail className="h-3 w-3" />
                              <a href={`mailto:${selectedCustomer.email}`} className="hover:underline">
                                {selectedCustomer.email}
                              </a>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="tags">Tags (separados por coma)</Label>
                <Input
                  id="tags"
                  placeholder="backend, api, urgente"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={handleCloseDialog}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} disabled={isCreating || isUpdating}>
                {isCreating || isUpdating ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                {editingTask ? 'Guardar Cambios' : 'Crear Tarea'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
