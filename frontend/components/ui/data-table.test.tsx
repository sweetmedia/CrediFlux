import { fireEvent, render, screen, within } from '@testing-library/react';
import type { ColumnDef } from '@tanstack/react-table';
import { describe, expect, it } from 'vitest';
import { DataTable } from './data-table';

type Fila = { cliente: string; monto: string; vence: string };

const columnas: ColumnDef<Fila>[] = [
  { accessorKey: 'cliente', header: 'Cliente' },
  { accessorKey: 'monto', header: 'Monto', meta: { type: 'num' } },
  { accessorKey: 'vence', header: 'Vence', meta: { type: 'date' } },
];

const datos: Fila[] = [
  { cliente: 'Carmen', monto: 'RD$ 12,000.00', vence: '10 abr 2026' },
  { cliente: 'Ana', monto: '—', vence: '02 mar 2026' },
  { cliente: 'Luis', monto: 'RD$ 950.00', vence: '—' },
  { cliente: 'Pedro', monto: 'RD$ 3,400.50', vence: '2026-01-15' },
];

const clientes = () =>
  within(screen.getAllByRole('rowgroup')[1])
    .getAllByRole('row')
    .map((r) => within(r).getAllByRole('cell')[0].textContent);

const cabecera = (nombre: string) => screen.getByRole('columnheader', { name: nombre });

describe('DataTable', () => {
  it('ordena por cabecera: ascendente, luego descendente, vacíos al final', () => {
    render(<DataTable columns={columnas} data={datos} footer={<tr><td>Total</td></tr>} />);
    expect(cabecera('Monto')).toHaveAttribute('aria-sort', 'none');

    fireEvent.click(screen.getByRole('button', { name: 'Monto' }));
    expect(cabecera('Monto')).toHaveAttribute('aria-sort', 'ascending');
    expect(clientes()).toEqual(['Luis', 'Pedro', 'Carmen', 'Ana']);

    fireEvent.click(screen.getByRole('button', { name: 'Monto' }));
    expect(cabecera('Monto')).toHaveAttribute('aria-sort', 'descending');
    expect(clientes()).toEqual(['Carmen', 'Pedro', 'Luis', 'Ana']);

    fireEvent.click(screen.getByRole('button', { name: 'Vence' }));
    expect(cabecera('Monto')).toHaveAttribute('aria-sort', 'none');
    expect(clientes()).toEqual(['Pedro', 'Ana', 'Carmen', 'Luis']);
  });

  it('el pie de totales queda fuera del cuerpo y no se ordena', () => {
    render(<DataTable columns={columnas} data={datos} footer={<tr><td>Total</td></tr>} />);
    fireEvent.click(screen.getByRole('button', { name: 'Cliente' }));
    const grupos = screen.getAllByRole('rowgroup');
    expect(grupos).toHaveLength(3);
    expect(within(grupos[2]).getByText('Total')).toBeInTheDocument();
    expect(clientes()).toEqual(['Ana', 'Carmen', 'Luis', 'Pedro']);
  });

  it('usa el marcado del DS', () => {
    const { container } = render(<DataTable columns={columnas} data={datos} initialSort={{ id: 'monto', desc: true }} />);
    expect(container.querySelector('table')).toHaveClass('cf-table');
    expect(cabecera('Monto')).toHaveClass('cf-num');
    expect(cabecera('Monto')).toHaveAttribute('aria-sort', 'descending');
    expect(screen.getByRole('button', { name: 'Monto' })).toHaveClass('cf-sort');
  });
});
