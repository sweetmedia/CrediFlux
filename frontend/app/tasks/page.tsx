'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
  MoreVertical,
} from 'lucide-react';

interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in-progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high';
  assignee?: string;
  dueDate?: string;
  tags: string[];
  createdAt: string;
}

const columns = [
  { id: 'todo', title: 'Por Hacer', color: 'bg-gray-500' },
  { id: 'in-progress', title: 'En Progreso', color: 'bg-blue-500' },
  { id: 'review', title: 'En Revisión', color: 'bg-yellow-500' },
  { id: 'done', title: 'Completado', color: 'bg-green-500' },
];

const priorityColors = {
  low: 'bg-gray-500',
  medium: 'bg-yellow-500',
  high: 'bg-red-500',
};

export default function TasksPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([
    {
      id: '1',
      title: 'Implementar servicio SMTP/IMAP',
      description: 'Crear servicio para enviar y recibir emails usando SMTP e IMAP',
      status: 'todo',
      priority: 'high',
      assignee: 'Juan Pérez',
      dueDate: '2025-11-10',
      tags: ['backend', 'email'],
      createdAt: new Date().toISOString(),
    },
    {
      id: '2',
      title: 'Crear endpoints API de emails',
      description: 'Endpoints para CRUD de emails, envío, recepción y sincronización',
      status: 'todo',
      priority: 'high',
      assignee: 'Juan Pérez',
      tags: ['backend', 'api', 'email'],
      createdAt: new Date().toISOString(),
    },
    {
      id: '3',
      title: 'Crear endpoints API de WhatsApp',
      description: 'Endpoints para gestionar conversaciones y mensajes de WhatsApp',
      status: 'todo',
      priority: 'medium',
      assignee: 'Juan Pérez',
      tags: ['backend', 'api', 'whatsapp'],
      createdAt: new Date().toISOString(),
    },
    {
      id: '4',
      title: 'Conectar frontend con APIs',
      description: 'Integrar el frontend de comunicaciones con las APIs del backend',
      status: 'todo',
      priority: 'medium',
      tags: ['frontend', 'integration'],
      createdAt: new Date().toISOString(),
    },
    {
      id: '5',
      title: 'Probar envío y recepción de emails',
      description: 'Testing completo del sistema de emails',
      status: 'todo',
      priority: 'low',
      tags: ['testing', 'email'],
      createdAt: new Date().toISOString(),
    },
  ]);

  const [isAddingTask, setIsAddingTask] = useState(false);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'medium' as 'low' | 'medium' | 'high',
    assignee: '',
    dueDate: '',
    tags: '',
  });

  const handleAddTask = () => {
    if (!newTask.title) return;

    const task: Task = {
      id: Date.now().toString(),
      title: newTask.title,
      description: newTask.description,
      status: 'todo',
      priority: newTask.priority,
      assignee: newTask.assignee || undefined,
      dueDate: newTask.dueDate || undefined,
      tags: newTask.tags.split(',').map(t => t.trim()).filter(Boolean),
      createdAt: new Date().toISOString(),
    };

    setTasks([...tasks, task]);
    setNewTask({
      title: '',
      description: '',
      priority: 'medium',
      assignee: '',
      dueDate: '',
      tags: '',
    });
    setIsAddingTask(false);
  };

  const handleMoveTask = (taskId: string, newStatus: Task['status']) => {
    setTasks(tasks.map(task =>
      task.id === taskId ? { ...task, status: newStatus } : task
    ));
  };

  const handleDeleteTask = (taskId: string) => {
    setTasks(tasks.filter(task => task.id !== taskId));
  };

  const getTasksByStatus = (status: Task['status']) => {
    return tasks.filter(task => task.status === status);
  };

  return (
    <div className="p-8">
      <div className="container mx-auto max-w-full">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="h-6 w-6 text-blue-600" />
              Tareas
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Gestiona tus tareas con un tablero Kanban
            </p>
          </div>
          <Dialog open={isAddingTask} onOpenChange={setIsAddingTask}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700">
                <Plus className="h-4 w-4 mr-2" />
                Nueva Tarea
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Crear Nueva Tarea</DialogTitle>
                <DialogDescription>
                  Agrega una nueva tarea al tablero
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Título *</Label>
                  <Input
                    id="title"
                    placeholder="Título de la tarea"
                    value={newTask.title}
                    onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Descripción</Label>
                  <Textarea
                    id="description"
                    placeholder="Descripción de la tarea"
                    rows={3}
                    value={newTask.description}
                    onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="priority">Prioridad</Label>
                    <Select
                      value={newTask.priority}
                      onValueChange={(value: 'low' | 'medium' | 'high') =>
                        setNewTask({ ...newTask, priority: value })
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
                      value={newTask.dueDate}
                      onChange={(e) => setNewTask({ ...newTask, dueDate: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="assignee">Asignado a</Label>
                  <Input
                    id="assignee"
                    placeholder="Nombre de la persona"
                    value={newTask.assignee}
                    onChange={(e) => setNewTask({ ...newTask, assignee: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tags">Tags (separados por coma)</Label>
                  <Input
                    id="tags"
                    placeholder="backend, api, email"
                    value={newTask.tags}
                    onChange={(e) => setNewTask({ ...newTask, tags: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setIsAddingTask(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleAddTask}>
                  Crear Tarea
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Kanban Board */}
        <div className="grid grid-cols-4 gap-4">
          {columns.map((column) => (
            <div key={column.id} className="flex flex-col">
              <div className={`${column.color} text-white px-4 py-3 rounded-t-lg`}>
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{column.title}</h3>
                  <Badge variant="secondary" className="bg-white/20 text-white">
                    {getTasksByStatus(column.id as Task['status']).length}
                  </Badge>
                </div>
              </div>
              <div className="bg-gray-50 border border-t-0 border-gray-200 rounded-b-lg p-4 min-h-[600px] space-y-3">
                {getTasksByStatus(column.id as Task['status']).map((task) => (
                  <Card key={task.id} className="border-slate-200 hover:shadow-md transition-shadow cursor-pointer">
                    <CardHeader className="p-4 pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <GripVertical className="h-4 w-4 text-gray-400" />
                            <Badge className={`${priorityColors[task.priority]} text-white text-xs`}>
                              {task.priority === 'low' ? 'Baja' : task.priority === 'medium' ? 'Media' : 'Alta'}
                            </Badge>
                          </div>
                          <CardTitle className="text-sm font-semibold">
                            {task.title}
                          </CardTitle>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() => handleDeleteTask(task.id)}
                        >
                          <Trash2 className="h-3 w-3 text-gray-500" />
                        </Button>
                      </div>
                      {task.description && (
                        <CardDescription className="text-xs mt-2">
                          {task.description}
                        </CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="p-4 pt-2">
                      <div className="space-y-2">
                        {task.assignee && (
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <User className="h-3 w-3" />
                            <span>{task.assignee}</span>
                          </div>
                        )}
                        {task.dueDate && (
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <Calendar className="h-3 w-3" />
                            <span>{new Date(task.dueDate).toLocaleDateString('es-ES')}</span>
                          </div>
                        )}
                        {task.tags.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap">
                            <Tag className="h-3 w-3 text-gray-400" />
                            {task.tags.map((tag, index) => (
                              <Badge key={index} variant="outline" className="text-xs px-2 py-0">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      {column.id !== 'done' && (
                        <div className="mt-3 pt-3 border-t">
                          <Select
                            value={task.status}
                            onValueChange={(value: Task['status']) => handleMoveTask(task.id, value)}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue placeholder="Mover a..." />
                            </SelectTrigger>
                            <SelectContent>
                              {columns
                                .filter(col => col.id !== task.status)
                                .map(col => (
                                  <SelectItem key={col.id} value={col.id}>
                                    Mover a {col.title}
                                  </SelectItem>
                                ))
                              }
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
