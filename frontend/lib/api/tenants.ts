import { apiClient } from './client';

export interface Tenant {
  id: number;
  name: string;
  schema_name: string;
  business_name: string;
  tax_id?: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  is_active: boolean;
  max_users: number;
  subscription_plan: 'basic' | 'professional' | 'enterprise';
  logo?: string;
  primary_color?: string;
  created_on: string;
  updated_on: string;

  // Loan Configuration
  default_interest_rate?: number;
  min_interest_rate?: number;
  max_interest_rate?: number;
  min_loan_amount?: number;
  min_loan_amount_currency?: string;
  max_loan_amount?: number;
  max_loan_amount_currency?: string;
  default_loan_term_months?: number;
  min_loan_term_months?: number;
  max_loan_term_months?: number;
  default_payment_frequency?: 'daily' | 'weekly' | 'biweekly' | 'monthly';
  default_loan_type?: 'personal' | 'business' | 'mortgage' | 'auto' | 'education';
  require_collateral_default?: boolean;
  collateral_required_above?: number;
  collateral_required_above_currency?: string;
  enable_auto_approval?: boolean;
  auto_approval_max_amount?: number;
  auto_approval_max_amount_currency?: string;
  default_grace_period_days?: number;
  require_disbursement_approval?: boolean;
  allow_partial_disbursement?: boolean;

  // Enabled Loan Types
  enabled_loan_types?: string[];

  // Payment Methods
  accepted_payment_methods?: string[];
  enable_cash_payments?: boolean;
  enable_check_payments?: boolean;
  enable_bank_transfer_payments?: boolean;
  enable_card_payments?: boolean;
  enable_mobile_payments?: boolean;

  // Credit Score Requirements
  require_credit_score?: boolean;
  minimum_credit_score?: number;
  credit_score_for_auto_approval?: number;

  // Currency Settings
  default_currency?: string;
  allow_multiple_currencies?: boolean;
  supported_currencies?: string[];

  // Document Requirements
  require_id_document?: boolean;
  require_proof_of_income?: boolean;
  require_proof_of_address?: boolean;
  require_bank_statement?: boolean;
  require_employment_letter?: boolean;
  enhanced_verification_amount?: number;
  enhanced_verification_amount_currency?: string;
  enhanced_verification_documents?: string[];

  // Additional Loan Settings
  allow_early_repayment?: boolean;
  early_repayment_penalty?: number;
  require_guarantor?: boolean;
  guarantor_required_above?: number;
  guarantor_required_above_currency?: string;
  max_active_loans_per_customer?: number;

  // Late Fee Configuration
  late_fee_type?: 'percentage' | 'fixed' | 'none';
  late_fee_percentage?: number;
  late_fee_fixed_amount?: number;
  late_fee_fixed_amount_currency?: string;
  late_fee_frequency?: 'daily' | 'monthly' | 'one_time';
  grace_period_days?: number;

  // Notification Configuration
  enable_email_reminders?: boolean;
  enable_sms_reminders?: boolean;
  enable_whatsapp_reminders?: boolean;
  reminder_days_before?: number;
  notification_email_from?: string;
}

export interface TenantUpdateData {
  business_name?: string;
  tax_id?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  primary_color?: string;

  // Loan Configuration
  default_interest_rate?: number;
  min_interest_rate?: number;
  max_interest_rate?: number;
  min_loan_amount?: number;
  max_loan_amount?: number;
  default_loan_term_months?: number;
  min_loan_term_months?: number;
  max_loan_term_months?: number;
  default_payment_frequency?: string;
  default_loan_type?: string;
  require_collateral_default?: boolean;
  collateral_required_above?: number;
  enable_auto_approval?: boolean;
  auto_approval_max_amount?: number;
  default_grace_period_days?: number;
  require_disbursement_approval?: boolean;
  allow_partial_disbursement?: boolean;

  // Enabled Loan Types
  enabled_loan_types?: string[];

  // Payment Methods
  accepted_payment_methods?: string[];
  enable_cash_payments?: boolean;
  enable_check_payments?: boolean;
  enable_bank_transfer_payments?: boolean;
  enable_card_payments?: boolean;
  enable_mobile_payments?: boolean;

  // Credit Score Requirements
  require_credit_score?: boolean;
  minimum_credit_score?: number;
  credit_score_for_auto_approval?: number;

  // Currency Settings
  default_currency?: string;
  allow_multiple_currencies?: boolean;
  supported_currencies?: string[];

  // Document Requirements
  require_id_document?: boolean;
  require_proof_of_income?: boolean;
  require_proof_of_address?: boolean;
  require_bank_statement?: boolean;
  require_employment_letter?: boolean;
  enhanced_verification_amount?: number;
  enhanced_verification_documents?: string[];

  // Additional Loan Settings
  allow_early_repayment?: boolean;
  early_repayment_penalty?: number;
  require_guarantor?: boolean;
  guarantor_required_above?: number;
  max_active_loans_per_customer?: number;

  // Late Fee Configuration
  late_fee_type?: string;
  late_fee_percentage?: number;
  late_fee_fixed_amount?: number;
  late_fee_frequency?: string;
  grace_period_days?: number;

  // Notification Configuration
  enable_email_reminders?: boolean;
  enable_sms_reminders?: boolean;
  enable_whatsapp_reminders?: boolean;
  reminder_days_before?: number;
  notification_email_from?: string;
}

export interface TenantUpdateResponse {
  message: string;
  tenant: Tenant;
}

export const tenantsAPI = {
  /**
   * Get current tenant settings
   */
  getSettings: async (): Promise<Tenant> => {
    return apiClient.get<Tenant>('/api/tenants/settings/');
  },

  /**
   * Update tenant settings
   */
  updateSettings: async (data: TenantUpdateData): Promise<TenantUpdateResponse> => {
    return apiClient.patch<TenantUpdateResponse>('/api/tenants/settings/', data);
  },

  /**
   * Upload tenant logo
   */
  uploadLogo: async (file: File): Promise<TenantUpdateResponse> => {
    const formData = new FormData();
    formData.append('logo', file);

    const { getApiUrl } = await import('./client');
    const token = localStorage.getItem('access_token');
    const apiUrl = getApiUrl();

    console.log('Uploading to:', `${apiUrl}/api/tenants/settings/`);
    console.log('File:', file.name, file.size, file.type);
    console.log('Token exists:', !!token);

    try {
      const response = await fetch(`${apiUrl}/api/tenants/settings/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      console.log('Response status:', response.status, response.statusText);

      if (!response.ok) {
        let error;
        try {
          error = await response.json();
          console.log('Error response:', error);
        } catch (e) {
          // If response is not JSON, use status text
          const text = await response.text();
          console.log('Error response (text):', text);
          error = { detail: response.statusText || 'Error desconocido' };
        }

        const err = new Error('Upload failed');
        (err as any).response = {
          data: error,
          status: response.status,
          statusText: response.statusText
        };
        throw err;
      }

      const result = await response.json();
      console.log('Upload success:', result);
      return result;
    } catch (error: any) {
      console.error('Upload error:', error);
      // Re-throw with better error information
      if (error.response) {
        throw error;
      }
      // Network error or other issues
      throw new Error(`Error de red: ${error.message || 'No se pudo conectar con el servidor'}`);
    }
  },

  /**
   * Remove tenant logo
   */
  removeLogo: async (): Promise<TenantUpdateResponse> => {
    return apiClient.patch<TenantUpdateResponse>('/api/tenants/settings/', { logo: null });
  },
};
