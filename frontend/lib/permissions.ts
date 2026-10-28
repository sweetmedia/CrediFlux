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

const labels = new Map<string, string>();

export const PERMISSION_CATALOG_KEY = ['permissions-catalog'] as const;

/** Catálogo de permisos (cacheado por TanStack Query); alimenta `permissionLabel`. */
export function usePermissionCatalog() {
  const { user } = useAuth();
  return useQuery({
    queryKey: PERMISSION_CATALOG_KEY,
    enabled: !!user,
    staleTime: 60 * 60 * 1000,
    queryFn: async () => {
      const catalog = await apiClient.get<PermissionCatalogGroup[]>('/api/users/permissions/catalog/');
      for (const group of catalog) {
        for (const p of group.permissions) labels.set(p.code, p.label);
      }
      return catalog;
    },
  });
}

/** Etiqueta legible del permiso; el código mismo si el catálogo no se ha cargado. */
export function permissionLabel(code: string): string {
  return labels.get(code) ?? code;
}
