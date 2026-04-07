/**
 * Customer Contacts API — Multi-phone & multi-email
 */
import { apiClient } from './client';

export interface CustomerPhoneData {
  id?: string;
  customer: string;
  phone: string;
  phone_type: 'mobile' | 'home' | 'work' | 'landline' | 'whatsapp' | 'fax' | 'other';
  phone_type_display?: string;
  label?: string;
  is_primary: boolean;
  is_whatsapp: boolean;
  notes?: string;
}

export interface CustomerEmailData {
  id?: string;
  customer: string;
  email: string;
  email_type: 'personal' | 'work' | 'business' | 'other';
  email_type_display?: string;
  label?: string;
  is_primary: boolean;
  notes?: string;
}

export const contactsAPI = {
  // Create a customer phone
  async createPhone(data: Omit<CustomerPhoneData, 'id' | 'phone_type_display'>): Promise<CustomerPhoneData> {
    return apiClient.post<CustomerPhoneData>('/api/loans/customer-phones/', data);
  },

  // Create a customer email
  async createEmail(data: Omit<CustomerEmailData, 'id' | 'email_type_display'>): Promise<CustomerEmailData> {
    return apiClient.post<CustomerEmailData>('/api/loans/customer-emails/', data);
  },

  // Get phones for a customer
  async getPhones(customerId: string): Promise<CustomerPhoneData[]> {
    const res = await apiClient.get<any>(`/api/loans/customer-phones/?customer=${customerId}`);
    return res.results || res;
  },

  // Get emails for a customer
  async getEmails(customerId: string): Promise<CustomerEmailData[]> {
    const res = await apiClient.get<any>(`/api/loans/customer-emails/?customer=${customerId}`);
    return res.results || res;
  },

  // Delete phone
  async deletePhone(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/customer-phones/${id}/`);
  },

  // Delete email
  async deleteEmail(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/customer-emails/${id}/`);
  },
};
