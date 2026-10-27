/**
 * Menú de la app (ShellV1 del canvas F3). Los grupos plegables recuerdan su
 * estado; Administración sólo la ve el dueño o un administrador. Facturas
 * recibidas, Proveedores (F6) e Impresos (F7) entran cuando existan sus rutas.
 */
import {
  Banknote, BarChart3, Bell, Calculator, CheckSquare, ClipboardCheck, DollarSign, FilePlus,
  FileSignature, FileSpreadsheet, FileText, Hash, LayoutDashboard, List, MapPin, MessageSquare,
  PenLine, Phone, Receipt, Settings, Shield, Sparkles, UserCog, Users, type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export interface NavGroup {
  id: string;
  label: string;
  /** Los grupos fijos (Overview, Administración) no se pliegan. */
  collapsible: boolean;
  /** Plegado la primera vez (luego manda lo que eligió el usuario). */
  collapsedByDefault?: boolean;
  adminOnly?: boolean;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    id: 'overview', label: 'Overview', collapsible: false, items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/calculator', label: 'Calculadora', icon: Calculator },
      { href: '/ai', label: 'Asistente IA', icon: Sparkles },
    ],
  },
  {
    id: 'operacion', label: 'Operación', collapsible: true, items: [
      { href: '/loans', label: 'Préstamos', icon: FileText },
      { href: '/customers', label: 'Clientes', icon: Users },
      { href: '/payments', label: 'Pagos', icon: DollarSign },
      { href: '/cashbox', label: 'Caja', icon: Banknote },
    ],
  },
  {
    id: 'cobranza', label: 'Cobranza', collapsible: true, items: [
      { href: '/collections', label: 'Mesa de cobranza', icon: Phone },
      { href: '/collections/contacts', label: 'Gestiones', icon: PenLine },
      { href: '/collections/reminders', label: 'Recordatorios', icon: Bell },
      { href: '/collector', label: 'Cobrador móvil', icon: MapPin },
      { href: '/collections/reports', label: 'Reportes', icon: BarChart3 },
    ],
  },
  {
    id: 'facturacion', label: 'Facturación', collapsible: true, collapsedByDefault: true, items: [
      { href: '/billing', label: 'Facturas e-CF', icon: Receipt },
      { href: '/billing/sequences', label: 'Secuencias e-NCF', icon: Hash },
      { href: '/billing/certificates', label: 'Certificados', icon: Shield },
      { href: '/billing/dgii-reports', label: 'Reportes DGII', icon: FileSpreadsheet },
    ],
  },
  {
    id: 'contratos', label: 'Contratos', collapsible: true, collapsedByDefault: true, items: [
      { href: '/contracts', label: 'Contratos', icon: FileSignature },
      { href: '/contracts/generate', label: 'Generar contrato', icon: FilePlus },
      { href: '/contract-templates', label: 'Plantillas', icon: List },
    ],
  },
  {
    id: 'comunicaciones', label: 'Comunicaciones', collapsible: true, collapsedByDefault: true, items: [
      { href: '/communications', label: 'Mensajes', icon: MessageSquare },
      { href: '/tasks', label: 'Tareas', icon: CheckSquare },
    ],
  },
  {
    id: 'admin', label: 'Administración', collapsible: false, adminOnly: true, items: [
      { href: '/users', label: 'Equipo', icon: UserCog },
      { href: '/audit', label: 'Auditoría', icon: ClipboardCheck },
      { href: '/settings', label: 'Configuración', icon: Settings },
    ],
  },
];

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
