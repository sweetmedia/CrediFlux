/**
 * JCE Padrón Cédula Lookup API
 * ~7.9M Dominican citizens registry
 */
import { apiClient } from './client';

export interface CedulaLookupResult {
  found: boolean;
  cedula: string;
  cedula_raw?: string;
  nombres?: string;
  first_name?: string;
  middle_name?: string;
  apellido1?: string;
  apellido2?: string;
  last_name?: string;
  nombre_completo?: string;
  fecha_nacimiento?: string | null;
  source?: string;
  message?: string;
}

export const cedulaAPI = {
  /**
   * Lookup a cédula in the JCE Padrón
   * Returns citizen data if found
   */
  async validate(cedula: string): Promise<CedulaLookupResult> {
    const clean = cedula.replace(/[-\s]/g, '');
    return await apiClient.get<CedulaLookupResult>(
      `/api/validate-cedula/?cedula=${clean}`
    );
  },
};
