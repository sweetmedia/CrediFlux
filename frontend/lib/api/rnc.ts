/**
 * RNC Validation API
 */
import { apiClient } from './client';

export interface RNCValidationResult {
  is_valid: boolean;
  exists: boolean;
  is_active: boolean;
  data: RNCData | null;
  message: string;
  source: 'local_db' | 'dgii_scraper' | null;
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
  source?: 'local_db' | 'dgii_scraper';
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
    return await apiClient.post<RNCValidationResult>('/api/validate-rnc/', { rnc });
  },

  /**
   * Get RNC database status
   */
  async getDatabaseStatus(): Promise<RNCDatabaseStatus> {
    return await apiClient.get<RNCDatabaseStatus>('/api/rnc-database-status/');
  },
};
