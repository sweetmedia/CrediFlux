/**
 * DataTable del DS: toda tabla de datos se ordena por cabecera (`cf-table`,
 * `cf-sort`). Cada columna dice su tipo en `meta.type` (text, num, date); el
 * pie (`footer`, p. ej. totales) va en <tfoot> y no se mueve al ordenar.
 */

import * as React from 'react';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowData,
} from '@tanstack/react-table';
import { cn } from '@/lib/utils';
import { compareSortValues, parseSortValue, type SortType, type SortValue } from '@/lib/table/sort';

declare module '@tanstack/react-table' {
  interface ColumnMeta<TData extends RowData, TValue> {
    /** Cómo se ordena la columna. `num` también la alinea a la derecha. */
    type?: SortType;
    /** `false` para columnas de acciones. */
    sortable?: boolean;
  }
}

export interface DataTableSort {
  id: string;
  desc: boolean;
}

export interface DataTableProps<T> {
  columns: ColumnDef<T, any>[];
  data: T[];
  footer?: React.ReactNode;
  initialSort?: DataTableSort;
  className?: string;
  /** Fila vacía cuando no hay datos. */
  empty?: React.ReactNode;
}

const ICONO = (
  <svg className="cf-sort__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <polyline points="18 15 12 9 6 15" />
  </svg>
);

function valorDeOrden(v: unknown, type: SortType): SortValue {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number') return Number.isNaN(v) ? null : v;
  if (v instanceof Date) return v.getTime();
  return parseSortValue(String(v), type);
}

export function DataTable<T>({ columns, data, footer, initialSort, className, empty }: DataTableProps<T>) {
  const [sort, setSort] = React.useState<DataTableSort | undefined>(initialSort);
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });

  const filas = React.useMemo(() => {
    const rows = table.getRowModel().rows;
    if (!sort) return rows;
    const col = table.getColumn(sort.id);
    if (!col) return rows;
    const type = col.columnDef.meta?.type ?? 'text';
    const dir = sort.desc ? 'desc' : 'asc';
    return [...rows].sort((a, b) =>
      compareSortValues(valorDeOrden(a.getValue(sort.id), type), valorDeOrden(b.getValue(sort.id), type), dir),
    );
    // table.getRowModel() cambia con data/columns.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table, data, columns, sort]);

  return (
    <table className={cn('cf-table', className)}>
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id}>
            {hg.headers.map((h) => {
              const meta = h.column.columnDef.meta;
              const ordenable = meta?.sortable !== false && !h.isPlaceholder;
              const activo = sort?.id === h.column.id;
              const label = h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext());
              return (
                <th
                  key={h.id}
                  scope="col"
                  className={cn(meta?.type === 'num' && 'cf-num')}
                  aria-sort={ordenable ? (activo ? (sort!.desc ? 'descending' : 'ascending') : 'none') : undefined}
                >
                  {ordenable ? (
                    <button
                      type="button"
                      className="cf-sort"
                      onClick={() => setSort({ id: h.column.id, desc: activo ? !sort!.desc : false })}
                    >
                      {label}
                      {ICONO}
                    </button>
                  ) : (
                    label
                  )}
                </th>
              );
            })}
          </tr>
        ))}
      </thead>
      <tbody>
        {filas.length === 0 && empty ? (
          <tr>
            <td colSpan={columns.length}>{empty}</td>
          </tr>
        ) : (
          filas.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className={cn(cell.column.columnDef.meta?.type === 'num' && 'cf-num')}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))
        )}
      </tbody>
      {footer ? <tfoot>{footer}</tfoot> : null}
    </table>
  );
}
