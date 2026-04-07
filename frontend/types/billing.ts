// ============================================================
// Billing / Facturación Electrónica Types
// ============================================================

// e-CF Types
export type ECFType = '31' | '32' | '33' | '34' | '41' | '43' | '44' | '45' | '46' | '47';

export const ECF_TYPE_LABELS: Record<ECFType, string> = {
  '31': 'Factura de Crédito Fiscal',
  '32': 'Factura de Consumo',
  '33': 'Nota de Débito',
  '34': 'Nota de Crédito',
  '41': 'Compras',
  '43': 'Gastos Menores',
  '44': 'Regímenes Especiales',
  '45': 'Gubernamental',
  '46': 'Exportaciones',
  '47': 'Pagos al Exterior',
};

// Invoice Status
export type InvoiceStatus =
  | 'draft'
  | 'generated'
  | 'signed'
  | 'submitted'
  | 'accepted'
  | 'conditionally_accepted'
  | 'rejected'
  | 'cancelled';

export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: 'Borrador',
  generated: 'XML Generado',
  signed: 'Firmado',
  submitted: 'Enviado a DGII',
  accepted: 'Aceptado',
  conditionally_accepted: 'Aceptado Condicional',
  rejected: 'Rechazado',
  cancelled: 'Anulado',
};

export const INVOICE_STATUS_COLORS: Record<InvoiceStatus, string> = {
  draft: 'bg-slate-100 text-slate-700',
  generated: 'bg-blue-100 text-blue-700',
  signed: 'bg-indigo-100 text-indigo-700',
  submitted: 'bg-yellow-100 text-yellow-700',
  accepted: 'bg-green-100 text-green-700',
  conditionally_accepted: 'bg-orange-100 text-orange-700',
  rejected: 'bg-red-100 text-red-700',
  cancelled: 'bg-slate-100 text-slate-500',
};

// Payment Methods
export type PaymentMethod = '01' | '02' | '03' | '04' | '05' | '06' | '07';

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  '01': 'Efectivo',
  '02': 'Cheque / Transferencia',
  '03': 'Tarjeta de Crédito/Débito',
  '04': 'Venta a Crédito',
  '05': 'Permuta',
  '06': 'Nota de Crédito',
  '07': 'Mixto',
};

// ITBIS Rates
export type ITBISRate = '18' | '16' | '0';

export const ITBIS_RATE_LABELS: Record<ITBISRate, string> = {
  '18': '18% (General)',
  '16': '16% (Reducida)',
  '0': '0% (Exento)',
};

// DGII Environment
export type DGIIEnvironment = 'testecf' | 'certecf' | 'ecf';

export const DGII_ENV_LABELS: Record<DGIIEnvironment, string> = {
  testecf: 'Pre-Certificación',
  certecf: 'Certificación',
  ecf: 'Producción',
};

// ============================================================
// Models
// ============================================================

export interface DigitalCertificate {
  id: string;
  name: string;
  issuer: string;
  serial_number: string;
  valid_from: string | null;
  valid_until: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FiscalSequence {
  id: string;
  ecf_type: ECFType;
  ecf_type_display: string;
  prefix: string;
  range_from: number;
  range_to: number;
  current_number: number;
  expiration_date: string | null;
  is_active: boolean;
  authorization_number: string;
  available_count: number;
  is_exhausted: boolean;
  created_at: string;
  updated_at: string;
}

export interface InvoiceItem {
  id: string;
  line_number: number;
  description: string;
  quantity: number;
  unit_price: number;
  unit_price_currency: string;
  discount_amount: number;
  discount_amount_currency: string;
  itbis_rate: ITBISRate;
  itbis_amount: number;
  itbis_amount_currency: string;
  total: number;
  total_currency: string;
}

export interface Invoice {
  id: string;
  encf_number: string | null;
  ecf_type: ECFType;
  ecf_type_display: string;
  fiscal_sequence: string | null;
  security_code: string;
  status: InvoiceStatus;
  status_display: string;
  // Emisor
  emisor_rnc: string;
  emisor_razon_social: string;
  // Comprador
  comprador_rnc: string;
  comprador_razon_social: string;
  // Links
  loan: string | null;
  payment: string | null;
  customer: string;
  reference_invoice: string | null;
  // Dates
  issue_date: string;
  due_date: string | null;
  payment_method: PaymentMethod;
  payment_method_display: string;
  // Totals
  subtotal: number;
  subtotal_currency: string;
  total_itbis: number;
  total_itbis_currency: string;
  total_discount: number;
  total_discount_currency: string;
  total: number;
  total_currency: string;
  // DGII
  dgii_trackid: string;
  dgii_status: string;
  dgii_response: any;
  dgii_submitted_at: string | null;
  // XML
  xml_content: string;
  signed_xml: string;
  certificate: string | null;
  // Items
  items: InvoiceItem[];
  // Meta
  notes: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface InvoiceCreate {
  ecf_type: ECFType;
  customer: string;
  loan?: string;
  payment?: string;
  issue_date: string;
  due_date?: string;
  payment_method: PaymentMethod;
  reference_invoice?: string;
  notes?: string;
  items: InvoiceItemCreate[];
}

export interface InvoiceItemCreate {
  line_number: number;
  description: string;
  quantity: number;
  unit_price: number;
  unit_price_currency?: string;
  discount_amount?: number;
  itbis_rate: ITBISRate;
}

export interface ECFSubmission {
  id: string;
  invoice: string;
  action: 'submit' | 'query_status' | 'query_result' | 'cancel';
  action_display: string;
  environment: DGIIEnvironment;
  environment_display: string;
  trackid: string;
  response_status: string;
  response_body: any;
  http_status_code: number | null;
  error_message: string;
  submitted_at: string;
}

// ============================================================
// Statistics
// ============================================================

export interface BillingStatistics {
  total_invoices: number;
  draft_count: number;
  submitted_count: number;
  accepted_count: number;
  rejected_count: number;
  total_billed: number;
  total_itbis: number;
}
