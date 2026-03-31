import * as React from 'react';
import { cn } from '@/lib/utils';

type LoanStatus = 'active' | 'pending' | 'approved' | 'paid' | 'defaulted' | 'rejected' | 'completed' | 'written_off' | string;

const statusConfig: Record<string, { label: string; className: string }> = {
  active:     { label: 'Activo',      className: 'bg-green-50 text-green-700 border-green-200' },
  pending:    { label: 'Pendiente',   className: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  approved:   { label: 'Aprobado',   className: 'bg-blue-50 text-blue-700 border-blue-200' },
  paid:       { label: 'Pagado',      className: 'bg-[#f0f3ec] text-[#163300] border-[#c5d1b8]' },
  defaulted:  { label: 'Mora',        className: 'bg-red-50 text-red-700 border-red-200' },
  rejected:   { label: 'Rechazado',  className: 'bg-red-50 text-red-700 border-red-200' },
  completed:  { label: 'Completado', className: 'bg-green-50 text-green-700 border-green-200' },
  written_off:{ label: 'Castigado',  className: 'bg-gray-50 text-gray-600 border-gray-200' },
};

interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: LoanStatus;
  customLabel?: string;
}

export function StatusBadge({ status, customLabel, className, ...props }: StatusBadgeProps) {
  const config = statusConfig[status] ?? { label: status, className: 'bg-gray-50 text-gray-600 border-gray-200' };
  const label = customLabel ?? config.label;

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border',
        config.className,
        className
      )}
      {...props}
    >
      {label}
    </span>
  );
}
