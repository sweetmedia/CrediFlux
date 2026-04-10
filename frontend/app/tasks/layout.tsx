import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Tareas',
  description: 'Tablero de tareas del equipo',
}

export default function TasksLayout({ children }: { children: React.ReactNode }) {
  return children
}
