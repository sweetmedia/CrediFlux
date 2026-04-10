'use client'

import { useState, type ReactNode } from 'react'
import { Search, ChevronLeft, ChevronRight } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { EmptyState } from './EmptyState'
import type { LucideIcon } from 'lucide-react'
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  isLoading?: boolean
  // Empty state
  emptyState?: {
    icon: LucideIcon
    title: string
    description?: string
    action?: { label: string; onClick: () => void }
  }
  // Search
  searchPlaceholder?: string
  searchValue?: string
  onSearchChange?: (value: string) => void
  // Pagination (server-side when onPageChange provided)
  pageCount?: number
  pageIndex?: number
  pageSize?: number
  onPageChange?: (page: number) => void
  // Toolbar
  toolbarActions?: ReactNode
  // Styling
  compact?: boolean
  className?: string
}

/**
 * Opinionated DataTable with skeleton, search, pagination, and empty state.
 *
 * Wraps the raw `@/components/ui/data-table` primitive with features that
 * most dashboard pages need. Columns can opt into tabular-nums formatting
 * via `meta: { numeric: true }` in the column definition.
 */
export function DataTable<TData, TValue>({
  columns,
  data,
  isLoading,
  emptyState,
  searchPlaceholder = 'Buscar...',
  searchValue,
  onSearchChange,
  pageCount,
  pageIndex = 0,
  pageSize = 20,
  onPageChange,
  toolbarActions,
  compact = false,
  className,
}: DataTableProps<TData, TValue>) {
  const [internalSearch, setInternalSearch] = useState('')
  const searchVal = searchValue ?? internalSearch
  const handleSearch = onSearchChange ?? setInternalSearch
  const isServerPaginated = typeof onPageChange === 'function'

  const table = useReactTable({
    data,
    columns,
    pageCount: pageCount ?? -1,
    state: isServerPaginated
      ? { pagination: { pageIndex, pageSize } }
      : undefined,
    manualPagination: isServerPaginated,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: isServerPaginated ? undefined : getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const rows = table.getRowModel().rows
  const hasRows = rows.length > 0
  const showEmpty = !isLoading && !hasRows && emptyState

  return (
    <div className={cn('space-y-3', className)}>
      {(onSearchChange || searchValue !== undefined || toolbarActions) && (
        <div className="flex items-center gap-3">
          {(onSearchChange || searchValue !== undefined) && (
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={searchPlaceholder}
                value={searchVal}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          )}
          {toolbarActions && (
            <div className="flex items-center gap-2 ml-auto">{toolbarActions}</div>
          )}
        </div>
      )}

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const meta = header.column.columnDef.meta as
                    | { numeric?: boolean }
                    | undefined
                  return (
                    <TableHead
                      key={header.id}
                      className={cn(
                        compact && 'h-9',
                        meta?.numeric && 'text-right'
                      )}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={`sk-${i}`}>
                  {columns.map((_col, j) => (
                    <TableCell key={j} className={compact ? 'py-2' : undefined}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : showEmpty ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-auto p-0">
                  <EmptyState
                    icon={emptyState.icon}
                    title={emptyState.title}
                    description={emptyState.description}
                    action={emptyState.action}
                  />
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
                >
                  {row.getVisibleCells().map((cell) => {
                    const meta = cell.column.columnDef.meta as
                      | { numeric?: boolean }
                      | undefined
                    return (
                      <TableCell
                        key={cell.id}
                        className={cn(
                          compact && 'py-2',
                          meta?.numeric && 'cf-mono-number text-right'
                        )}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    )
                  })}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {isServerPaginated && pageCount && pageCount > 1 && (
        <div className="flex items-center justify-between gap-2 px-1 text-sm text-muted-foreground">
          <span>
            Página {pageIndex + 1} de {pageCount}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(pageIndex - 1)}
              disabled={pageIndex === 0}
            >
              <ChevronLeft className="h-4 w-4" />
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(pageIndex + 1)}
              disabled={pageIndex >= (pageCount ?? 1) - 1}
            >
              Siguiente
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
