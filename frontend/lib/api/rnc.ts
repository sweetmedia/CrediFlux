/**
 * RNC Validation API
 */
import api from './base';

export interface RNCValidationResult {
  is_valid: boolean;
  exists: boolean;
  is_active: boolean;
  data: RNCData | null;
  message: string;
  database_loaded?: boolean;
}

export interface RNCData {
  rnc: string;
  razon_social: string;
  actividad_economica: string;
  fecha_inicio: string;
  estado: string;
  regimen_pago: string;
  is_active: boolean;
}

export interface RNCDatabaseStatus {
  loaded: boolean;
  total_records: number;
  last_updated: string | null;
  message?: string;
}

export const rncAPI = {
  /**
   * Validate an RNC or Cedula number
   */
  async validateRNC(rnc: string): Promise<RNCValidationResult> {
    const response = await api.post<RNCValidationResult>('/validate-rnc/', { rnc });
    return response.data;
  },

  /**
   * Get RNC database status
   */
  async getDatabaseStatus(): Promise<RNCDatabaseStatus> {
    const response = await api.get<RNCDatabaseStatus>('/rnc-database-status/');
    return response.data;
  },
};
