/**
 * Menú de la app (ShellV1 del canvas F3). Los grupos plegables recuerdan su
 * estado; cada ítem pide un permiso y un grupo sin ítems visibles se oculta. Facturas
 * recibidas, Proveedores (F6) e Impresos (F7) entran cuando existan sus rutas.
 */
import {
  Banknote, BarChart3, Bell, Calculator, CheckSquare, ClipboardCheck, DollarSign, FilePlus,
  FileSignature, FileSpreadsheet, FileText, Hash, LayoutDashboard, List, MapPin, MessageSquare,
  PenLine, Phone, Receipt, Settings, Shield, Sparkles, UserCog, Users, type LucideIcon,
} from 'lucide-react';

/*
 * Códigos más finos del catálogo (contracts.create/templates, comms.tasks,
 * collections.mobile/contacts/reminders) se limitan a _PRESTAMOS/_COBRANZA y
 * esconderían entradas que hoy ven contador, cajero y visualizador; por eso
 * esos ítems piden el código de «ver» de su módulo.
 */
export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Código de permiso para verlo; sin él, siempre visible. */
  permission?: string;
}

export interface NavGroup {
  id: string;
  label: string;
  /** Los grupos fijos (Overview, Administración) no se pliegan. */
  collapsible: boolean;
  /** Plegado la primera vez (luego manda lo que eligió el usuario). */
  collapsedByDefault?: boolean;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    id: 'overview', label: 'Overview', collapsible: false, items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/calculator', label: 'Calculadora', icon: Calculator, permission: 'loans.calculator' },
      { href: '/ai', label: 'Asistente IA', icon: Sparkles, permission: 'ai.access' },
    ],
  },
  {
    id: 'operacion', label: 'Operación', collapsible: true, items: [
      { href: '/loans', label: 'Préstamos', icon: FileText, permission: 'loans.view' },
      { href: '/customers', label: 'Clientes', icon: Users, permission: 'customers.view' },
      { href: '/payments', label: 'Pagos', icon: DollarSign, permission: 'payments.view' },
      { href: '/cashbox', label: 'Caja', icon: Banknote, permission: 'cashbox.view' },
    ],
  },
  {
    id: 'cobranza', label: 'Cobranza', collapsible: true, items: [
      { href: '/collections', label: 'Mesa de cobranza', icon: Phone, permission: 'collections.view' },
      { href: '/collections/contacts', label: 'Gestiones', icon: PenLine, permission: 'collections.view' },
      { href: '/collections/reminders', label: 'Recordatorios', icon: Bell, permission: 'collections.view' },
      { href: '/collector', label: 'Cobrador móvil', icon: MapPin, permission: 'collections.view' },
      { href: '/collections/reports', label: 'Reportes', icon: BarChart3, permission: 'collections.view' },
    ],
  },
  {
    id: 'facturacion', label: 'Facturación', collapsible: true, collapsedByDefault: true, items: [
      { href: '/billing', label: 'Facturas e-CF', icon: Receipt, permission: 'billing.view' },
      { href: '/billing/sequences', label: 'Secuencias e-NCF', icon: Hash, permission: 'billing.view' },
      { href: '/billing/certificates', label: 'Certificados', icon: Shield, permission: 'billing.view' },
      { href: '/billing/dgii-reports', label: 'Reportes DGII', icon: FileSpreadsheet, permission: 'billing.reports' },
    ],
  },
  {
    id: 'contratos', label: 'Contratos', collapsible: true, collapsedByDefault: true, items: [
      { href: '/contracts', label: 'Contratos', icon: FileSignature, permission: 'contracts.view' },
      { href: '/contracts/generate', label: 'Generar contrato', icon: FilePlus, permission: 'contracts.view' },
      { href: '/contract-templates', label: 'Plantillas', icon: List, permission: 'contracts.view' },
    ],
  },
  {
    id: 'comunicaciones', label: 'Comunicaciones', collapsible: true, collapsedByDefault: true, items: [
      { href: '/communications', label: 'Mensajes', icon: MessageSquare, permission: 'comms.view' },
      { href: '/tasks', label: 'Tareas', icon: CheckSquare, permission: 'comms.view' },
    ],
  },
  {
    id: 'admin', label: 'Administración', collapsible: false, items: [
      { href: '/users', label: 'Equipo', icon: UserCog, permission: 'team.view' },
      { href: '/audit', label: 'Auditoría', icon: ClipboardCheck, permission: 'settings.audit' },
      { href: '/settings', label: 'Configuración', icon: Settings, permission: 'settings.view' },
    ],
  },
];

/** Grupos con sus ítems filtrados por permiso; los grupos que quedan vacíos se omiten. */
export function visibleNavGroups(groups: NavGroup[], can: (code: string) => boolean): NavGroup[] {
  return groups
    .map((g) => ({ ...g, items: g.items.filter((i) => !i.permission || can(i.permission)) }))
    .filter((g) => g.items.length > 0);
}

/** Marca activa la ruta exacta o una hija; `/collections` no se activa en `/collections/contacts`. */
export function activeHref(pathname: string, hrefs: string[]): string | undefined {
  return hrefs
    .filter((h) => pathname === h || pathname.startsWith(h + '/'))
    .sort((a, b) => b.length - a.length)[0];
}

/** Etiqueta de la sección para la miga de pan de la barra superior. */
export function sectionFor(pathname: string): { group: string; item?: string } {
  const all = NAV_GROUPS.flatMap((g) => g.items.map((i) => ({ g, i })));
  const href = activeHref(pathname, all.map((x) => x.i.href));
  const hit = all.find((x) => x.i.href === href);
  return hit ? { group: hit.g.label, item: hit.i.label } : { group: '' };
}
