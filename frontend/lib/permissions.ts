/**
 * Permisos del usuario actual (D6). El backend devuelve `user.permissions`
 * (códigos como `loans.approve`); la SPA ya no compara roles fijos.
 */
import { useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useAuth } from '@/lib/contexts/AuthContext';

export interface PermissionCatalogGroup {
  key: string;
  label: string;
  permissions: { code: string; label: string }[];
}

/**
 * Devuelve `can(code)`. El dueño puede todo (respaldo para un usuario en caché
 * sin `permissions`). Si el usuario aún no trae `permissions` (sesión previa al
 * despliegue; AuthContext lo refresca al arrancar) se falla cerrado.
 */
export function useCan(): (code: string) => boolean {
  const { user } = useAuth();
  return useCallback(
    (code: string) => {
      if (!user) return false;
      if (user.is_tenant_owner) return true;
      return !!user.permissions?.includes(code);
    },
    [user]
  );
}

export const PERMISSION_CATALOG_KEY = ['permissions-catalog'] as const;

/** Catálogo de permisos (cacheado por TanStack Query). */
export function usePermissionCatalog() {
  const { user } = useAuth();
  return useQuery({
    queryKey: PERMISSION_CATALOG_KEY,
    enabled: !!user,
    staleTime: 60 * 60 * 1000,
    queryFn: () => apiClient.get<PermissionCatalogGroup[]>('/api/users/permissions/catalog/'),
  });
}

/** Etiqueta legible del permiso según el catálogo; el código mismo si no lo trae. */
export function permissionLabel(code: string, catalog?: PermissionCatalogGroup[]): string {
  for (const group of catalog ?? []) {
    const hit = group.permissions.find((p) => p.code === code);
    if (hit) return hit.label;
  }
  return code;
}

/** `(code) => etiqueta`; el componente se vuelve a renderizar cuando llega el catálogo. */
export function usePermissionLabel(): (code: string) => string {
  const { data } = usePermissionCatalog();
  return useCallback((code: string) => permissionLabel(code, data), [data]);
}
