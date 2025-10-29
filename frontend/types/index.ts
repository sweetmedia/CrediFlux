// User Types
export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  avatar: string | null;
  bio: string | null;
  job_title: string | null;
  department: string | null;
  role: 'admin' | 'manager' | 'loan_officer' | 'accountant' | 'cashier' | 'viewer';
  tenant?: number;
  tenant_name?: string;
  is_tenant_owner: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  email_verified: boolean;
  receive_notifications: boolean;
  created_at: string;
  updated_at?: string;
  last_login_at: string | null;
}

// Customer Types
export interface Customer {
  id: string;
  customer_id: string;
  first_name: string;
  middle_name?: string;
  last_name: string;
  full_name: string;
  date_of_birth: string;
  gender?: 'M' | 'F' | 'O';
  email: string;
  phone: string;
  alternate_phone?: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  id_type: 'cedula' | 'passport' | 'driver_license';
  id_number: string;
  id_expiry_date?: string;
  id_document?: string;
  employment_status?: 'employed' | 'self_employed' | 'unemployed' | 'retired';
  employer_name?: string;
  occupation?: string;
  monthly_income?: number;
  credit_score?: number;
  status: 'active' | 'inactive' | 'blacklisted';
  notes?: string;
  photo?: string;
  total_loans: number;
  active_loans: number;
  created_at: string;
  updated_at: string;
}

// Loan Types
export interface Loan {
  id: string;
  loan_number: string;
  customer: string;
  customer_name: string;
  customer_details: {
    id: string;
    customer_id: string;
    full_name: string;
    email: string;
    phone: string;
    status: string;
    created_at: string;
  };
  loan_type: 'personal' | 'auto' | 'mortgage' | 'business' | 'student' | 'payday';
  principal_amount: number;
  interest_rate: number;
  term_months: number;
  payment_frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'quarterly';
  payment_amount: number;
  application_date: string;
  approval_date?: string;
  rejection_date?: string;
  disbursement_date?: string;
  first_payment_date?: string;
  maturity_date?: string;
  status: 'draft' | 'pending' | 'approved' | 'active' | 'paid' | 'defaulted' | 'written_off' | 'rejected';
  outstanding_balance: number;
  total_paid: number;
  total_interest_paid: number;
  late_fees: number;
  loan_officer?: string;
  loan_officer_name?: string;
  approved_by?: string;
  approved_by_name?: string;
  rejected_by?: string;
  rejected_by_name?: string;
  approval_notes?: string;
  purpose?: string;
  notes?: string;
  terms_accepted: boolean;
  contract_document?: string;
  total_amount: number;
  is_overdue: boolean;
  collaterals: Collateral[];
  payment_schedules: LoanSchedule[];
  recent_payments: LoanPayment[];
  created_at: string;
  updated_at: string;
}

// Loan Schedule Types
export interface LoanSchedule {
  id: string;
  loan: string;
  installment_number: number;
  due_date: string;
  total_amount: number;
  principal_amount: number;
  interest_amount: number;
  paid_amount: number;
  paid_date?: string;
  status: 'pending' | 'paid' | 'overdue' | 'partial';
  balance: number;
  created_at: string;
  updated_at: string;
}

// Loan Payment Types
export interface LoanPayment {
  id: string;
  payment_number: string;
  loan: string;
  loan_number: string;
  customer_name: string;
  schedule?: string;
  payment_date: string;
  amount: number;
  principal_paid: number;
  interest_paid: number;
  late_fee_paid: number;
  payment_method: 'cash' | 'check' | 'bank_transfer' | 'card' | 'mobile_payment';
  reference_number?: string;
  status: 'pending' | 'completed' | 'failed' | 'reversed';
  notes?: string;
  receipt?: string;
  created_at: string;
  updated_at: string;
}

// Collateral Types
export interface Collateral {
  id: string;
  loan: string;
  collateral_type: 'vehicle' | 'property' | 'equipment' | 'inventory' | 'securities' | 'cash_deposit' | 'other';
  description: string;
  estimated_value: number;
  appraisal_value?: number;
  appraisal_date?: string;
  documents?: string;
  photos?: string;
  status: 'active' | 'released' | 'liquidated';
  notes?: string;
  created_at: string;
  updated_at: string;
}

// Tenant Types
export interface Tenant {
  id: number;
  name: string;
  business_name: string;
  subscription_plan: 'basic' | 'professional' | 'enterprise';
  is_active: boolean;
  domain: string;
}

// Auth Types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface TenantLoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  tenant: Tenant;
  message: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}

// Tenant Registration
export interface TenantRegistrationData {
  business_name: string;
  tenant_name: string;
  tax_id?: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  subdomain: string;
  owner_first_name: string;
  owner_last_name: string;
  owner_email: string;
  owner_password: string;
  owner_phone?: string;
  subscription_plan: 'basic' | 'professional' | 'enterprise';
}

// Email Verification
export interface EmailVerificationRequest {
  email: string;
}

export interface EmailVerificationConfirm {
  uid: string;
  token: string;
}

// Password Reset
export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  uid: string;
  token: string;
  new_password: string;
  confirm_password: string;
}

// Profile Update
export interface ProfileUpdateData {
  first_name?: string;
  last_name?: string;
  phone?: string;
  avatar?: File | null;
  bio?: string;
  job_title?: string;
  department?: string;
  receive_notifications?: boolean;
}

// Password Change
export interface PasswordChangeData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

// Team Member Types
export interface TeamMember {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  role: 'admin' | 'manager' | 'loan_officer' | 'accountant' | 'cashier' | 'viewer';
  job_title: string | null;
  department: string | null;
  is_tenant_owner: boolean;
  is_active: boolean;
  email_verified: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TeamMemberCreate {
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  phone?: string;
  password: string;
  role: 'admin' | 'manager' | 'loan_officer' | 'accountant' | 'cashier' | 'viewer';
  job_title?: string;
  department?: string;
}

export interface TeamMemberUpdate {
  first_name?: string;
  last_name?: string;
  phone?: string;
  role?: 'admin' | 'manager' | 'loan_officer' | 'accountant' | 'cashier' | 'viewer';
  job_title?: string;
  department?: string;
  is_active?: boolean;
}

// API Response Types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail?: string;
  [key: string]: any;
}

// Statistics Types
export interface LoanStatistics {
  total_loans: number;
  active_loans: number;
  pending_loans: number;
  paid_loans: number;
  defaulted_loans: number;
  total_disbursed: number;
  total_outstanding: number;
  total_collected: number;
}

export interface CustomerStatistics {
  total_loans: number;
  active_loans: number;
  paid_loans: number;
  defaulted_loans: number;
  total_borrowed: number;
  total_outstanding: number;
}
