"use client"

import * as React from "react"
import {
  ColumnDef,
  OnChangeFn,
  PaginationState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

/**
 * Headless DataTable primitive.
 *
 * Thin wrapper over @tanstack/react-table that renders into shadcn's Table.
 * No skeleton, no empty state, no pagination UI — just the raw tanstack
 * machinery. The opinionated DataTable lives in components/ds/DataTable.tsx
 * and layers features on top of this.
 */

export interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  // Pagination (controlled when onPaginationChange is provided)
  pageCount?: number
  pagination?: PaginationState
  onPaginationChange?: OnChangeFn<PaginationState>
  // Sorting
  sorting?: SortingState
  onSortingChange?: OnChangeFn<SortingState>
  // Manual = server-side paging/sorting
  manualPagination?: boolean
  manualSorting?: boolean
}

export function DataTable<TData, TValue>({
  columns,
  data,
  pageCount,
  pagination,
  onPaginationChange,
  sorting,
  onSortingChange,
  manualPagination = false,
  manualSorting = false,
}: DataTableProps<TData, TValue>) {
  const table = useReactTable({
    data,
    columns,
    pageCount: pageCount ?? -1,
    state: {
      ...(pagination && { pagination }),
      ...(sorting && { sorting }),
    },
    onPaginationChange,
    onSortingChange,
    manualPagination,
    manualSorting,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: manualPagination ? undefined : getPaginationRowModel(),
    getSortedRowModel: manualSorting ? undefined : getSortedRowModel(),
  })

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {header.isPlaceholder
                  ? null
                  : flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows?.length ? (
          table.getRowModel().rows.map((row) => (
            <TableRow
              key={row.id}
              data-state={row.getIsSelected() && "selected"}
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))
        ) : (
          <TableRow>
            <TableCell
              colSpan={columns.length}
              className="h-24 text-center text-sm text-muted-foreground"
            >
              Sin resultados.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}
