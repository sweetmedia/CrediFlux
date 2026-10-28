import { render, screen } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

type U = { is_tenant_owner?: boolean; role?: string; permissions?: string[] } | null;
let currentUser: U = null;
vi.mock('@/lib/contexts/AuthContext', () => ({ useAuth: () => ({ user: currentUser }) }));

const get = vi.fn();
vi.mock('@/lib/api/client', () => ({ apiClient: { get: (...a: unknown[]) => get(...a) } }));

import { useCan, permissionLabel, usePermissionLabel } from '@/lib/permissions';
import { PermissionGate } from '@/components/auth/PermissionGate';
import { NAV_GROUPS, visibleNavGroups } from '@/components/layout/nav';

beforeEach(() => {
  currentUser = null;
  get.mockReset();
});

describe('useCan', () => {
  it('lee user.permissions', () => {
    currentUser = { role: 'viewer', permissions: ['loans.view'] };
    const { result } = renderHook(() => useCan());
    expect(result.current('loans.view')).toBe(true);
    expect(result.current('loans.approve')).toBe(false);
  });

  it('el dueño puede todo aunque su usuario en caché no traiga permisos', () => {
    currentUser = { is_tenant_owner: true };
    const { result } = renderHook(() => useCan());
    expect(result.current('loans.approve')).toBe(true);
  });

  it('sin permisos cargados (caché previa al despliegue) falla cerrado', () => {
    currentUser = { role: 'admin' };
    const { result } = renderHook(() => useCan());
    expect(result.current('loans.view')).toBe(false);
  });

  it('sin usuario no puede nada', () => {
    const { result } = renderHook(() => useCan());
    expect(result.current('loans.view')).toBe(false);
  });
});

describe('PermissionGate', () => {
  it('oculta su contenido sin el permiso y muestra el fallback', () => {
    currentUser = { permissions: ['loans.view'] };
    render(
      <PermissionGate code="loans.approve" fallback={<p>sin acceso</p>}>
        <p>aprobar</p>
      </PermissionGate>
    );
    expect(screen.queryByText('aprobar')).toBeNull();
    expect(screen.getByText('sin acceso')).toBeTruthy();
  });

  it('muestra su contenido con el permiso', () => {
    currentUser = { permissions: ['loans.approve'] };
    render(<PermissionGate code="loans.approve"><p>aprobar</p></PermissionGate>);
    expect(screen.getByText('aprobar')).toBeTruthy();
  });
});

describe('menú', () => {
  const labels = (can: (c: string) => boolean) =>
    visibleNavGroups(NAV_GROUPS, can).flatMap((g) => g.items.map((i) => i.label));

  it('muestra «Equipo» con team.view aunque el rol no sea admin', () => {
    const codes = ['team.view'];
    expect(labels((c) => codes.includes(c))).toContain('Equipo');
  });

  it('cada ítem lleva el código de su pantalla', () => {
    const byLabel = Object.fromEntries(NAV_GROUPS.flatMap((g) => g.items).map((i) => [i.label, i.permission]));
    expect(byLabel['Contratos']).toBe('contracts.view');
    expect(byLabel['Reportes DGII']).toBe('billing.reports');
    expect(byLabel['Tareas']).toBe('comms.view');
    expect(byLabel['Gestiones']).toBe('collections.view');
  });

  it('oculta «Equipo» y el grupo Administración sin los permisos', () => {
    const l = labels(() => false);
    expect(l).not.toContain('Equipo');
    expect(visibleNavGroups(NAV_GROUPS, () => false).some((g) => g.id === 'admin')).toBe(false);
  });
});

describe('permissionLabel', () => {
  it('devuelve el código si no hay catálogo', () => {
    expect(permissionLabel('zzz.unknown')).toBe('zzz.unknown');
  });

  it('usePermissionLabel se actualiza cuando llega el catálogo', async () => {
    currentUser = { permissions: [] };
    get.mockResolvedValue([
      { key: 'payments', label: 'Pagos', permissions: [{ code: 'payments.void', label: 'Anular pago' }] },
    ]);
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => usePermissionLabel(), { wrapper });
    expect(result.current('payments.void')).toBe('payments.void');
    await vi.waitFor(() => expect(result.current('payments.void')).toBe('Anular pago'));
    expect(get).toHaveBeenCalledWith('/api/users/permissions/catalog/');
  });
});
