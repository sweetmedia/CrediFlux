import {
  LayoutDashboard,
  FileText,
  Users,
  Phone,
  DollarSign,
  UsersRound,
  Settings,
  FileSignature,
  ScrollText,
  MessageSquare,
  CheckSquare,
  ClipboardList,
  Receipt,
  Shield,
  Hash,
  Calculator,
  MapPin,
  FileSpreadsheet,
  Banknote,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'

import type { ModuleId } from '@/lib/api/queries/useModules'

export interface NavItem {
  href: string
  icon: LucideIcon
  /** i18n key (under `nav` namespace) */
  labelKey: string
}

export interface NavGroup {
  id: string
  /** i18n key (under `nav` namespace) for the group heading */
  labelKey: string
  /** Only render this group when the tenant has the module active. */
  module?: ModuleId
  /** Require admin/owner role to see this group. */
  adminOnly?: boolean
  items: NavItem[]
}

/**
 * Canonical dashboard navigation structure.
 *
 * Sidebar, breadcrumbs, and module filtering all read from this single source.
 * Labels are i18n keys — the sidebar resolves them via `useTranslations('nav')`.
 */
export const navigationGroups: NavGroup[] = [
  {
    id: 'overview',
    labelKey: 'overview',
    items: [
      { href: '/dashboard', icon: LayoutDashboard, labelKey: 'dashboard' },
      { href: '/calculator', icon: Calculator, labelKey: 'calculator' },
      { href: '/ai', icon: Sparkles, labelKey: 'aiAssistant' },
    ],
  },
  {
    id: 'operation',
    labelKey: 'operation',
    module: 'loans',
    items: [
      { href: '/loans', icon: FileText, labelKey: 'loans' },
      { href: '/customers', icon: Users, labelKey: 'customers' },
      { href: '/payments', icon: DollarSign, labelKey: 'payments' },
      { href: '/cashbox', icon: Banknote, labelKey: 'cashbox' },
    ],
  },
  {
    id: 'collections',
    labelKey: 'collections',
    module: 'collections',
    items: [
      { href: '/collections', icon: Phone, labelKey: 'collectionsDashboard' },
      { href: '/collector', icon: MapPin, labelKey: 'collector' },
    ],
  },
  {
    id: 'billing',
    labelKey: 'billing',
    module: 'billing',
    items: [
      { href: '/billing', icon: Receipt, labelKey: 'billingInvoices' },
      { href: '/billing/sequences', icon: Hash, labelKey: 'billingSequences' },
      { href: '/billing/certificates', icon: Shield, labelKey: 'billingCertificates' },
      { href: '/billing/dgii-reports', icon: FileSpreadsheet, labelKey: 'billingReports' },
    ],
  },
  {
    id: 'contracts',
    labelKey: 'contracts',
    module: 'contracts',
    items: [
      { href: '/contracts', icon: FileSignature, labelKey: 'contractsList' },
      { href: '/contract-templates', icon: ScrollText, labelKey: 'contractTemplates' },
    ],
  },
  {
    id: 'communications',
    labelKey: 'communications',
    module: 'communications',
    items: [
      { href: '/communications', icon: MessageSquare, labelKey: 'communicationsCenter' },
      { href: '/tasks', icon: CheckSquare, labelKey: 'tasks' },
    ],
  },
  {
    id: 'admin',
    labelKey: 'admin',
    adminOnly: true,
    items: [
      { href: '/users', icon: UsersRound, labelKey: 'team' },
      { href: '/audit', icon: ClipboardList, labelKey: 'audit' },
      { href: '/settings', icon: Settings, labelKey: 'settings' },
    ],
  },
]
